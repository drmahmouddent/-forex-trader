"""
Trend Following Strategy
Uses EMA crossover + RSI + MACD for trend confirmation
Works best during trending markets
"""

import pandas as pd
import logging

from strategies.base_strategy import BaseStrategy, Signal
from config.settings import config

logger = logging.getLogger(__name__)


class TrendFollowingStrategy(BaseStrategy):
    """EMA 9/21 Crossover with RSI and MACD confirmation"""

    def __init__(self):
        super().__init__("Trend Following")
        self.ema_fast = config.strategy.ema_fast  # 9
        self.ema_slow = config.strategy.ema_slow  # 21
        self.rsi_period = config.strategy.rsi_period  # 14

    def analyze(self, df: pd.DataFrame) -> Signal:
        """Analyze for trend following setup"""
        if df is None or len(df) < 100:
            return Signal(
                type="NONE", sl_pips=0, tp_pips=0,
                strategy=self.name, confidence=0, reason="Insufficient data"
            )

        # Calculate indicators
        df = self.calculate_indicators(df)

        # Get latest values
        current = df.iloc[-1]
        previous = df.iloc[-2]

        ema_fast = current['ema_fast']
        ema_slow = current['ema_slow']
        prev_ema_fast = previous['ema_fast']
        prev_ema_slow = previous['ema_slow']

        rsi = current['rsi']
        macd = current['macd']
        macd_signal = current['macd_signal']
        macd_hist = current['macd_hist']

        current_price = current['close']

        # Calculate ATR for dynamic SL/TP
        atr = self._calculate_atr(df, 14).iloc[-1]

        # Check for BUY signal
        if self._is_buy_signal(ema_fast, ema_slow, prev_ema_fast, prev_ema_slow, rsi, macd_hist):
            sl_pips = (atr * 2) * 10000  # 2x ATR for SL
            tp_pips = sl_pips * config.risk.default_rr_ratio  # 1:2 R:R

            confidence = self._calculate_confidence(df, "BUY", rsi, macd_hist)

            return Signal(
                type="BUY",
                sl_pips=round(sl_pips, 1),
                tp_pips=round(tp_pips, 1),
                strategy=self.name,
                confidence=confidence,
                entry_price=current_price,
                reason=f"EMA crossover BUY | RSI:{rsi:.0f} | MACD:{macd_hist:.5f}"
            )

        # Check for SELL signal
        if self._is_sell_signal(ema_fast, ema_slow, prev_ema_fast, prev_ema_slow, rsi, macd_hist):
            sl_pips = (atr * 2) * 10000  # 2x ATR for SL
            tp_pips = sl_pips * config.risk.default_rr_ratio  # 1:2 R:R

            confidence = self._calculate_confidence(df, "SELL", rsi, macd_hist)

            return Signal(
                type="SELL",
                sl_pips=round(sl_pips, 1),
                tp_pips=round(tp_pips, 1),
                strategy=self.name,
                confidence=confidence,
                entry_price=current_price,
                reason=f"EMA crossover SELL | RSI:{rsi:.0f} | MACD:{macd_hist:.5f}"
            )

        return Signal(
            type="NONE", sl_pips=0, tp_pips=0,
            strategy=self.name, confidence=0, reason="No signal"
        )

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all indicators"""
        df = df.copy()

        # EMAs
        df['ema_fast'] = self._calculate_ema(df['close'], self.ema_fast)
        df['ema_slow'] = self._calculate_ema(df['close'], self.ema_slow)

        # RSI
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)

        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = self._calculate_macd(
            df['close'],
            config.strategy.macd_fast,
            config.strategy.macd_slow,
            config.strategy.macd_signal
        )

        # ATR
        df['atr'] = self._calculate_atr(df, 14)

        return df

    def _is_buy_signal(
        self,
        ema_fast: float,
        ema_slow: float,
        prev_ema_fast: float,
        prev_ema_slow: float,
        rsi: float,
        macd_hist: float
    ) -> bool:
        """Check for BUY signal conditions"""
        # EMA crossover (fast crosses above slow)
        crossover = prev_ema_fast <= prev_ema_slow and ema_fast > ema_slow

        # RSI not overbought
        rsi_ok = rsi < config.strategy.rsi_overbought and rsi > 40

        # MACD histogram positive
        macd_ok = macd_hist > 0

        return crossover and rsi_ok and macd_ok

    def _is_sell_signal(
        self,
        ema_fast: float,
        ema_slow: float,
        prev_ema_fast: float,
        prev_ema_slow: float,
        rsi: float,
        macd_hist: float
    ) -> bool:
        """Check for SELL signal conditions"""
        # EMA crossover (fast crosses below slow)
        crossover = prev_ema_fast >= prev_ema_slow and ema_fast < ema_slow

        # RSI not oversold
        rsi_ok = rsi > config.strategy.rsi_oversold and rsi < 60

        # MACD histogram negative
        macd_ok = macd_hist < 0

        return crossover and rsi_ok and macd_ok

    def _calculate_confidence(
        self,
        df: pd.DataFrame,
        direction: str,
        rsi: float,
        macd_hist: float
    ) -> float:
        """Calculate signal confidence"""
        confidence = 0.5

        # RSI strength
        if direction == "BUY" and 50 < rsi < 65:
            confidence += 0.15
        elif direction == "SELL" and 35 < rsi < 50:
            confidence += 0.15

        # MACD histogram strength
        if abs(macd_hist) > 0.0002:
            confidence += 0.1

        # Price above/below both EMAs
        current_price = df['close'].iloc[-1]
        ema_fast = df['ema_fast'].iloc[-1]
        ema_slow = df['ema_slow'].iloc[-1]

        if direction == "BUY" and current_price > ema_fast > ema_slow:
            confidence += 0.15
        elif direction == "SELL" and current_price < ema_fast < ema_slow:
            confidence += 0.15

        # Trend strength (EMA separation increasing)
        ema_diff = abs(ema_fast - ema_slow)
        prev_ema_diff = abs(df['ema_fast'].iloc[-2] - df['ema_slow'].iloc[-2])
        if ema_diff > prev_ema_diff:
            confidence += 0.1

        return min(confidence, 1.0)
