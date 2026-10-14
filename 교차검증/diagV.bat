@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0runV.ps1" -DiagOnly
echo.
pause
