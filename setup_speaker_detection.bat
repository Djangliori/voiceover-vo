@echo off
REM Speaker Detection Setup Script for Windows

echo ================================================================
echo   Speaker Detection Setup
echo   Multi-voice Georgian Translation
echo ================================================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed!
    echo Please install Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo [OK] Docker is installed
echo.

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] docker-compose is not available!
    pause
    exit /b 1
)

echo [OK] docker-compose is available
echo.

echo Building speaker detection container...
echo This may take 5-10 minutes on first run...
echo.

docker-compose build speaker-detection

if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Container built successfully!
echo.

echo Starting speaker detection service...
docker-compose up -d speaker-detection

if errorlevel 1 (
    echo [ERROR] Failed to start service!
    pause
    exit /b 1
)

echo.
echo Waiting for service to be ready...
timeout /t 10 /nobreak >nul

REM Test service health
curl -s http://localhost:5002/health >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Service might not be ready yet. Check logs with:
    echo    docker logs voyoutube-speaker-detection
) else (
    echo [SUCCESS] Speaker detection service is running!
)

echo.
echo ================================================================
echo   Setup Complete!
echo ================================================================
echo.
echo Service URL: http://localhost:5002
echo.
echo Next steps:
echo   1. Add to .env file:
echo      SPEAKER_DETECTION_URL=http://localhost:5002
echo.
echo   2. Restart Flask app (it will auto-detect the service)
echo.
echo   3. Process a multi-speaker video
echo.
echo Check status: docker ps
echo View logs: docker logs voyoutube-speaker-detection
echo Stop service: docker-compose stop speaker-detection
echo.
pause
