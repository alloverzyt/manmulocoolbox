import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# 打包前清理可能污染产物/构建的环境变量：
# - PYTHONHOME/PYTHONPATH 会被 PyInstaller 收集流程带偏，且 onefile 运行时
#   bootloader 若继承到错误 PYTHONHOME，用户机器上会报 Python path configuration
# - _MEIPASS2 是运行期变量，这里清理以防开发环境残留
for _v in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "_MEIPASS2"):
    os.environ.pop(_v, None)

print("[LocalToolbox] 开始打包...")
result = subprocess.run(
    [sys.executable, '-m', 'PyInstaller', 'LocalToolbox.spec', '--clean', '--noconfirm'],
    capture_output=False,
    text=True,
    env=os.environ.copy()
)

if result.returncode == 0:
    print("[LocalToolbox] 打包成功！")
    print("[LocalToolbox] 产物位置: dist/满木工具箱_v1.3.9.exe")
else:
    print(f"[LocalToolbox] 打包失败，退出码: {result.returncode}")
    sys.exit(1)
