"""
Risk Manager Service
Handles position sizing, daily/weekly loss limits, and trade validation
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass, field
import logging
import json
from pathlib import Path

from config.settings import config
from services.news_monitor import news_monitor

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Record of a completed trade"""
    ticket: int
    symbol: str
    type: str
    volume: float
    open_price: float
    close_price: float
    profit: float
    open_time: datetime
    close_time: datetime
    strategy: str


class RiskManager:
    """Manages trading risk and position sizing"""

    def __init__(self):
        self.trade_history: List[TradeRecord] = []
        self.daily_pnl: float = 0.0
        self.weekly_pnl: float = 0.0
        self.last_reset_date: Optional[datetime] = None
        self.last_weekly_reset: Optional[datetime] = None
        self._history_file = Path("data/trade_history.json")
        self._load_history()

    def can_trade(self, account_balance: float) -> tuple[bool, str]:
        """Check if trading is allowed based on risk rules"""
        # Check daily reset
        self._check_daily_reset()

        # Check news blackout
        if news_monitor.is_blackout_active():
            reason = news_monitor.get_blackout_reason()
            return False, f"News blackout active: {reason}"

        # Check daily loss limit
        daily_loss_limit = account_balance * config.risk.max_daily_loss
        if self.daily_pnl <= -daily_loss_limit:
            return False, f"Daily loss limit reached: {self.daily_pnl:.2f} ({config.risk.max_daily_loss*100}%)"

        # Check weekly loss limit
        weekly_loss_limit = account_balance * config.risk.max_weekly_loss
        if self.weekly_pnl <= -weekly_loss_limit:
            return False, f"Weekly loss limit reached: {self.weekly_pnl:.2f} ({config.risk.max_weekly_loss*100}%)"

        return True, "Trading allowed"

    def calculate_position_size(
        self,
        account_balance: float,
        sl_pips: float,
        risk_percent: float = None
    ) -> float:
        """Calculate position size based on risk parameters"""
        if risk_percent is None:
            risk_percent = config.risk.account_risk_per_trade

        risk_amount = account_balance * risk_percent

        # Approximate pip value for EUR/USD (standard lot)
        pip_value_per_lot = 10.0  # $10 per pip for 1 standard lot

        if sl_pips <= 0:
            return config.risk.min_lot_size

        lot_size = risk_amount / (sl_pips * pip_value_per_lot)

        # Clamp to allowed range
        lot_size = max(config.risk.min_lot_size, min(lot_size, config.risk.max_lot_size))
        lot_size = round(lot_size, 2)

        return lot_size

    def validate_trade(
        self,
        account_balance: float,
        open_positions: int,
        sl_pips: float,
        strategy: str
    ) -> tuple[bool, str, float]:
        """Validate if a trade should be taken and return position size"""
        # Check if we can trade
        can, reason = self.can_trade(account_balance)
        if not can:
            return False, reason, 0.0

        # Check max open positions
        if open_positions >= config.risk.max_open_trades:
            return False, f"Max open trades reached: {open_positions}/{config.risk.max_open_trades}", 0.0

        # Calculate position size
        lot_size = self.calculate_position_size(account_balance, sl_pips)

        return True, "Trade approved", lot_size

    def record_trade(self, trade: TradeRecord):
        """Record a completed trade"""
        self.trade_history.append(trade)
        self.daily_pnl += trade.profit
        self.weekly_pnl += trade.profit
        self._save_history()

        logger.info(
            f"Trade recorded: {trade.type} {trade.symbol} | "
            f"P&L: {trade.profit:.2f} | Daily: {self.daily_pnl:.2f} | Weekly: {self.weekly_pnl:.2f}"
        )

    def _check_daily_reset(self):
        """Reset daily P&L at midnight UTC"""
        now = datetime.utcnow()
        if self.last_reset_date is None or now.date() > self.last_reset_date.date():
            self.daily_pnl = 0.0
            self.last_reset_date = now
            logger.info("Daily P&L reset")

        # Weekly reset on Monday
        if now.weekday() == 0 and (
            self.last_weekly_reset is None or
            (now - self.last_weekly_reset).days >= 7
        ):
            self.weekly_pnl = 0.0
            self.last_weekly_reset = now
            logger.info("Weekly P&L reset")

    def get_risk_summary(self, account_balance: float) -> Dict:
        """Get current risk status summary"""
        self._check_daily_reset()

        daily_loss_limit = account_balance * config.risk.max_daily_loss
        weekly_loss_limit = account_balance * config.risk.max_weekly_loss

        return {
            "daily_pnl": round(self.daily_pnl, 2),
            "daily_limit": round(daily_loss_limit, 2),
            "daily_remaining": round(daily_loss_limit + self.daily_pnl, 2),
            "daily_percent": round((self.daily_pnl / account_balance) * 100, 2) if account_balance > 0 else 0,
            "weekly_pnl": round(self.weekly_pnl, 2),
            "weekly_limit": round(weekly_loss_limit, 2),
            "weekly_remaining": round(weekly_loss_limit + self.weekly_pnl, 2),
            "weekly_percent": round((self.weekly_pnl / account_balance) * 100, 2) if account_balance > 0 else 0,
            "news_blackout": news_monitor.is_blackout_active(),
            "blackout_reason": news_monitor.get_blackout_reason()
        }

    def get_trade_stats(self) -> Dict:
        """Calculate trading statistics"""
        if not self.trade_history:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_profit": 0,
                "total_loss": 0,
                "net_pnl": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "profit_factor": 0,
                "best_trade": 0,
                "worst_trade": 0
            }

        winning = [t for t in self.trade_history if t.profit > 0]
        losing = [t for t in self.trade_history if t.profit < 0]

        total_profit = sum(t.profit for t in winning)
        total_loss = abs(sum(t.profit for t in losing))

        return {
            "total_trades": len(self.trade_history),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": round(len(winning) / len(self.trade_history) * 100, 1),
            "total_profit": round(total_profit, 2),
            "total_loss": round(total_loss, 2),
            "net_pnl": round(total_profit - total_loss, 2),
            "avg_win": round(total_profit / len(winning), 2) if winning else 0,
            "avg_loss": round(total_loss / len(losing), 2) if losing else 0,
            "profit_factor": round(total_profit / total_loss, 2) if total_loss > 0 else 0,
            "best_trade": round(max(t.profit for t in self.trade_history), 2),
            "worst_trade": round(min(t.profit for t in self.trade_history), 2)
        }

    def _save_history(self):
        """Save trade history to file"""
        try:
            self._history_file.parent.mkdir(exist_ok=True)
            data = {
                "daily_pnl": self.daily_pnl,
                "weekly_pnl": self.weekly_pnl,
                "last_reset": self.last_reset_date.isoformat() if self.last_reset_date else None,
                "last_weekly_reset": self.last_weekly_reset.isoformat() if self.last_weekly_reset else None,
                "trades": [
                    {
                        "ticket": t.ticket,
                        "symbol": t.symbol,
                        "type": t.type,
                        "volume": t.volume,
                        "open_price": t.open_price,
                        "close_price": t.close_price,
                        "profit": t.profit,
                        "open_time": t.open_time.isoformat(),
                        "close_time": t.close_time.isoformat(),
                        "strategy": t.strategy
                    }
                    for t in self.trade_history[-1000:]  # Keep last 1000 trades
                ]
            }
            self._history_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save trade history: {e}")

    def _load_history(self):
        """Load trade history from file"""
        try:
            if self._history_file.exists():
                data = json.loads(self._history_file.read_text())
                self.daily_pnl = data.get("daily_pnl", 0.0)
                self.weekly_pnl = data.get("weekly_pnl", 0.0)
                self.last_reset_date = datetime.fromisoformat(data["last_reset"]) if data.get("last_reset") else None
                self.last_weekly_reset = datetime.fromisoformat(data["last_weekly_reset"]) if data.get("last_weekly_reset") else None
                self.trade_history = [
                    TradeRecord(
                        ticket=t["ticket"],
                        symbol=t["symbol"],
                        type=t["type"],
                        volume=t["volume"],
                        open_price=t["open_price"],
                        close_price=t["close_price"],
                        profit=t["profit"],
                        open_time=datetime.fromisoformat(t["open_time"]),
                        close_time=datetime.fromisoformat(t["close_time"]),
                        strategy=t["strategy"]
                    )
                    for t in data.get("trades", [])
                ]
                logger.info(f"Loaded {len(self.trade_history)} trades from history")
        except Exception as e:
            logger.warning(f"Failed to load trade history: {e}")


# Global risk manager instance
risk_manager = RiskManager()
