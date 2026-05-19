"""
MT5 Cloud Service
Connects to local MT5 bridge via HTTP for cloud deployment
"""

import requests
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

# MT5 Bridge URL from environment variable
MT5_BRIDGE_URL = os.getenv("MT5_BRIDGE_URL", "http://localhost:5000")


@dataclass
class TradeResult:
    """Result of a trade execution"""
    success: bool
    order_id: Optional[int] = None
    message: str = ""
    price: float = 0.0


@dataclass
class Position:
    """Open position info"""
    ticket: int
    symbol: str
    type: str  # "BUY" or "SELL"
    volume: float
    open_price: float
    current_price: float
    profit: float
    sl: float
    tp: float
    open_time: datetime


class MT5CloudService:
    """Service for connecting to MT5 via cloud bridge"""

    def __init__(self):
        self.bridge_url = MT5_BRIDGE_URL
        self.connected = False

    def connect(self, login: int, password: str, server: str) -> bool:
        """Connect to MT5 via bridge"""
        try:
            response = requests.post(
                f"{self.bridge_url}/connect",
                json={
                    "login": login,
                    "password": password,
                    "server": server
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                self.connected = data.get("connected", False)
                if self.connected:
                    logger.info(f"Connected to MT5 via bridge: Account #{data['account']['login']}")
                return self.connected
            else:
                logger.error(f"Bridge connection failed: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Bridge connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from MT5"""
        try:
            requests.post(f"{self.bridge_url}/disconnect", timeout=10)
            self.connected = False
        except Exception as e:
            logger.warning(f"Disconnect error: {e}")

    def check_status(self) -> bool:
        """Check if bridge is connected to MT5"""
        try:
            response = requests.get(f"{self.bridge_url}/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.connected = data.get("connected", False)
                return self.connected
            return False
        except Exception:
            return False

    def get_account_info(self) -> Optional[Dict]:
        """Get account information"""
        try:
            response = requests.get(f"{self.bridge_url}/account", timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Get account info error: {e}")
            return None

    def get_current_price(self, symbol: str = "EURUSD") -> Optional[Tuple[float, float]]:
        """Get current bid/ask price"""
        try:
            response = requests.get(f"{self.bridge_url}/price/{symbol}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return (data["bid"], data["ask"])
            return None
        except Exception as e:
            logger.error(f"Get price error: {e}")
            return None

    def get_ohlcv(self, symbol: str = "EURUSD", timeframe: int = 15, count: int = 500):
        """Get OHLCV data"""
        try:
            import pandas as pd
            response = requests.get(
                f"{self.bridge_url}/ohlcv/{symbol}",
                params={"timeframe": timeframe, "count": count},
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('time', inplace=True)
                return df
            return None
        except Exception as e:
            logger.error(f"Get OHLCV error: {e}")
            return None

    def open_trade(
        self,
        symbol: str,
        trade_type: str,
        sl_pips: float,
        tp_pips: float,
        lot_size: float = 0.01,
        comment: str = ""
    ) -> TradeResult:
        """Open a new trade via bridge"""
        try:
            response = requests.post(
                f"{self.bridge_url}/trade/open",
                json={
                    "symbol": symbol,
                    "trade_type": trade_type,
                    "volume": lot_size,
                    "sl": sl_pips,
                    "tp": tp_pips,
                    "comment": comment
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                return TradeResult(
                    success=True,
                    order_id=data.get("order_id"),
                    price=data.get("price", 0),
                    message=f"{trade_type} {lot_size} lots @ {data.get('price', 0)}"
                )
            else:
                return TradeResult(
                    success=False,
                    message=response.json().get("detail", "Unknown error")
                )

        except Exception as e:
            logger.error(f"Open trade error: {e}")
            return TradeResult(success=False, message=str(e))

    def close_trade(self, ticket: int) -> TradeResult:
        """Close a trade via bridge"""
        try:
            response = requests.post(
                f"{self.bridge_url}/trade/close/{ticket}",
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                return TradeResult(
                    success=True,
                    price=data.get("price", 0),
                    message=f"Closed @ {data.get('price', 0)}"
                )
            else:
                return TradeResult(
                    success=False,
                    message=response.json().get("detail", "Unknown error")
                )

        except Exception as e:
            logger.error(f"Close trade error: {e}")
            return TradeResult(success=False, message=str(e))

    def close_all_trades(self) -> List[TradeResult]:
        """Close all trades via bridge"""
        try:
            response = requests.post(f"{self.bridge_url}/trade/close-all", timeout=30)

            if response.status_code == 200:
                data = response.json()
                return [
                    TradeResult(
                        success=r.get("success", False),
                        message=f"Ticket #{r['ticket']}"
                    )
                    for r in data.get("results", [])
                ]
            return []
        except Exception as e:
            logger.error(f"Close all error: {e}")
            return []

    def get_open_positions(self, magic: int = None) -> List[Position]:
        """Get open positions via bridge"""
        try:
            url = f"{self.bridge_url}/positions"
            if magic:
                url = f"{self.bridge_url}/positions/{magic}"

            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return [
                    Position(
                        ticket=p["ticket"],
                        symbol=p["symbol"],
                        type=p["type"],
                        volume=p["volume"],
                        open_price=p["open_price"],
                        current_price=p["current_price"],
                        profit=p["profit"],
                        sl=p["sl"],
                        tp=p["tp"],
                        open_time=datetime.fromtimestamp(p["time"])
                    )
                    for p in data
                ]
            return []
        except Exception as e:
            logger.error(f"Get positions error: {e}")
            return []

    def modify_sl_tp(self, ticket: int, new_sl: float = None, new_tp: float = None) -> bool:
        """Modify SL/TP via bridge"""
        try:
            response = requests.post(
                f"{self.bridge_url}/trade/modify",
                json={
                    "ticket": ticket,
                    "sl": new_sl,
                    "tp": new_tp
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Modify error: {e}")
            return False

    def calculate_lot_size(self, symbol: str, sl_pips: float, risk_percent: float = 0.02) -> float:
        """Calculate position size based on risk"""
        account = self.get_account_info()
        if not account:
            return 0.01

        balance = account.get("balance", 0)
        risk_amount = balance * risk_percent

        # Approximate pip value for EUR/USD
        pip_value_per_lot = 10.0

        if sl_pips <= 0:
            return 0.01

        lot_size = risk_amount / (sl_pips * pip_value_per_lot)
        lot_size = max(0.01, min(lot_size, 1.0))
        lot_size = round(lot_size, 2)

        return lot_size


# Global MT5 cloud service instance
mt5_cloud_service = MT5CloudService()
