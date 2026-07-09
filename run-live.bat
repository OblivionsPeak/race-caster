@echo off
rem Live mode: attach the booth to a running iRacing session (race or spectate).
cd /d %~dp0
venv\Scripts\python.exe racecaster.py
pause
