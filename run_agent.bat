@echo off
title Room Booking AI Agent
echo ============================================
echo   Room Booking AI Agent  ^|  HeyKoala
echo ============================================
echo.

:: Install dependencies if needed
pip install -r requirements.txt --quiet
playwright install chromium --quiet

:: Run the agent
python -m backend.main
pause
