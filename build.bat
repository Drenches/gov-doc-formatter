@echo off
chcp 65001 >nul
echo ================================================
echo   Build Script - GovDoc Formatter
echo ================================================
echo.
cd /d "%~dp0"

echo [1/5] Stopping related processes...
taskkill /F /IM "公文自动排版工具.exe" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *公文*" 2>nul
timeout /t 1 /nobreak >nul
echo       Done
echo.

echo [2/5] Cleaning old files...
if exist build rmdir /S /Q build 2>nul
timeout /t 1 /nobreak >nul
if exist dist rmdir /S /Q dist 2>nul
if exist "GovDocFormatter.zip" del /F /Q "GovDocFormatter.zip" 2>nul
if exist "temp_build.zip" del /F /Q "temp_build.zip" 2>nul
echo       Done
echo.

echo [3/5] Generating icon...
if not exist app.ico (
    python create_icon.py
) else (
    echo       Icon exists, skipping
)
echo.

echo [4/5] Running PyInstaller...
pyinstaller gw-formatter.spec
if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)
echo       Done
echo.

echo [5/5] Creating ZIP...
echo       Waiting for file system...
timeout /t 3 /nobreak >nul
cd dist
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; Compress-Archive -Path '公文自动排版工具' -DestinationPath '..\GovDocFormatter.zip' -CompressionLevel Optimal -Force"
cd ..
if exist "GovDocFormatter.zip" (
    echo       Done - GovDocFormatter.zip created
) else (
    echo       WARNING: ZIP creation failed
    echo       You can manually zip the 'dist\公文自动排版工具' folder
)
echo.

echo ================================================
echo   Build Complete!
echo   Output: GovDocFormatter.zip
echo ================================================
echo.
pause
