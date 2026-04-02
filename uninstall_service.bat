@echo off
echo ============================================
echo  Poshmark Bot - Service Uninstaller
echo ============================================
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: This script must be run as Administrator.
    echo Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

echo Stopping PoshmarkBot service...
nssm stop PoshmarkBot >nul 2>&1

echo Removing PoshmarkBot service...
nssm remove PoshmarkBot confirm >nul 2>&1

echo.
echo Service removed. The bot is no longer running.
pause
