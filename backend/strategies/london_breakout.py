"""
London Session Breakout Strategy
Trades the breakout of Asian session range during London open
EUR/USD's biggest moves happen during London session (7:00-10:00 UTC)
"""

import pandas as pd
from datetime import datetime
import logging

from strategies.base_strategy import BaseStrategy, Signal
from config.settings import config

logger = logging.getLogger(__name__)


class LondonBreakoutStrategy(BaseStrategy):
    """London Session Breakout Strategy"""

    def __init__(self):
        super().__init__("London Breakout")
        self.asian_start = config.strategy.asian_session_start  # 0 UTC
        self.asian_end = config.strategy.asian_session_end  # 7 UTC
        self.london_start = config.strategy.london_session_start  # 7 UTC
        self.london_end = config.strategy.london_session_end  # 10 UTC

    def analyze(self, df: pd.DataFrame) -> Signal:
        """Analyze for London breakout setup"""
        if df is None or len(df) < 50:
            return Signal(
                type="NONE", sl_pips=0, tp_pips=0,
                strategy=self.name, confidence=0, reason="Insufficient data"
            )

        now = datetime.utcnow()
        current_hour = now.hour

        # Only trade during London session hours
        if not (self.london_start <= current_hour < self.london_end):
            return Signal(
                type="NONE", sl_pips=0, tp_pips=0,
                strategy=self.name, confidence=0, reason="Outside London session"
            )

        # Get Asian session range
        asian_high, asian_low = self._get_asian_range(df)

        if asian_high is None or asian_low is None:
            return Signal(
                type="NONE", sl_pips=0, tp_pips=0,
                strategy=self.name, confidence=0, reason="No Asian range found"
            )

        # Current price
        current_price = df['close'].iloc[-1]
        range_size = asian_high - asian_low

        # Minimum range filter (avoid trading tiny ranges)
        min_range_pips = 15 * 0.0001  # 15 pips
        if range_size < min_range_pips:
            return Signal(
                type="NONE", sl_pips=0, tp_pips=0,
                strategy=self.name, confidence=0,
                reason=f"Range too small: {range_size*10000:.0f} pips"
            )

        # Maximum range filter (avoid trading huge ranges)
        max_range_pips = 60 * 0.0001  # 60 pips
        if range_size > max_range_pips:
            return Signal(
                type="NONE", sl_pips=0, tp_pips=0,
                strategy=self.name, confidence=0,
                reason=f"Range too large: {range_size*10000:.0f} pips"
            )

        # Check for breakout
        breakout_buffer = 5 * 0.0001  # 5 pips buffer above/below range

        # BUY breakout above Asian high
        if current_price > asian_high + breakout_buffer:
            sl_pips = (current_price - asian_low) * 10000 + 5  # SL below Asian low + buffer
            tp_pips = sl_pips * config.risk.default_rr_ratio  # 1:2 R:R

            confidence = self._calculate_breakout_confidence(df, "BUY", asian_high)

            return Signal(
                type="BUY",
                sl_pips=round(sl_pips, 1),
                tp_pips=round(tp_pips, 1),
                strategy=self.name,
                confidence=confidence,
                entry_price=current_price,
                reason=f"Breakout above Asian high {asian_high:.5f}"
            )

        # SELL breakout below Asian low
        if current_price < asian_low - breakout_buffer:
            sl_pips = (asian_high - current_price) * 10000 + 5  # SL above Asian high + buffer
            tp_pips = sl_pips * config.risk.default_rr_ratio  # 1:2 R:R

            confidence = self._calculate_breakout_confidence(df, "SELL", asian_low)

            return Signal(
                type="SELL",
                sl_pips=round(sl_pips, 1),
                tp_pips=round(tp_pips, 1),
                strategy=self.name,
                confidence=confidence,
                entry_price=current_price,
                reason=f"Breakout below Asian low {asian_low:.5f}"
            )

        return Signal(
            type="NONE", sl_pips=0, tp_pips=0,
            strategy=self.name, confidence=0, reason="No breakout detected"
        )

    def _get_asian_range(self, df: pd.DataFrame) -> tuple[float, float]:
        """Get the high and low of Asian session"""
        now = datetime.utcnow()

        # Calculate Asian session times for today
        today = now.date()
        asian_start = pd.Timestamp(f"{today} 00:00:00")
        asian_end = pd.Timestamp(f"{today} 07:00:00")

        # Filter data for Asian session
        asian_data = df[(df.index >= asian_start) & (df.index < asian_end)]

        if len(asian_data) < 5:
            return None, None

        asian_high = asian_data['high'].max()
        asian_low = asian_data['low'].min()

        return asian_high, asian_low

    def _calculate_breakout_confidence(
        self,
        df: pd.DataFrame,
        direction: str,
        breakout_level: float
    ) -> float:
        """Calculate confidence score for the breakout"""
        confidence = 0.5  # Base confidence

        # Volume confirmation (if available)
        if 'tick_volume' in df.columns:
            recent_vol = df['tick_volume'].tail(5).mean()
            avg_vol = df['tick_volume'].tail(50).mean()
            if avg_vol > 0 and recent_vol > avg_vol * 1.5:
                confidence += 0.15

        # Momentum confirmation
        rsi = self._calculate_rsi(df['close'], 14).iloc[-1]
        if direction == "BUY" and rsi > 55:
            confidence += 0.1
        elif direction == "SELL" and rsi < 45:
            confidence += 0.1

        # EMA trend alignment
        ema_20 = self._calculate_ema(df['close'], 20).iloc[-1]
        ema_50 = self._calculate_ema(df['close'], 50).iloc[-1]

        if direction == "BUY" and ema_20 > ema_50:
            confidence += 0.1
        elif direction == "SELL" and ema_20 < ema_50:
            confidence += 0.1

        # Multiple candle confirmation (3 consecutive candles in direction)
        last_3 = df['close'].tail(3)
        if direction == "BUY" and all(last_3.diff().dropna() > 0):
            confidence += 0.15
        elif direction == "SELL" and all(last_3.diff().dropna() < 0):
            confidence += 0.15

        return min(confidence, 1.0)
