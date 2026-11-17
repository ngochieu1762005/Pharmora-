@echo off
setlocal
cd /d "%~dp0"
echo PharmaVision AI - Local Demo
echo Open http://127.0.0.1:8000 in your browser
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py server.py
) else (
  python server.py
)
pause
