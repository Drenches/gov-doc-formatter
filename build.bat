@echo off
chcp 65001 >nul
echo ================================================
echo   Build Script - GovDoc Formatter
echo ================================================
echo.
cd /d "%~dp0"

echo [1/5] Stopping related processes...
powershell -Command "Get-Process | Where-Object {$_.ProcessName -like '*公文*' -or $_.ProcessName -like '*python*'} | Stop-Process -Force -ErrorAction SilentlyContinue"
echo       Done
echo.

echo [2/5] Cleaning old files...
powershell -Command "Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue"
if exist "GovDocFormatter.zip" del /q "GovDocFormatter.zip"
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
powershell -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Compress-Archive -Path 'dist\公文自动排版工具' -DestinationPath 'GovDocFormatter.zip' -Force"
if errorlevel 1 (
    echo       Trying alternative method...
    powershell -Command "$folder = Get-ChildItem -Path 'dist' -Directory | Select-Object -First 1; if ($folder) { Compress-Archive -Path $folder.FullName -DestinationPath 'GovDocFormatter.zip' -Force }"
)
echo       Done
echo.

echo ================================================
echo   Build Complete!
echo   Output: GovDocFormatter.zip
echo ================================================
echo.
pause
