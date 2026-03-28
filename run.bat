@echo off
title OwO HuntBot Auto-Upgrader

echo ===================================================
echo     OwO HuntBot Auto-Upgrader
echo ===================================================
echo.

if not exist tokens.txt (
    echo [ERROR] tokens.txt not found!
    echo Creating tokens.example.txt...
    copy tokens.example.txt tokens.txt >nul
    echo Please edit tokens.txt and add your Discord tokens, then restart.
    pause
    goto end
)

set /p channel_id="Enter Discord Channel ID: "
echo.
echo Starting bot...
python auto_huntbot.py --channel %channel_id%
pause

:end
