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

set APP_DIR=%~dp0
set NSSM=%APP_DIR%nssm-2.24\win64\nssm.exe
set APP_PATH=%APP_DIR%app.py

:: Check NSSM exists
if not exist "%NSSM%" (
    echo ERROR: nssm.exe not found at %NSSM%
    echo Please re-download the project from GitHub.
    pause
    exit /b 1
)

:: Find Python
set PYTHON_PATH=
for /f "tokens=*" %%i in ('where py 2^>nul') do if not defined PYTHON_PATH set PYTHON_PATH=%%i
if not defined PYTHON_PATH (
    for /f "tokens=*" %%i in ('where python 2^>nul') do if not defined PYTHON_PATH set PYTHON_PATH=%%i
)
if not defined PYTHON_PATH (
    echo ERROR: Python not found. Please install Python first.
    pause
    exit /b 1
)
echo Found Python: %PYTHON_PATH%

:: Remove existing service if present
"%NSSM%" stop PoshmarkBot >nul 2>&1
"%NSSM%" remove PoshmarkBot confirm >nul 2>&1

:: Install the service
echo Installing PoshmarkBot service...
"%NSSM%" install PoshmarkBot "%PYTHON_PATH%" "%APP_PATH%"
"%NSSM%" set PoshmarkBot AppDirectory "%APP_DIR%"
"%NSSM%" set PoshmarkBot DisplayName "Poshmark Bot"
"%NSSM%" set PoshmarkBot Description "Auto-share and offer bot for Poshmark"
"%NSSM%" set PoshmarkBot Start SERVICE_AUTO_START
"%NSSM%" set PoshmarkBot AppStdout "%APP_DIR%service.log"
"%NSSM%" set PoshmarkBot AppStderr "%APP_DIR%service.log"
"%NSSM%" set PoshmarkBot AppRotateFiles 1
"%NSSM%" set PoshmarkBot AppRotateBytes 1048576

:: Start the service
echo Starting PoshmarkBot service...
"%NSSM%" start PoshmarkBot

echo.
echo ============================================
echo  Service installed and started!
echo  - Dashboard: http://localhost:5000
echo  - Starts automatically on boot
echo  - Logs: %APP_DIR%service.log
echo.
echo  To stop:    "%NSSM%" stop PoshmarkBot
echo  To start:   "%NSSM%" start PoshmarkBot
echo  To remove:  "%NSSM%" remove PoshmarkBot confirm
echo ============================================
pause
