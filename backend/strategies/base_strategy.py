"""
Base Strategy Class
All trading strategies inherit from this
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """Trading signal"""
    type: str  # "BUY", "SELL", "NONE"
    sl_pips: float
    tp_pips: float
    strategy: str
    confidence: float  # 0.0 to 1.0
    reason: str = ""
    entry_price: float = 0.0

    @property
    def is_valid(self) -> bool:
        return self.type in ("BUY", "SELL") and self.sl_pips > 0 and self.tp_pips > 0


class BaseStrategy(ABC):
    """Base class for all trading strategies"""

    def __init__(self, name: str):
        self.name = name
        self.enabled = True

    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> Signal:
        """Analyze market data and return a signal"""
        pass

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators - override if needed"""
        return df

    def _calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return series.ewm(span=period, adjust=False).mean()

    def _calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(
        self,
        series: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD, Signal line, and Histogram"""
        ema_fast = self._calculate_ema(series, fast)
        ema_slow = self._calculate_ema(series, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def _calculate_bollinger_bands(
        self,
        series: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)

        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    def _find_support_resistance(
        self,
        df: pd.DataFrame,
        lookback: int = 100
    ) -> tuple[List[float], List[float]]:
        """Find support and resistance levels"""
        highs = df['high'].tail(lookback)
        lows = df['low'].tail(lookback)

        resistance_levels = []
        support_levels = []

        # Find swing highs (resistance)
        for i in range(2, len(highs) - 2):
            if (
                highs.iloc[i] > highs.iloc[i-1] and
                highs.iloc[i] > highs.iloc[i-2] and
                highs.iloc[i] > highs.iloc[i+1] and
                highs.iloc[i] > highs.iloc[i+2]
            ):
                resistance_levels.append(highs.iloc[i])

        # Find swing lows (support)
        for i in range(2, len(lows) - 2):
            if (
                lows.iloc[i] < lows.iloc[i-1] and
                lows.iloc[i] < lows.iloc[i-2] and
                lows.iloc[i] < lows.iloc[i+1] and
                lows.iloc[i] < lows.iloc[i+2]
            ):
                support_levels.append(lows.iloc[i])

        # Cluster nearby levels
        resistance_levels = self._cluster_levels(resistance_levels)
        support_levels = self._cluster_levels(support_levels)

        return support_levels, resistance_levels

    def _cluster_levels(self, levels: List[float], tolerance: float = 0.0010) -> List[float]:
        """Cluster nearby price levels"""
        if not levels:
            return []

        levels = sorted(levels)
        clustered = [levels[0]]

        for level in levels[1:]:
            if level - clustered[-1] > tolerance:
                clustered.append(level)
            else:
                clustered[-1] = (clustered[-1] + level) / 2

        return clustered
