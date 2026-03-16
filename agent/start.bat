@echo off
title AutoFlip Autonomous Agent
echo ============================================
echo   AutoFlip Autonomous Agent
echo   Runs 24/7 - max $10/day Anthropic API
echo   Reports: agent\reports\YYYY-MM-DD.md
echo   Keys needed: agent\api_requests.md
echo ============================================
echo.

cd /d "%~dp0\.."

echo Pulling latest state from GitHub...
git pull origin main --rebase

echo.
echo Installing agent dependencies...
py -m pip install -r agent\requirements.txt -q

echo.
echo Starting agent... Press Ctrl+C to stop.
echo Reports are written to agent\reports\ daily.
echo.

py -X utf8 agent\run.py

pause
