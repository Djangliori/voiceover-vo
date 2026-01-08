# FFmpeg Installation Script for Windows
# Run this in PowerShell (NOT Git Bash)

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  FFmpeg Installation for Windows" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if ffmpeg is already installed
Write-Host "Checking if ffmpeg is already installed..." -ForegroundColor Yellow
$ffmpegExists = Get-Command ffmpeg -ErrorAction SilentlyContinue

if ($ffmpegExists) {
    Write-Host "✅ ffmpeg is already installed!" -ForegroundColor Green
    Write-Host "Version: " -NoNewline
    ffmpeg -version | Select-Object -First 1
    Write-Host ""
    Write-Host "Location: $($ffmpegExists.Source)" -ForegroundColor Green
    exit 0
}

Write-Host "❌ ffmpeg not found. Installing..." -ForegroundColor Red
Write-Host ""

# Method 1: Try winget (Windows Package Manager)
Write-Host "Attempting installation via winget..." -ForegroundColor Yellow
try {
    $wingetExists = Get-Command winget -ErrorAction SilentlyContinue
    if ($wingetExists) {
        Write-Host "Installing ffmpeg via winget..." -ForegroundColor Cyan
        winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements

        Write-Host ""
        Write-Host "✅ Installation complete!" -ForegroundColor Green
        Write-Host ""
        Write-Host "⚠️  IMPORTANT: You must CLOSE and REOPEN PowerShell for PATH to update!" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "After reopening, test with:" -ForegroundColor Cyan
        Write-Host "    ffmpeg -version" -ForegroundColor White
        exit 0
    }
} catch {
    Write-Host "❌ winget failed: $_" -ForegroundColor Red
}

# Method 2: Manual installation instructions
Write-Host ""
Write-Host "================================================" -ForegroundColor Yellow
Write-Host "  Manual Installation Required" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "Please follow these steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Download ffmpeg:" -ForegroundColor White
Write-Host "   https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Extract to: C:\ffmpeg" -ForegroundColor White
Write-Host ""
Write-Host "3. Add to PATH (copy and run this in PowerShell):" -ForegroundColor White
Write-Host '   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\ffmpeg\bin", "User")' -ForegroundColor Gray
Write-Host ""
Write-Host "4. Close and reopen PowerShell" -ForegroundColor White
Write-Host ""
Write-Host "5. Test: ffmpeg -version" -ForegroundColor White
Write-Host ""
