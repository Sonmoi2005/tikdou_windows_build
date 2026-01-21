@echo off
REM Build Windows single executable for TikTokDownloader
REM This script installs dependencies and runs PyInstaller in onefile mode.

:: Ensure we're in the script's directory
cd /d %~dp0

echo Installing Python dependencies...
python -m pip install --upgrade pip > NUL 2>&1
python -m pip install -r requirements.txt pyinstaller > NUL 2>&1

echo Building onefile executable...
python -m PyInstaller --noconfirm --clean --windowed --onefile --name TikTokDownloader main.py

echo.
echo Build complete. The output can be found in the dist folder as TikTokDownloader.exe.
pause