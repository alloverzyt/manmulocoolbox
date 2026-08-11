@echo off
chcp 65001 >nul 2>&1
title LocalToolbox - 本地工具箱
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     🧰 LocalToolbox  一键启动脚本        ║
echo  ║        本地文件处理工具箱                  ║
echo  ╚══════════════════════════════════════════╝
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [错误] 未检测到 Python，请先安装 Python 3.10+
    echo  下载地址: https://www.python.org/downloads/
    echo.
    echo  安装时请勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  [信息] 检测到 %PYVER%
echo.

if not exist "venv" (
    echo  [步骤1] 正在创建虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo  [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo  [完成] 虚拟环境创建成功
    echo.
)

echo  [步骤2] 激活虚拟环境...
call venv\Scripts\activate.bat
echo  [完成] 已激活 venv
echo.

echo  [步骤3] 检查并安装依赖...
echo  这可能需要几分钟，取决于网络速度...
echo.

python -c "import sys; sys.path.insert(0, '.'); from src.core.dependency_manager import check_all_dependencies, install_all_missing_essential; r = check_all_dependencies(); print(f'  已有: {r[\"installed\"]}/{r[\"total\"]} 个依赖'); missing = [d for d in r['python'] if not d['installed'] and d.get('essential')]; import sys; sys.exit(0 if not missing else 1)"

if %errorlevel% neq 0 (
    echo  [提示] 检测到缺失的核心依赖，正在安装...
    python -m pip install --upgrade pip
    python -m pip install PySide6 PyMuPDF Pillow pypdf qrcode[pil] python-docx python-markdown pyyaml pyzbar pdf2docx reportlab img2pdf
    if %errorlevel% neq 0 (
        echo  [警告] 部分依赖安装失败，尝试继续...
    )
    echo  [完成] 核心依赖安装完成
) else (
    echo  [完成] 所有核心依赖已就绪
)

echo.
echo  [步骤4] 启动 LocalToolbox...
echo.
python run.py

if %errorlevel% neq 0 (
    echo.
    echo  [错误] 程序异常退出
    echo  请查看上方错误信息
    echo.
    pause
)
