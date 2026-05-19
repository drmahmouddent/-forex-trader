"""
Strategy Manager
Orchestrates all trading strategies and selects the best signal
"""

import pandas as pd
from typing import List, Optional
import logging

from strategies.base_strategy import Signal
from strategies.london_breakout import LondonBreakoutStrategy
from strategies.trend_following import TrendFollowingStrategy
from strategies.support_resistance import SupportResistanceStrategy
from config.settings import config

logger = logging.getLogger(__name__)


class StrategyManager:
    """Manages and orchestrates all trading strategies"""

    def __init__(self):
        self.strategies = []

        # Initialize strategies based on config
        if config.strategy.london_breakout_enabled:
            self.strategies.append(LondonBreakoutStrategy())
            logger.info("London Breakout strategy enabled")

        if config.strategy.trend_following_enabled:
            self.strategies.append(TrendFollowingStrategy())
            logger.info("Trend Following strategy enabled")

        if config.strategy.sr_enabled:
            self.strategies.append(SupportResistanceStrategy())
            logger.info("Support/Resistance strategy enabled")

    def analyze_all(self, df: pd.DataFrame) -> Optional[Signal]:
        """Run all strategies and return the best signal"""
        signals: List[Signal] = []

        for strategy in self.strategies:
            if not strategy.enabled:
                continue

            try:
                signal = strategy.analyze(df)
                if signal.is_valid:
                    signals.append(signal)
                    logger.info(
                        f"Signal from {strategy.name}: {signal.type} "
                        f"SL:{signal.sl_pips} TP:{signal.tp_pips} "
                        f"Confidence:{signal.confidence:.2f}"
                    )
            except Exception as e:
                logger.error(f"Strategy {strategy.name} error: {e}")

        if not signals:
            return None

        # Select best signal based on confidence
        best_signal = max(signals, key=lambda s: s.confidence)

        # Only return signal if confidence is above threshold
        min_confidence = 0.6
        if best_signal.confidence < min_confidence:
            logger.info(f"Best signal confidence {best_signal.confidence:.2f} below threshold {min_confidence}")
            return None

        logger.info(
            f"Selected signal: {best_signal.strategy} - {best_signal.type} "
            f"Confidence:{best_signal.confidence:.2f} | {best_signal.reason}"
        )

        return best_signal

    def get_strategy_status(self) -> List[dict]:
        """Get status of all strategies"""
        return [
            {
                "name": s.name,
                "enabled": s.enabled
            }
            for s in self.strategies
        ]

    def enable_strategy(self, name: str) -> bool:
        """Enable a strategy by name"""
        for strategy in self.strategies:
            if strategy.name == name:
                strategy.enabled = True
                logger.info(f"Strategy {name} enabled")
                return True
        return False

    def disable_strategy(self, name: str) -> bool:
        """Disable a strategy by name"""
        for strategy in self.strategies:
            if strategy.name == name:
                strategy.enabled = False
                logger.info(f"Strategy {name} disabled")
                return True
        return False


# Global strategy manager instance
strategy_manager = StrategyManager()
