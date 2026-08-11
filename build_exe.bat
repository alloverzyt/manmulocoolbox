@echo off
chcp 65001 >nul 2>&1
title LocalToolbox - 生成 EXE
cd /d "%~dp0"

echo.
echo  ================================================
echo    LocalToolbox  一键打包为 EXE
echo  ================================================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [错误] 未检测到 Python，请先安装 Python 3.11+
    echo  下载: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo  [1/4] 检查依赖...
python -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo  正在安装 PyInstaller...
    python -m pip install pyinstaller
    if %errorlevel% neq 0 (
        echo  [错误] 安装失败
        pause
        exit /b 1
    )
)
echo  完成
echo.

echo  [2/4] 清理旧文件...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
echo  完成
echo.

echo  [3/4] 打包中 (可能需要几分钟)...
python -m PyInstaller LocalToolbox.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo.
    echo  [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo  [4/4] 验证产物...
if not exist "dist\LocalToolbox.exe" (
    echo  [错误] 未找到 exe
    pause
    exit /b 1
)

for %%A in ("dist\LocalToolbox.exe") do set SIZE=%%~zA
set /a SIZEMB=%SIZE%/1048576

echo.
echo  ================================================
echo    ✅ 打包成功！
echo  ================================================
echo.
echo    位置: dist\LocalToolbox.exe
echo    大小: %SIZEMB% MB
echo.
echo    💡 双击 exe 即可运行
echo.
echo    🛡️ 防误报:
echo      - 首次如弹窗提示"未知发布者"，点击"更多信息"→"仍要运行"
echo      - 可提交误报申请:
echo        https://www.microsoft.com/en-us/wdsi/filesubmission
echo.

start "" "explorer" "dist"

pause
