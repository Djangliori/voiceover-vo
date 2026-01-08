@echo off
REM ===================================
REM .env Backup Script
REM Creates timestamped backup of .env
REM ===================================

echo ====================================
echo   .env Backup Tool
echo ====================================
echo.

REM Check if .env exists
if not exist .env (
    echo [ERROR] .env file not found!
    echo Create .env first: copy .env.example .env
    pause
    exit /b 1
)

REM Create backup with timestamp
set timestamp=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set timestamp=%timestamp: =0%
set backup_file=.env.backup.%timestamp%

copy .env %backup_file%

if errorlevel 1 (
    echo [ERROR] Backup failed!
    pause
    exit /b 1
)

echo [OK] Backup created: %backup_file%
echo.

REM Show backup location
echo Backup saved to:
echo %CD%\%backup_file%
echo.

REM Optional: Create latest backup link
copy /Y .env .env.backup >nul 2>&1
echo [OK] Also saved as: .env.backup (latest)
echo.

echo ====================================
echo   Backup Complete!
echo ====================================
echo.
echo IMPORTANT: Keep this backup safe!
echo - Store in password manager
echo - Or keep on external drive
echo - NEVER commit to git!
echo.

REM Show backups
echo Current backups:
dir /B .env.backup* 2>nul
echo.

pause
