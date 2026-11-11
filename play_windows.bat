@echo off
cd /d "%~dp0"
py -3 tetris.py
if errorlevel 1 (
    echo.
    echo Cannot start Tetris Deluxe. Install pygame first:
    echo py -3 -m pip install -r requirements.txt
    pause
)
