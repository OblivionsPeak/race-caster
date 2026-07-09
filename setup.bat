@echo off
rem One-time setup: creates a virtual environment and installs dependencies.
cd /d %~dp0
py -3.12 -m venv venv 2>nul || python -m venv venv
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
echo.
echo Setup complete. Try the booth with:  run-demo.bat
pause
