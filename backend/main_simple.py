"""
Forex Trader - Simple Backend
Minimal version that works on Render free tier
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import json
from datetime import datetime

app = FastAPI(title="Forex Trader API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory storage
trading_state = {
    "running": False,
    "positions": [],
    "balance": 10000.0,
    "daily_pnl": 0.0,
    "weekly_pnl": 0.0,
    "total_trades": 0,
    "last_update": None
}


@app.get("/")
async def root():
    return {"status": "running", "service": "Forex Trader API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/engine/status")
async def engine_status():
    return {
        "status": "RUNNING" if trading_state["running"] else "STOPPED",
        "running": trading_state["running"],
        "connected": True,
        "account": {
            "balance": trading_state["balance"],
            "equity": trading_state["balance"],
            "margin": 0,
            "free_margin": trading_state["balance"],
            "profit": trading_state["daily_pnl"],
            "leverage": 100,
            "currency": "USD"
        },
        "open_positions": len(trading_state["positions"]),
        "total_trades": trading_state["total_trades"],
        "news_blackout": False,
        "blackout_reason": "",
        "risk_summary": {
            "daily_pnl": trading_state["daily_pnl"],
            "daily_limit": 500.0,
            "daily_remaining": 500.0 + trading_state["daily_pnl"],
            "daily_percent": (trading_state["daily_pnl"] / trading_state["balance"]) * 100,
            "weekly_pnl": trading_state["weekly_pnl"],
            "weekly_limit": 1000.0,
            "weekly_remaining": 1000.0 + trading_state["weekly_pnl"],
            "weekly_percent": (trading_state["weekly_pnl"] / trading_state["balance"]) * 100,
            "news_blackout": False,
            "blackout_reason": ""
        },
        "strategies": [
            {"name": "London Breakout", "enabled": True},
            {"name": "Trend Following", "enabled": True},
            {"name": "Support/Resistance", "enabled": True}
        ]
    }


@app.post("/api/engine/start")
async def start_engine():
    trading_state["running"] = True
    trading_state["last_update"] = datetime.utcnow().isoformat()
    return {"status": "started", "message": "Trading engine started"}


@app.post("/api/engine/stop")
async def stop_engine():
    trading_state["running"] = False
    return {"status": "stopped", "message": "Trading engine stopped"}


@app.post("/api/engine/emergency-stop")
async def emergency_stop():
    trading_state["running"] = False
    trading_state["positions"] = []
    return {"status": "emergency_stopped", "message": "All positions closed"}


@app.get("/api/positions")
async def get_positions():
    return trading_state["positions"]


@app.post("/api/positions/{ticket}/close")
async def close_position(ticket: int):
    trading_state["positions"] = [p for p in trading_state["positions"] if p.get("ticket") != ticket]
    return {"status": "closed", "ticket": ticket}


@app.post("/api/positions/close-all")
async def close_all():
    trading_state["positions"] = []
    return {"status": "closed_all"}


@app.get("/api/news")
async def get_news():
    return {
        "blackout_active": False,
        "blackout_reason": "",
        "next_high_impact": None,
        "events": []
    }


@app.post("/api/news/refresh")
async def refresh_news():
    return {"status": "refreshed", "events": 0}


@app.get("/api/risk")
async def get_risk():
    return {
        "summary": {
            "daily_pnl": trading_state["daily_pnl"],
            "daily_limit": 500.0,
            "daily_remaining": 500.0 + trading_state["daily_pnl"],
            "daily_percent": (trading_state["daily_pnl"] / trading_state["balance"]) * 100,
            "weekly_pnl": trading_state["weekly_pnl"],
            "weekly_limit": 1000.0,
            "weekly_remaining": 1000.0 + trading_state["weekly_pnl"],
            "weekly_percent": (trading_state["weekly_pnl"] / trading_state["balance"]) * 100,
            "news_blackout": False,
            "blackout_reason": ""
        },
        "stats": {
            "total_trades": trading_state["total_trades"],
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
    }


@app.get("/api/strategies")
async def get_strategies():
    return [
        {"name": "London Breakout", "enabled": True},
        {"name": "Trend Following", "enabled": True},
        {"name": "Support/Resistance", "enabled": True}
    ]


@app.post("/api/strategies/{name}/enable")
async def enable_strategy(name: str):
    return {"status": "enabled", "strategy": name}


@app.post("/api/strategies/{name}/disable")
async def disable_strategy(name: str):
    return {"status": "disabled", "strategy": name}


@app.get("/api/config")
async def get_config():
    return {
        "pair": "EURUSD",
        "timeframe": "M15",
        "risk_per_trade": 0.02,
        "max_daily_loss": 0.05,
        "max_weekly_loss": 0.10,
        "max_open_trades": 3,
        "news_filter_enabled": True,
        "news_buffer_minutes": 30
    }


@app.post("/api/config")
async def update_config(updates: dict):
    return {"status": "updated", "config": await get_config()}


@app.post("/api/trade/manual")
async def manual_trade(trade_type: str, sl_pips: float, tp_pips: float, lot_size: float = 0.01):
    return {"status": "opened", "order_id": 12345, "message": f"{trade_type} {lot_size} lots"}


@app.get("/api/price/{symbol}")
async def get_price(symbol: str = "EURUSD"):
    return {"symbol": symbol, "bid": 1.0850, "ask": 1.0852}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
