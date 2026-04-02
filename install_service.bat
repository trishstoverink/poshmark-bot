@echo off
echo ============================================
echo  Poshmark Bot - Windows Service Installer
echo ============================================
echo.

:: Check for admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: This script must be run as Administrator.
    echo Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

:: Install nssm if not present
where nssm >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing NSSM (Non-Sucking Service Manager)...
    powershell -Command "Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile '%TEMP%\nssm.zip'"
    powershell -Command "Expand-Archive -Path '%TEMP%\nssm.zip' -DestinationPath '%TEMP%\nssm' -Force"
    copy "%TEMP%\nssm\nssm-2.24\win64\nssm.exe" "C:\Windows\System32\nssm.exe" >nul
    echo NSSM installed.
)

:: Find Python
for /f "tokens=*" %%i in ('where py 2^>nul') do set PYTHON_PATH=%%i
if not defined PYTHON_PATH (
    for /f "tokens=*" %%i in ('where python 2^>nul') do set PYTHON_PATH=%%i
)
if not defined PYTHON_PATH (
    echo ERROR: Python not found. Please install Python first.
    pause
    exit /b 1
)
echo Found Python: %PYTHON_PATH%

set APP_DIR=%~dp0
set APP_PATH=%APP_DIR%app.py

:: Remove existing service if present
nssm stop PoshmarkBot >nul 2>&1
nssm remove PoshmarkBot confirm >nul 2>&1

:: Install the service
echo Installing PoshmarkBot service...
nssm install PoshmarkBot "%PYTHON_PATH%" "%APP_PATH%"
nssm set PoshmarkBot AppDirectory "%APP_DIR%"
nssm set PoshmarkBot DisplayName "Poshmark Bot"
nssm set PoshmarkBot Description "Auto-share and offer bot for Poshmark"
nssm set PoshmarkBot Start SERVICE_AUTO_START
nssm set PoshmarkBot AppStdout "%APP_DIR%service.log"
nssm set PoshmarkBot AppStderr "%APP_DIR%service.log"
nssm set PoshmarkBot AppRotateFiles 1
nssm set PoshmarkBot AppRotateBytes 1048576

:: Start the service
echo Starting PoshmarkBot service...
nssm start PoshmarkBot

echo.
echo ============================================
echo  Service installed and started!
echo  - Dashboard: http://localhost:5000
echo  - Starts automatically on boot
echo  - Logs: %APP_DIR%service.log
echo.
echo  To stop:    nssm stop PoshmarkBot
echo  To start:   nssm start PoshmarkBot
echo  To remove:  nssm remove PoshmarkBot confirm
echo ============================================
pause
