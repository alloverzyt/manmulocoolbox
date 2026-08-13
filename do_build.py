import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("[LocalToolbox] 开始打包...")
result = subprocess.run(
    [sys.executable, '-m', 'PyInstaller', 'LocalToolbox.spec', '--clean', '--noconfirm'],
    capture_output=False,
    text=True
)

if result.returncode == 0:
    print("[LocalToolbox] 打包成功！")
    print("[LocalToolbox] 产物位置: dist/LocalToolbox.exe")
else:
    print(f"[LocalToolbox] 打包失败，退出码: {result.returncode}")
    sys.exit(1)
