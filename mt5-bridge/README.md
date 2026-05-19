# MT5 Bridge Service

This bridge service runs locally on your Windows machine and connects MetaTrader 5 to your cloud-deployed forex trading bot.

## Why This Is Needed

- MetaTrader 5 only runs on Windows
- Your cloud backend runs on Linux (Google Cloud Run)
- This bridge exposes MT5 via HTTP so the cloud can call it

## Setup Instructions

### 1. Install Requirements

```bash
pip install -r requirements.txt
```

### 2. Start MetaTrader 5

Make sure MT5 is running and logged into your trading account.

### 3. Start the Bridge

Double-click `start.bat` or run:
```bash
python bridge.py
```

The bridge will start on `http://localhost:5000`

### 4. Expose to Internet with ngrok

Download ngrok from https://ngrok.com/download

In a new terminal:
```bash
ngrok http 5000
```

Copy the `https://xxxx.ngrok.io` URL.

### 5. Update Cloud Backend

Set the `MT5_BRIDGE_URL` environment variable in Google Cloud Run to your ngrok URL.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/connect` | POST | Connect to MT5 |
| `/disconnect` | POST | Disconnect from MT5 |
| `/status` | GET | Check connection status |
| `/account` | GET | Get account info |
| `/price/{symbol}` | GET | Get current price |
| `/ohlcv/{symbol}` | GET | Get OHLCV data |
| `/positions` | GET | Get open positions |
| `/trade/open` | POST | Open a trade |
| `/trade/close/{ticket}` | POST | Close a trade |
| `/trade/close-all` | POST | Close all trades |
| `/trade/modify` | POST | Modify SL/TP |

## Troubleshooting

- **MT5 not connecting**: Make sure MT5 is running and logged in
- **ngrok URL changed**: Update `MT5_BRIDGE_URL` in Cloud Run
- **Bridge crashes**: Check MT5 is still running, restart bridge
