@echo off
cd /d "%~dp0"
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
    echo Installation failed. Check that Python 3 is installed.
) else (
    echo Dependencies installed. Run play_windows.bat to start.
)
pause
