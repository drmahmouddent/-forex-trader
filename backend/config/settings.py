"""
Forex Trader Configuration
EUR/USD Automated Trading System with News Filter
"""

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class TimeFrame(Enum):
    M1 = 1
    M5 = 5
    M15 = 15
    M30 = 30
    H1 = 60
    H4 = 240
    D1 = 1440


@dataclass
class MT5Config:
    """MetaTrader 5 connection settings"""
    login: int = 0  # Your MT5 account number
    password: str = ""
    server: str = ""
    path: str = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    timeout: int = 60000


@dataclass
class TradingPairConfig:
    """Configuration for a trading pair"""
    symbol: str = "EURUSD"
    timeframe: TimeFrame = TimeFrame.M15
    spread_limit: float = 2.0  # Max spread in pips
    magic_number: int = 202505


@dataclass
class RiskConfig:
    """Risk management settings"""
    account_risk_per_trade: float = 0.02  # 2% per trade
    max_daily_loss: float = 0.05  # 5% daily loss limit
    max_weekly_loss: float = 0.10  # 10% weekly loss limit
    max_open_trades: int = 3
    default_rr_ratio: float = 2.0  # 1:2 risk-reward
    max_lot_size: float = 1.0
    min_lot_size: float = 0.01


@dataclass
class NewsConfig:
    """News filter settings"""
    enabled: bool = True
    high_impact_buffer_minutes: int = 30  # Stop trading 30 min before/after
    medium_impact_buffer_minutes: int = 15
    sources: List[str] = field(default_factory=lambda: [
        "forex_factory",
        "investing_com"
    ])
    currencies_to_watch: List[str] = field(default_factory=lambda: ["USD", "EUR"])


@dataclass
class StrategyConfig:
    """Strategy-specific settings"""
    # London Breakout
    london_breakout_enabled: bool = True
    london_session_start: int = 7  # UTC hour
    london_session_end: int = 10
    asian_session_start: int = 0
    asian_session_end: int = 7

    # Trend Following
    trend_following_enabled: bool = True
    ema_fast: int = 9
    ema_slow: int = 21
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    # Support/Resistance
    sr_enabled: bool = True
    sr_lookback: int = 100  # Candles to look back for S/R levels
    sr_touch_tolerance: float = 0.0005  # 5 pips tolerance


@dataclass
class AppConfig:
    """Main application configuration"""
    mt5: MT5Config = field(default_factory=MT5Config)
    pair: TradingPairConfig = field(default_factory=TradingPairConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    news: NewsConfig = field(default_factory=NewsConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/trading.log"


# Global config instance
config = AppConfig()
