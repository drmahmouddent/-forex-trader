"""
MT5 Bridge Service
Runs locally on Windows with MT5 terminal
Exposes REST API for cloud backend to call
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import MetaTrader5 as mt5
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MT5 Bridge", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
connected = False


class MT5Config(BaseModel):
    login: int
    password: str
    server: str
    path: str = r"C:\Program Files\MetaTrader 5\terminal64.exe"


class TradeRequest(BaseModel):
    symbol: str
    trade_type: str  # "BUY" or "SELL"
    volume: float
    sl: float
    tp: float
    magic: int = 202505
    comment: str = ""


class ModifyRequest(BaseModel):
    ticket: int
    sl: Optional[float] = None
    tp: Optional[float] = None


# ========== Connection ==========

@app.post("/connect")
async def connect_mt5(config: MT5Config):
    """Connect to MT5 terminal"""
    global connected

    if not mt5.initialize(
        path=config.path,
        login=config.login,
        password=config.password,
        server=config.server,
        timeout=60000
    ):
        error = mt5.last_error()
        logger.error(f"MT5 init failed: {error}")
        raise HTTPException(status_code=500, detail=f"MT5 connection failed: {error}")

    connected = True
    account = mt5.account_info()
    logger.info(f"Connected to MT5: Account #{account.login}")

    return {
        "status": "connected",
        "account": {
            "login": account.login,
            "balance": account.balance,
            "equity": account.equity,
            "margin": account.margin,
            "free_margin": account.margin_free,
            "profit": account.profit,
            "leverage": account.leverage,
            "currency": account.currency
        }
    }


@app.post("/disconnect")
async def disconnect_mt5():
    """Disconnect from MT5 terminal"""
    global connected
    mt5.shutdown()
    connected = False
    logger.info("Disconnected from MT5")
    return {"status": "disconnected"}


@app.get("/status")
async def get_status():
    """Check MT5 connection status"""
    if not connected:
        return {"connected": False}

    account = mt5.account_info()
    if account is None:
        return {"connected": False}

    return {
        "connected": True,
        "account": {
            "login": account.login,
            "balance": account.balance,
            "equity": account.equity,
            "margin": account.margin,
            "free_margin": account.margin_free,
            "profit": account.profit,
            "leverage": account.leverage,
            "currency": account.currency
        }
    }


# ========== Account ==========

@app.get("/account")
async def get_account():
    """Get account information"""
    if not connected:
        raise HTTPException(status_code=503, detail="Not connected to MT5")

    account = mt5.account_info()
    if account is None:
        raise HTTPException(status_code=500, detail="Failed to get account info")

    return {
        "login": account.login,
        "balance": account.balance,
        "equity": account.equity,
        "margin": account.margin,
        "free_margin": account.margin_free,
        "profit": account.profit,
        "leverage": account.leverage,
        "currency": account.currency
    }


# ========== Market Data ==========

@app.get("/price/{symbol}")
async def get_price(symbol: str):
    """Get current bid/ask price"""
    if not connected:
        raise HTTPException(status_code=503, detail="Not connected to MT5")

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

    return {
        "symbol": symbol,
        "bid": tick.bid,
        "ask": tick.ask,
        "spread": (tick.ask - tick.bid) * 10000
    }


@app.get("/ohlcv/{symbol}")
async def get_ohlcv(symbol: str, timeframe: int = 15, count: int = 500):
    """Get OHLCV data"""
    if not connected:
        raise HTTPException(status_code=503, detail="Not connected to MT5")

    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    if rates is None or len(rates) == 0:
        raise HTTPException(status_code=500, detail="Failed to get OHLCV data")

    return [
        {
            "time": int(r['time']),
            "open": r['open'],
            "high": r['high'],
            "low": r['low'],
            "close": r['close'],
            "volume": r['tick_volume']
        }
        for r in rates
    ]


# ========== Trading ==========

@app.post("/trade/open")
async def open_trade(req: TradeRequest):
    """Open a new trade"""
    if not connected:
        raise HTTPException(status_code=503, detail="Not connected to MT5")

    # Get current price
    tick = mt5.symbol_info_tick(req.symbol)
    if tick is None:
        raise HTTPException(status_code=404, detail=f"Symbol {req.symbol} not found")

    # Determine order type and price
    if req.trade_type == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
        sl = price - req.sl * 0.0001
        tp = price + req.tp * 0.0001
    elif req.trade_type == "SELL":
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
        sl = price + req.sl * 0.0001
        tp = price - req.tp * 0.0001
    else:
        raise HTTPException(status_code=400, detail="Type must be BUY or SELL")

    # Prepare request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": req.symbol,
        "volume": req.volume,
        "type": order_type,
        "price": price,
        "sl": round(sl, 5),
        "tp": round(tp, 5),
        "magic": req.magic,
        "comment": req.comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # Send order
    result = mt5.order_send(request)

    if result is None:
        raise HTTPException(status_code=500, detail=f"Order failed: {mt5.last_error()}")

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise HTTPException(
            status_code=400,
            detail=f"Order rejected: {result.comment} (code: {result.retcode})"
        )

    logger.info(f"Trade opened: {req.trade_type} {req.volume} {req.symbol} @ {price}")

    return {
        "success": True,
        "order_id": result.order,
        "price": price,
        "sl": round(sl, 5),
        "tp": round(tp, 5)
    }


@app.post("/trade/close/{ticket}")
async def close_trade(ticket: int):
    """Close a trade by ticket"""
    if not connected:
        raise HTTPException(status_code=503, detail="Not connected to MT5")

    position = mt5.positions_get(ticket=ticket)
    if position is None or len(position) == 0:
        raise HTTPException(status_code=404, detail=f"Position #{ticket} not found")

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
        "magic": pos.magic,
        "comment": "Close by bridge",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        msg = result.comment if result else str(mt5.last_error())
        raise HTTPException(status_code=400, detail=f"Close failed: {msg}")

    logger.info(f"Position #{ticket} closed @ {price}")

    return {
        "success": True,
        "ticket": ticket,
        "price": price,
        "profit": pos.profit
    }


@app.post("/trade/close-all")
async def close_all_trades():
    """Close all open positions"""
    if not connected:
        raise HTTPException(status_code=503, detail="Not connected to MT5")

    positions = mt5.positions_get()
    if positions is None or len(positions) == 0:
        return {"closed": 0, "results": []}

    results = []
    for pos in positions:
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
            "position": pos.ticket,
            "price": price,
            "magic": pos.magic,
            "comment": "Close all",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        results.append({
            "ticket": pos.ticket,
            "success": result is not None and result.retcode == mt5.TRADE_RETCODE_DONE,
            "profit": pos.profit
        })

    return {"closed": len(results), "results": results}


@app.post("/trade/modify")
async def modify_trade(req: ModifyRequest):
    """Modify SL/TP of a trade"""
    if not connected:
        raise HTTPException(status_code=503, detail="Not connected to MT5")

    position = mt5.positions_get(ticket=req.ticket)
    if position is None or len(position) == 0:
        raise HTTPException(status_code=404, detail=f"Position #{req.ticket} not found")

    pos = position[0]

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": pos.symbol,
        "position": req.ticket,
        "sl": req.sl if req.sl is not None else pos.sl,
        "tp": req.tp if req.tp is not None else pos.tp,
    }

    result = mt5.order_send(request)

    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        raise HTTPException(status_code=400, detail="Modification failed")

    return {"success": True, "ticket": req.ticket}


# ========== Positions ==========

@app.get("/positions")
async def get_positions():
    """Get all open positions"""
    if not connected:
        return []

    positions = mt5.positions_get()
    if positions is None:
        return []

    return [
        {
            "ticket": p.ticket,
            "symbol": p.symbol,
            "type": "BUY" if p.type == 0 else "SELL",
            "volume": p.volume,
            "open_price": p.price_open,
            "current_price": p.price_current,
            "profit": p.profit,
            "sl": p.sl,
            "tp": p.tp,
            "time": p.time,
            "magic": p.magic,
            "comment": p.comment
        }
        for p in positions
    ]


@app.get("/positions/{magic}")
async def get_positions_by_magic(magic: int):
    """Get positions filtered by magic number"""
    if not connected:
        return []

    positions = mt5.positions_get()
    if positions is None:
        return []

    return [
        {
            "ticket": p.ticket,
            "symbol": p.symbol,
            "type": "BUY" if p.type == 0 else "SELL",
            "volume": p.volume,
            "open_price": p.price_open,
            "current_price": p.price_current,
            "profit": p.profit,
            "sl": p.sl,
            "tp": p.tp,
            "time": p.time,
            "comment": p.comment
        }
        for p in positions
        if p.magic == magic
    ]


# ========== Health ==========

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "connected": connected}


# ========== Main ==========

if __name__ == "__main__":
    logger.info("Starting MT5 Bridge Service...")
    uvicorn.run(app, host="0.0.0.0", port=5000)
