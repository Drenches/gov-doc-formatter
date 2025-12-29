@echo off
chcp 65001 >nul
echo ================================================
echo   公文自动排版工具 - 一键打包脚本
echo ================================================
echo.

cd /d "%~dp0"

echo [1/4] 清理旧文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "公文自动排版工具.zip" del /q "公文自动排版工具.zip"
echo       完成

echo.
echo [2/4] 生成图标...
if not exist app.ico (
    python create_icon.py
) else (
    echo       图标已存在，跳过
)

echo.
echo [3/4] 执行 PyInstaller 打包...
pyinstaller gw-formatter.spec
if errorlevel 1 (
    echo.
    echo 错误：打包失败！
    pause
    exit /b 1
)
echo       完成

echo.
echo [4/4] 压缩成 ZIP...
powershell -Command "Compress-Archive -Path 'dist\公文自动排版工具' -DestinationPath '公文自动排版工具.zip' -Force"
echo       完成

echo.
echo ================================================
echo   打包完成！
echo   输出文件: 公文自动排版工具.zip
echo ================================================
echo.
pause
