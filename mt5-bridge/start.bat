@echo off
echo ==========================================
echo   MT5 Bridge Service - Starting...
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

REM Check if MT5 is running
tasklist /FI "IMAGENAME eq terminal64.exe" 2>NUL | find /I /N "terminal64.exe">NUL
if errorlevel 1 (
    echo Warning: MetaTrader 5 terminal not detected!
    echo Please start MetaTrader 5 before running this bridge.
    echo.
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Starting MT5 Bridge on http://localhost:5000
echo.
echo Keep this window open while trading.
echo Press Ctrl+C to stop.
echo.

python bridge.py

pause
