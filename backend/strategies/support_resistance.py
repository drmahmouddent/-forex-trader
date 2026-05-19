"""
Support/Resistance Bounce Strategy
Trades bounces off key S/R levels with candlestick confirmation
Works best during ranging markets
"""

import pandas as pd
import numpy as np
import logging

from strategies.base_strategy import BaseStrategy, Signal
from config.settings import config

logger = logging.getLogger(__name__)


class SupportResistanceStrategy(BaseStrategy):
    """Support/Resistance Bounce Strategy"""

    def __init__(self):
        super().__init__("Support/Resistance")
        self.lookback = config.strategy.sr_lookback
        self.touch_tolerance = config.strategy.sr_touch_tolerance

    def analyze(self, df: pd.DataFrame) -> Signal:
        """Analyze for S/R bounce setup"""
        if df is None or len(df) < self.lookback:
            return Signal(
                type="NONE", sl_pips=0, tp_pips=0,
                strategy=self.name, confidence=0, reason="Insufficient data"
            )

        # Find S/R levels
        support_levels, resistance_levels = self._find_support_resistance(df, self.lookback)

        if not support_levels and not resistance_levels:
            return Signal(
                type="NONE", sl_pips=0, tp_pips=0,
                strategy=self.name, confidence=0, reason="No S/R levels found"
            )

        current_price = df['close'].iloc[-1]
        current_candle = df.iloc[-1]
        previous_candle = df.iloc[-2]

        # Calculate ATR for dynamic SL/TP
        atr = self._calculate_atr(df, 14).iloc[-1]

        # Check for support bounce (BUY)
        for level in support_levels:
            if self._is_near_level(current_price, level) and self._is_bullish_bounce(df, level):
                sl_pips = (current_price - (level - atr)) * 10000
                tp_pips = sl_pips * 1.5  # 1:1.5 R:R for ranging market

                if sl_pips > 0 and tp_pips > 0:
                    confidence = self._calculate_bounce_confidence(df, "BUY", level, support_levels, resistance_levels)

                    return Signal(
                        type="BUY",
                        sl_pips=round(sl_pips, 1),
                        tp_pips=round(tp_pips, 1),
                        strategy=self.name,
                        confidence=confidence,
                        entry_price=current_price,
                        reason=f"Support bounce at {level:.5f}"
                    )

        # Check for resistance bounce (SELL)
        for level in resistance_levels:
            if self._is_near_level(current_price, level) and self._is_bearish_bounce(df, level):
                sl_pips = ((level + atr) - current_price) * 10000
                tp_pips = sl_pips * 1.5  # 1:1.5 R:R for ranging market

                if sl_pips > 0 and tp_pips > 0:
                    confidence = self._calculate_bounce_confidence(df, "SELL", level, support_levels, resistance_levels)

                    return Signal(
                        type="SELL",
                        sl_pips=round(sl_pips, 1),
                        tp_pips=round(tp_pips, 1),
                        strategy=self.name,
                        confidence=confidence,
                        entry_price=current_price,
                        reason=f"Resistance bounce at {level:.5f}"
                    )

        return Signal(
            type="NONE", sl_pips=0, tp_pips=0,
            strategy=self.name, confidence=0, reason="No bounce setup"
        )

    def _is_near_level(self, price: float, level: float) -> bool:
        """Check if price is near a S/R level"""
        return abs(price - level) <= self.touch_tolerance

    def _is_bullish_bounce(self, df: pd.DataFrame, support_level: float) -> bool:
        """Check for bullish bounce pattern at support"""
        last_candles = df.tail(3)

        # Pattern 1: Hammer/Pin bar at support
        last = last_candles.iloc[-1]
        body = abs(last['close'] - last['open'])
        lower_wick = min(last['open'], last['close']) - last['low']
        upper_wick = last['high'] - max(last['open'], last['close'])

        # Hammer: long lower wick, small body
        if lower_wick > body * 2 and upper_wick < body:
            if last['low'] <= support_level + self.touch_tolerance:
                return True

        # Pattern 2: Bullish engulfing
        prev = last_candles.iloc[-2]
        if (
            prev['close'] < prev['open'] and  # Previous bearish
            last['close'] > last['open'] and  # Current bullish
            last['close'] > prev['open'] and  # Closes above previous open
            last['open'] < prev['close']  # Opens below previous close
        ):
            if last['low'] <= support_level + self.touch_tolerance:
                return True

        # Pattern 3: Double bottom
        if len(df) >= 20:
            recent_lows = df['low'].tail(20)
            low_points = recent_lows[recent_lows <= support_level + self.touch_tolerance]
            if len(low_points) >= 2:
                return True

        return False

    def _is_bearish_bounce(self, df: pd.DataFrame, resistance_level: float) -> bool:
        """Check for bearish bounce pattern at resistance"""
        last_candles = df.tail(3)

        # Pattern 1: Shooting star at resistance
        last = last_candles.iloc[-1]
        body = abs(last['close'] - last['open'])
        lower_wick = min(last['open'], last['close']) - last['low']
        upper_wick = last['high'] - max(last['open'], last['close'])

        # Shooting star: long upper wick, small body
        if upper_wick > body * 2 and lower_wick < body:
            if last['high'] >= resistance_level - self.touch_tolerance:
                return True

        # Pattern 2: Bearish engulfing
        prev = last_candles.iloc[-2]
        if (
            prev['close'] > prev['open'] and  # Previous bullish
            last['close'] < last['open'] and  # Current bearish
            last['close'] < prev['open'] and  # Closes below previous open
            last['open'] > prev['close']  # Opens above previous close
        ):
            if last['high'] >= resistance_level - self.touch_tolerance:
                return True

        # Pattern 3: Double top
        if len(df) >= 20:
            recent_highs = df['high'].tail(20)
            high_points = recent_highs[recent_highs >= resistance_level - self.touch_tolerance]
            if len(high_points) >= 2:
                return True

        return False

    def _calculate_bounce_confidence(
        self,
        df: pd.DataFrame,
        direction: str,
        level: float,
        support_levels: list,
        resistance_levels: list
    ) -> float:
        """Calculate confidence for S/R bounce"""
        confidence = 0.5

        # RSI confirmation
        rsi = self._calculate_rsi(df['close'], 14).iloc[-1]
        if direction == "BUY" and rsi < 35:
            confidence += 0.15
        elif direction == "SELL" and rsi > 65:
            confidence += 0.15

        # Level strength (more touches = stronger)
        if direction == "BUY":
            touches = sum(1 for l in support_levels if abs(l - level) < self.touch_tolerance * 2)
        else:
            touches = sum(1 for l in resistance_levels if abs(l - level) < self.touch_tolerance * 2)

        if touches >= 3:
            confidence += 0.15
        elif touches >= 2:
            confidence += 0.1

        # Distance from other levels (clear path to target)
        if direction == "BUY" and resistance_levels:
            nearest_resistance = min(resistance_levels, key=lambda x: abs(x - level))
            distance = (nearest_resistance - level) * 10000
            if distance > 30:  # At least 30 pips to next resistance
                confidence += 0.1
        elif direction == "SELL" and support_levels:
            nearest_support = min(support_levels, key=lambda x: abs(x - level))
            distance = (level - nearest_support) * 10000
            if distance > 30:
                confidence += 0.1

        # Candle pattern strength
        last = df.iloc[-1]
        body = abs(last['close'] - last['open'])
        full_range = last['high'] - last['low']
        if full_range > 0 and body / full_range < 0.3:  # Small body relative to range
            confidence += 0.1

        return min(confidence, 1.0)
