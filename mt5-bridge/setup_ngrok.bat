@echo off
echo ==========================================
echo   Ngrok Setup for MT5 Bridge
echo ==========================================
echo.

REM Check if ngrok is installed
ngrok version >nul 2>&1
if errorlevel 1 (
    echo Error: ngrok not found!
    echo.
    echo Download ngrok from: https://ngrok.com/download
    echo Extract it and add to your PATH or this folder.
    echo.
    pause
    exit /b 1
)

echo Starting ngrok tunnel to localhost:5000...
echo.
echo Copy the https://xxxx.ngrok.io URL and update your
echo cloud backend MT5_BRIDGE_URL environment variable.
echo.

ngrok http 5000

pause
