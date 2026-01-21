@echo off
REM Build Windows onedir distribution for TikTokDownloader
REM This script installs dependencies and runs PyInstaller in onedir mode.

:: Ensure we're in the script's directory
cd /d %~dp0

echo Installing Python dependencies...
python -m pip install --upgrade pip > NUL 2>&1
python -m pip install -r requirements.txt pyinstaller > NUL 2>&1

echo Building onedir executable...
python -m PyInstaller --noconfirm --clean --windowed --name TikTokDownloader main.py

echo.
echo Build complete. The output can be found in the dist\TikTokDownloader folder.
pause