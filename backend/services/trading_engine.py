"""
Trading Engine
Main orchestrator that connects strategies, risk management, news, and MT5
"""

import asyncio
import threading
import time
from datetime import datetime
from typing import Optional, Dict, List
import logging

from config.settings import config
from services.mt5_cloud_service import mt5_cloud_service as mt5_service
from services.news_monitor import news_monitor
from services.risk_manager import risk_manager, TradeRecord
from strategies.strategy_manager import strategy_manager

logger = logging.getLogger(__name__)


class TradingEngine:
    """Main trading engine that runs the bot"""

    def __init__(self):
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._check_interval = 60  # Check every 60 seconds
        self.last_signal = None
        self.last_trade_time = None
        self.total_trades = 0
        self.status = "STOPPED"
        self._ws_callbacks = []  # WebSocket callbacks for live updates

    def start(self):
        """Start the trading engine"""
        if self.running:
            logger.warning("Trading engine already running")
            return False

        # Connect to MT5
        if not mt5_service.connected:
            if not mt5_service.connect():
                self.status = "ERROR: MT5 Connection Failed"
                return False

        # Start news monitor
        news_monitor.start()

        # Start trading loop
        self.running = True
        self.status = "RUNNING"
        self._thread = threading.Thread(target=self._trading_loop, daemon=True)
        self._thread.start()

        logger.info("Trading engine started")
        self._notify_update({"type": "engine_status", "status": "RUNNING"})
        return True

    def stop(self):
        """Stop the trading engine"""
        self.running = False
        self.status = "STOPPING"

        if self._thread:
            self._thread.join(timeout=30)

        # Optionally close all positions
        # mt5_service.close_all_trades()

        self.status = "STOPPED"
        logger.info("Trading engine stopped")
        self._notify_update({"type": "engine_status", "status": "STOPPED"})

    def emergency_stop(self):
        """Emergency stop - close all trades and stop engine"""
        logger.warning("EMERGENCY STOP triggered")
        self.status = "EMERGENCY STOP"

        # Close all open positions
        results = mt5_service.close_all_trades()
        for r in results:
            logger.info(f"Emergency close: {r.message}")

        self.running = False
        self._notify_update({"type": "emergency_stop", "closed_trades": len(results)})

    def _trading_loop(self):
        """Main trading loop"""
        while self.running:
            try:
                self._check_cycle()
                time.sleep(self._check_interval)
            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                time.sleep(30)

    def _check_cycle(self):
        """Single check cycle - analyze market and potentially trade"""
        # Get account info
        account = mt5_service.get_account_info()
        if account is None:
            logger.error("Failed to get account info")
            return

        balance = account['balance']

        # Check risk limits
        can_trade, risk_reason = risk_manager.can_trade(balance)
        if not can_trade:
            logger.info(f"Trading blocked: {risk_reason}")
            self._notify_update({"type": "risk_block", "reason": risk_reason})
            return

        # Get open positions
        positions = mt5_service.get_open_positions()

        # Check if we already have max positions
        if len(positions) >= config.risk.max_open_trades:
            logger.debug("Max open trades reached, monitoring only")
            self._monitor_positions(positions)
            return

        # Get market data
        timeframe_map = {
            1: 1, 5: 5, 15: 15, 30: 30, 60: 16385, 240: 16388, 1440: 16408
        }
        mt5_timeframe = timeframe_map.get(config.pair.timeframe.value, 15)

        df = mt5_service.get_ohlcv(
            symbol=config.pair.symbol,
            timeframe=mt5_timeframe,
            count=500
        )

        if df is None:
            logger.error("Failed to get market data")
            return

        # Run strategies
        signal = strategy_manager.analyze_all(df)

        if signal is None:
            logger.debug("No signal from strategies")
            return

        # Validate with risk manager
        open_count = len(positions)
        approved, risk_msg, lot_size = risk_manager.validate_trade(
            balance, open_count, signal.sl_pips, signal.strategy
        )

        if not approved:
            logger.info(f"Trade rejected by risk manager: {risk_msg}")
            return

        # Execute trade
        self._execute_trade(signal, lot_size)

    def _execute_trade(self, signal, lot_size: float):
        """Execute a trade based on signal"""
        logger.info(
            f"Executing {signal.type} trade: {signal.strategy} | "
            f"SL:{signal.sl_pips} TP:{signal.tp_pips} | Lots:{lot_size}"
        )

        result = mt5_service.open_trade(
            symbol=config.pair.symbol,
            trade_type=signal.type,
            sl_pips=signal.sl_pips,
            tp_pips=signal.tp_pips,
            lot_size=lot_size,
            comment=f"{signal.strategy}:{signal.confidence:.2f}"
        )

        if result.success:
            self.total_trades += 1
            self.last_trade_time = datetime.utcnow()
            self.last_signal = signal

            logger.info(f"Trade opened successfully: {result.message}")

            self._notify_update({
                "type": "trade_opened",
                "trade": {
                    "order_id": result.order_id,
                    "type": signal.type,
                    "strategy": signal.strategy,
                    "entry_price": result.price,
                    "sl_pips": signal.sl_pips,
                    "tp_pips": signal.tp_pips,
                    "lot_size": lot_size,
                    "confidence": signal.confidence,
                    "reason": signal.reason
                }
            })
        else:
            logger.warning(f"Trade failed: {result.message}")
            self._notify_update({"type": "trade_failed", "reason": result.message})

    def _monitor_positions(self, positions):
        """Monitor open positions for trailing stop, etc."""
        for pos in positions:
            # Check if position is in profit and adjust trailing stop
            if pos.profit > 0:
                # Simple trailing stop: move SL to breakeven after 20 pips profit
                profit_pips = pos.profit / (pos.volume * 10)  # Approximate

                if profit_pips > 20 and pos.sl != pos.open_price:
                    if pos.type == "BUY":
                        new_sl = pos.open_price + 0.0010  # Breakeven + 1 pip
                    else:
                        new_sl = pos.open_price - 0.0010

                    mt5_service.modify_sl_tp(pos.ticket, new_sl=new_sl)
                    logger.info(f"Trailing stop updated for #{pos.ticket}: SL -> {new_sl:.5f}")

    def get_status(self) -> Dict:
        """Get current engine status"""
        account = mt5_service.get_account_info() if mt5_service.connected else None
        positions = mt5_service.get_open_positions() if mt5_service.connected else []

        return {
            "status": self.status,
            "running": self.running,
            "connected": mt5_service.connected,
            "account": account,
            "open_positions": len(positions),
            "total_trades": self.total_trades,
            "last_trade": self.last_trade_time.isoformat() if self.last_trade_time else None,
            "news_blackout": news_monitor.is_blackout_active(),
            "blackout_reason": news_monitor.get_blackout_reason(),
            "risk_summary": risk_manager.get_risk_summary(account['balance'] if account else 0),
            "strategies": strategy_manager.get_strategy_status()
        }

    def register_ws_callback(self, callback):
        """Register WebSocket callback for live updates"""
        self._ws_callbacks.append(callback)

    def _notify_update(self, data: dict):
        """Notify all WebSocket clients of an update"""
        for callback in self._ws_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(data))
                else:
                    callback(data)
            except Exception as e:
                logger.warning(f"WebSocket callback error: {e}")


# Global trading engine instance
trading_engine = TradingEngine()
