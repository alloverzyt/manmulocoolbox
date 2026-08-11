import urllib.request
import os
import sys
import subprocess

print("=" * 50)
print("  正在为你下载 Python 3.11...")
print("=" * 50)
print()

# Python 3.11.9 官方安装包（稳定版）
url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
installer = os.path.join(os.environ.get('TEMP', '.'), 'python_installer.exe')

print(f"下载地址: {url}")
print(f"保存到: {installer}")
print()

try:
    print("正在下载...")
    urllib.request.urlretrieve(url, installer)
    print("✅ 下载完成！")
    print()
    print("正在启动安装程序...")
    print("⚠️ 安装时请勾选 'Add Python to PATH'")
    print()
    
    # 自动运行安装程序
    os.startfile(installer)
    
    print("安装程序已启动，请按提示完成安装。")
    print()
    print("安装完成后，双击 build_exe.bat 即可生成 EXE。")
    
except Exception as e:
    print(f"下载失败: {e}")
    print()
    print("请手动下载:")
    print(f"  {url}")
    print()
    print("下载后双击运行，安装时勾选 'Add Python to PATH'")

print()
input("按回车退出...")
