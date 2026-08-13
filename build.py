import sys
import os
import subprocess
import ctypes
import winreg

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("  LocalToolbox - 一键打包 EXE")
print("=" * 50)
print()

# 1. 修改 PowerShell 执行策略（注册表方式，无需弹窗）
print("[0/3] 配置 PowerShell 执行策略...")
try:
    key = winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\PowerShell\1\ShellIds\Microsoft.PowerShell",
        0, winreg.KEY_SET_VALUE
    )
    winreg.SetValueEx(key, "ExecutionPolicy", 0, winreg.REG_SZ, "RemoteSigned")
    winreg.CloseKey(key)
    print("  ✅ 执行策略已设置 (RemoteSigned)")
except Exception as e:
    print(f"  ⚠️ 策略设置需要手动: {e}")

# 2. 检查 PyInstaller
print()
print("[1/3] 检查依赖...")
try:
    import PyInstaller
    print(f"  ✅ PyInstaller {PyInstaller.__version__}")
except ImportError:
    print("  安装 PyInstaller...")
    r = subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], timeout=120)
    if r.returncode != 0:
        print("  ❌ PyInstaller 安装失败")
        sys.exit(1)

# 3. 清理旧文件
print()
print("[2/3] 清理旧文件...")
import shutil
for d in ['build', 'dist']:
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
print("  ✅ 已清理")

# 4. 打包
print()
print("[3/3] 打包中 (onefile 模式，可能需要几分钟)...")
print("  请耐心等待...")
r = subprocess.run(
    [sys.executable, '-m', 'PyInstaller', 'LocalToolbox.spec', '--clean', '--noconfirm'],
    timeout=600
)

if r.returncode == 0:
    exe = 'dist/满木工具箱.exe'
    if os.path.isfile(exe):
        size_mb = os.path.getsize(exe) / 1048576
        print()
        print("=" * 50)
        print("  ✅ 打包成功！")
        print("=" * 50)
        print(f"  📦 文件: {exe}")
        print(f"  📏 大小: {size_mb:.1f} MB")
        print(f"  🚀 双击即可运行")
        print()
        print("  🛡️ 防误报:")
        print("     - 如杀毒弹窗，点'更多信息' → '仍要运行'")
        print("     - 可提交: https://www.microsoft.com/en-us/wdsi/filesubmission")
    else:
        print("  ⚠️ 产物未找到")
else:
    print(f"  ❌ 打包失败 (退出码 {r.returncode})")

print()
input("按回车退出...")
