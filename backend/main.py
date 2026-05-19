"""
Forex Trader - Main Application
EUR/USD Automated Trading System with News Filter
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from pathlib import Path

from api.routes import router
from config.settings import config

# Setup logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(config.log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Forex Trader",
    description="EUR/USD Automated Trading System with News Filter",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "Forex Trader",
        "version": "1.0.0",
        "status": "running",
        "pair": config.pair.symbol
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import os
    logger.info("Starting Forex Trader...")
    logger.info(f"Trading {config.pair.symbol} on {config.pair.timeframe.name} timeframe")
    port = int(os.environ.get("PORT", config.api_port))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
