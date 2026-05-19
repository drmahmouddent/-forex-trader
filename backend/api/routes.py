"""
API Routes
FastAPI endpoints for the forex trading dashboard
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, List
import json
import logging

from services.trading_engine import trading_engine
from services.mt5_service import mt5_service
from services.news_monitor import news_monitor
from services.risk_manager import risk_manager
from strategies.strategy_manager import strategy_manager
from config.settings import config

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Engine Control ==========

@router.post("/engine/start")
async def start_engine():
    """Start the trading engine"""
    success = trading_engine.start()
    if success:
        return {"status": "started", "message": "Trading engine started successfully"}
    raise HTTPException(status_code=400, detail="Failed to start engine")


@router.post("/engine/stop")
async def stop_engine():
    """Stop the trading engine"""
    trading_engine.stop()
    return {"status": "stopped", "message": "Trading engine stopped"}


@router.post("/engine/emergency-stop")
async def emergency_stop():
    """Emergency stop - close all trades"""
    trading_engine.emergency_stop()
    return {"status": "emergency_stopped", "message": "All trades closed, engine stopped"}


@router.get("/engine/status")
async def get_engine_status():
    """Get current engine status"""
    return trading_engine.get_status()


# ========== Account ==========

@router.get("/account")
async def get_account_info():
    """Get MT5 account information"""
    if not mt5_service.connected:
        raise HTTPException(status_code=503, detail="Not connected to MT5")
    return mt5_service.get_account_info()


# ========== Positions ==========

@router.get("/positions")
async def get_positions():
    """Get all open positions"""
    if not mt5_service.connected:
        return []
    positions = mt5_service.get_open_positions()
    return [
        {
            "ticket": p.ticket,
            "symbol": p.symbol,
            "type": p.type,
            "volume": p.volume,
            "open_price": p.open_price,
            "current_price": p.current_price,
            "profit": p.profit,
            "sl": p.sl,
            "tp": p.tp,
            "open_time": p.open_time.isoformat()
        }
        for p in positions
    ]


@router.post("/positions/{ticket}/close")
async def close_position(ticket: int):
    """Close a specific position"""
    result = mt5_service.close_trade(ticket)
    if result.success:
        return {"status": "closed", "message": result.message}
    raise HTTPException(status_code=400, detail=result.message)


@router.post("/positions/close-all")
async def close_all_positions():
    """Close all open positions"""
    results = mt5_service.close_all_trades()
    return {
        "closed": len(results),
        "results": [{"success": r.success, "message": r.message} for r in results]
    }


# ========== News ==========

@router.get("/news")
async def get_news():
    """Get upcoming news events"""
    return {
        "blackout_active": news_monitor.is_blackout_active(),
        "blackout_reason": news_monitor.get_blackout_reason(),
        "next_high_impact": news_monitor.get_next_high_impact(),
        "events": news_monitor.get_upcoming_events(hours=48)
    }


@router.post("/news/refresh")
async def refresh_news():
    """Force refresh news events"""
    news_monitor.update_events()
    return {"status": "refreshed", "events": len(news_monitor.events)}


# ========== Risk ==========

@router.get("/risk")
async def get_risk_status():
    """Get risk management status"""
    account = mt5_service.get_account_info()
    balance = account['balance'] if account else 0
    return {
        "summary": risk_manager.get_risk_summary(balance),
        "stats": risk_manager.get_trade_stats()
    }


# ========== Strategies ==========

@router.get("/strategies")
async def get_strategies():
    """Get strategy status"""
    return strategy_manager.get_strategy_status()


@router.post("/strategies/{name}/enable")
async def enable_strategy(name: str):
    """Enable a strategy"""
    if strategy_manager.enable_strategy(name):
        return {"status": "enabled", "strategy": name}
    raise HTTPException(status_code=404, detail=f"Strategy {name} not found")


@router.post("/strategies/{name}/disable")
async def disable_strategy(name: str):
    """Disable a strategy"""
    if strategy_manager.disable_strategy(name):
        return {"status": "disabled", "strategy": name}
    raise HTTPException(status_code=404, detail=f"Strategy {name} not found")


# ========== Config ==========

@router.get("/config")
async def get_config():
    """Get current configuration"""
    return {
        "pair": config.pair.symbol,
        "timeframe": config.pair.timeframe.name,
        "risk_per_trade": config.risk.account_risk_per_trade,
        "max_daily_loss": config.risk.max_daily_loss,
        "max_weekly_loss": config.risk.max_weekly_loss,
        "max_open_trades": config.risk.max_open_trades,
        "news_filter_enabled": config.news.enabled,
        "news_buffer_minutes": config.news.high_impact_buffer_minutes
    }


@router.post("/config")
async def update_config(updates: Dict):
    """Update configuration"""
    try:
        if "risk_per_trade" in updates:
            config.risk.account_risk_per_trade = float(updates["risk_per_trade"])
        if "max_daily_loss" in updates:
            config.risk.max_daily_loss = float(updates["max_daily_loss"])
        if "max_weekly_loss" in updates:
            config.risk.max_weekly_loss = float(updates["max_weekly_loss"])
        if "max_open_trades" in updates:
            config.risk.max_open_trades = int(updates["max_open_trades"])
        if "news_filter_enabled" in updates:
            config.news.enabled = bool(updates["news_filter_enabled"])
        if "news_buffer_minutes" in updates:
            config.news.high_impact_buffer_minutes = int(updates["news_buffer_minutes"])

        return {"status": "updated", "config": await get_config()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== Manual Trade ==========

@router.post("/trade/manual")
async def manual_trade(trade_type: str, sl_pips: float, tp_pips: float, lot_size: float = 0.01):
    """Execute a manual trade"""
    if trade_type not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="Type must be BUY or SELL")

    result = mt5_service.open_trade(
        symbol=config.pair.symbol,
        trade_type=trade_type,
        sl_pips=sl_pips,
        tp_pips=tp_pips,
        lot_size=lot_size,
        comment="Manual trade"
    )

    if result.success:
        return {"status": "opened", "order_id": result.order_id, "message": result.message}
    raise HTTPException(status_code=400, detail=result.message)


# ========== Price Data ==========

@router.get("/price/{symbol}")
async def get_price(symbol: str = "EURUSD"):
    """Get current price"""
    price = mt5_service.get_current_price(symbol)
    if price:
        return {"symbol": symbol, "bid": price[0], "ask": price[1]}
    raise HTTPException(status_code=503, detail="Failed to get price")


# ========== WebSocket for Live Updates ==========

class ConnectionManager:
    """WebSocket connection manager"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


ws_manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live updates"""
    await ws_manager.connect(websocket)

    # Register callback for engine updates
    async def send_update(data):
        await ws_manager.broadcast(data)

    trading_engine.register_ws_callback(lambda data: send_update(data))

    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif message.get("type") == "get_status":
                status = trading_engine.get_status()
                await websocket.send_json({"type": "status", "data": status})

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
