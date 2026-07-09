@echo off
rem Hear the booth commentate a simulated race — no iRacing needed.
cd /d %~dp0
venv\Scripts\python.exe racecaster.py --demo
pause
