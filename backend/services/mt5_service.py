"""
MetaTrader 5 Connection Service
Handles all communication with MT5 terminal
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
import logging

from config.settings import config

logger = logging.getLogger(__name__)


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


class MT5Service:
    """Service for MetaTrader 5 operations"""

    def __init__(self):
        self.connected = False
        self.account_info = None

    def connect(self) -> bool:
        """Initialize connection to MT5 terminal"""
        try:
            if not mt5.initialize(
                path=config.mt5.path,
                login=config.mt5.login,
                password=config.mt5.password,
                server=config.mt5.server,
                timeout=config.mt5.timeout
            ):
                logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                return False

            self.account_info = mt5.account_info()
            self.connected = True
            logger.info(f"Connected to MT5: Account #{self.account_info.login}")
            logger.info(f"Balance: {self.account_info.balance} {self.account_info.currency}")
            return True

        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from MT5 terminal"""
        mt5.shutdown()
        self.connected = False
        logger.info("Disconnected from MT5")

    def get_account_info(self) -> Optional[Dict]:
        """Get current account information"""
        if not self.connected:
            return None
        info = mt5.account_info()
        if info is None:
            return None
        return {
            "login": info.login,
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": info.margin_free,
            "profit": info.profit,
            "leverage": info.leverage,
            "currency": info.currency
        }

    def get_current_price(self, symbol: str = "EURUSD") -> Optional[Tuple[float, float]]:
        """Get current bid/ask price"""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.error(f"Failed to get price for {symbol}")
            return None
        return (tick.bid, tick.ask)

    def get_ohlcv(
        self,
        symbol: str = "EURUSD",
        timeframe: int = mt5.TIMEFRAME_M15,
        count: int = 500
    ) -> Optional[pd.DataFrame]:
        """Get OHLCV data as DataFrame"""
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None or len(rates) == 0:
            logger.error(f"Failed to get OHLCV data: {mt5.last_error()}")
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        return df

    def calculate_lot_size(
        self,
        symbol: str,
        sl_pips: float,
        risk_percent: float = None
    ) -> float:
        """Calculate position size based on risk"""
        if risk_percent is None:
            risk_percent = config.risk.account_risk_per_trade

        account = mt5.account_info()
        if account is None:
            return config.risk.min_lot_size

        balance = account.balance
        risk_amount = balance * risk_percent

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return config.risk.min_lot_size

        tick_value = symbol_info.trade_tick_value
        tick_size = symbol_info.trade_tick_size

        if tick_size == 0:
            return config.risk.min_lot_size

        pip_value = tick_value / tick_size
        if pip_value == 0:
            return config.risk.min_lot_size

        lot_size = risk_amount / (sl_pips * pip_value * 10)

        # Clamp to allowed range
        lot_size = max(config.risk.min_lot_size, min(lot_size, config.risk.max_lot_size))
        lot_size = round(lot_size, 2)

        return lot_size

    def open_trade(
        self,
        symbol: str,
        trade_type: str,  # "BUY" or "SELL"
        sl_pips: float,
        tp_pips: float,
        lot_size: float = None,
        comment: str = ""
    ) -> TradeResult:
        """Open a new trade"""
        if not self.connected:
            return TradeResult(success=False, message="Not connected to MT5")

        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return TradeResult(success=False, message=f"Failed to get price for {symbol}")

        # Check spread
        spread = (tick.ask - tick.bid) * 10000  # Convert to pips
        if spread > config.pair.spread_limit:
            return TradeResult(
                success=False,
                message=f"Spread too high: {spread:.1f} pips (limit: {config.pair.spread_limit})"
            )

        # Calculate lot size if not provided
        if lot_size is None:
            lot_size = self.calculate_lot_size(symbol, sl_pips)

        # Determine order type and prices
        if trade_type == "BUY":
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
            sl = price - sl_pips * 0.0001
            tp = price + tp_pips * 0.0001
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
            sl = price + sl_pips * 0.0001
            tp = price - tp_pips * 0.0001

        # Prepare request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "sl": round(sl, 5),
            "tp": round(tp, 5),
            "magic": config.pair.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Send order
        result = mt5.order_send(request)

        if result is None:
            return TradeResult(success=False, message=f"Order failed: {mt5.last_error()}")

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return TradeResult(
                success=False,
                message=f"Order rejected: {result.comment} (code: {result.retcode})"
            )

        logger.info(
            f"Trade opened: {trade_type} {lot_size} lots {symbol} @ {price:.5f} "
            f"SL:{sl:.5f} TP:{tp:.5f} | Order #{result.order}"
        )

        return TradeResult(
            success=True,
            order_id=result.order,
            price=price,
            message=f"{trade_type} {lot_size} lots @ {price:.5f}"
        )

    def close_trade(self, ticket: int) -> TradeResult:
        """Close an open trade by ticket"""
        if not self.connected:
            return TradeResult(success=False, message="Not connected to MT5")

        position = mt5.positions_get(ticket=ticket)
        if position is None or len(position) == 0:
            return TradeResult(success=False, message=f"Position #{ticket} not found")

        pos = position[0]

        # Determine close type
        if pos.type == mt5.ORDER_TYPE_BUY:
            close_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(pos.symbol).bid
        else:
            close_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(pos.symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "magic": config.pair.magic_number,
            "comment": "Close by bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            msg = result.comment if result else str(mt5.last_error())
            return TradeResult(success=False, message=f"Close failed: {msg}")

        logger.info(f"Position #{ticket} closed @ {price:.5f} | P&L: {pos.profit}")
        return TradeResult(success=True, price=price, message=f"Closed @ {price:.5f}")

    def close_all_trades(self) -> List[TradeResult]:
        """Close all open positions"""
        positions = mt5.positions_get()
        if positions is None or len(positions) == 0:
            return []

        results = []
        for pos in positions:
            if pos.magic == config.pair.magic_number:
                result = self.close_trade(pos.ticket)
                results.append(result)
        return results

    def get_open_positions(self) -> List[Position]:
        """Get all open positions for our bot"""
        positions = mt5.positions_get()
        if positions is None:
            return []

        result = []
        for pos in positions:
            if pos.magic == config.pair.magic_number:
                result.append(Position(
                    ticket=pos.ticket,
                    symbol=pos.symbol,
                    type="BUY" if pos.type == 0 else "SELL",
                    volume=pos.volume,
                    open_price=pos.price_open,
                    current_price=pos.price_current,
                    profit=pos.profit,
                    sl=pos.sl,
                    tp=pos.tp,
                    open_time=datetime.fromtimestamp(pos.time)
                ))
        return result

    def modify_sl_tp(self, ticket: int, new_sl: float = None, new_tp: float = None) -> bool:
        """Modify stop loss and/or take profit"""
        position = mt5.positions_get(ticket=ticket)
        if position is None or len(position) == 0:
            return False

        pos = position[0]

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": ticket,
            "sl": new_sl if new_sl is not None else pos.sl,
            "tp": new_tp if new_tp is not None else pos.tp,
        }

        result = mt5.order_send(request)
        return result is not None and result.retcode == mt5.TRADE_RETCODE_DONE


# Global MT5 service instance
mt5_service = MT5Service()
