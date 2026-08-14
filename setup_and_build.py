import sys
import os
import subprocess
import urllib.request
import winreg

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 50)
print("  LocalToolbox - 环境自动配置")
print("=" * 50)
print()

# 检查 Python 是否已安装
print("[检查] 检测 Python...")
try:
    result = subprocess.run([sys.executable, '--version'], capture_output=True, text=True)
    print(f"  ✅ Python 已就绪: {sys.executable}")
    print(f"  版本: {result.stdout.strip()}")
except:
    pass

# 尝试查找 python
python_paths = [
    sys.executable,
    r"C:\Users\31193\AppData\Local\Programs\Python\Python311\python.exe",
    r"C:\Users\31193\AppData\Local\Programs\Python\Python312\python.exe",
    r"C:\Program Files\Python311\python.exe",
    r"C:\Program Files\Python312\python.exe",
]

python_exe = None
for p in python_paths:
    if os.path.isfile(p):
        python_exe = p
        break

if not python_exe:
    # 检查注册表
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Python\PythonCore", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        i = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(key, i)
                subkey = winreg.OpenKey(key, subkey_name)
                install_path, _ = winreg.QueryValueEx(subkey, "InstallPath")
                candidate = os.path.join(install_path, "python.exe")
                if os.path.isfile(candidate):
                    python_exe = candidate
                    break
                i += 1
            except:
                break
        if python_exe:
            print(f"  ✅ 注册表找到: {python_exe}")
    except:
        pass

if not python_exe:
    # 当前解释器
    if sys.executable and os.path.isfile(sys.executable):
        python_exe = sys.executable
        print(f"  ✅ 使用当前: {python_exe}")

if not python_exe:
    print()
    print("  ⚠️ 未检测到 Python！")
    print()
    print("  请安装 Python 3.11+:")
    print("    方式1: winget install Python.Python.3.11")
    print("    方式2: https://www.python.org/downloads/")
    print()
    input("安装完成后按回车继续...")
    sys.exit(0)

# 设置环境
print()
print("[配置] 添加到 PATH...")
try:
    python_dir = os.path.dirname(python_exe)
    scripts_dir = os.path.join(python_dir, 'Scripts')
    
    current_path = os.environ.get('PATH', '')
    new_paths = [python_dir, scripts_dir]
    
    for p in new_paths:
        if p not in current_path:
            current_path = p + ';' + current_path
    
    os.environ['PATH'] = current_path
    print(f"  ✅ {python_dir}")
    print(f"  ✅ {scripts_dir}")
except Exception as e:
    print(f"  ⚠️ PATH 更新: {e}")

# 检查 pip
print()
print("[检查] 检测 pip...")
try:
    r = subprocess.run([python_exe, '-m', 'pip', '--version'], capture_output=True, text=True)
    print(f"  ✅ pip: {r.stdout.strip()}")
except:
    print("  安装 pip...")
    subprocess.run([python_exe, '-m', 'ensurepip', '--upgrade'], timeout=60)

# 检查 PyInstaller
print()
print("[检查] 检测 PyInstaller...")
try:
    import PyInstaller
    print(f"  ✅ PyInstaller {PyInstaller.__version__}")
except ImportError:
    print("  安装 PyInstaller...")
    r = subprocess.run([python_exe, '-m', 'pip', 'install', 'pyinstaller'], timeout=120)
    if r.returncode == 0:
        print("  ✅ PyInstaller 安装完成")
    else:
        print("  ❌ 安装失败")
        input("按回车退出...")
        sys.exit(1)

# 检查核心依赖
print()
print("[检查] 检测核心依赖...")
core_deps = ['PySide6', 'PyMuPDF', 'Pillow', 'pypdf', 'qrcode', 'python-docx', 'markdown', 'pyyaml', 'pyzbar', 'pdf2docx']
missing = []
for dep in core_deps:
    try:
        __import__(dep.replace('-', '_'))
    except ImportError:
        missing.append(dep)

if missing:
    print(f"  缺失: {', '.join(missing)}")
    print("  正在安装...")
    pip_names = ['PySide6', 'PyMuPDF', 'Pillow', 'pypdf', 'qrcode[pil]', 'python-docx', 'python-markdown', 'pyyaml', 'pyzbar', 'pdf2docx', 'reportlab', 'img2pdf']
    r = subprocess.run([python_exe, '-m', 'pip', 'install'] + pip_names, timeout=300)
    if r.returncode == 0:
        print("  ✅ 核心依赖安装完成")
    else:
        print("  ⚠️ 部分依赖安装可能需要手动处理")
else:
    print("  ✅ 核心依赖已就绪")

# 清理旧文件
print()
print("[清理] 清理旧文件...")
import shutil
for d in ['build', 'dist']:
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
print("  ✅ 已清理")

# 开始打包
print()
print("=" * 50)
print("  开始打包为 EXE...")
print("  （可能需要几分钟，请耐心等待）")
print("=" * 50)
print()

r = subprocess.run(
    [python_exe, '-m', 'PyInstaller', 'LocalToolbox.spec', '--clean', '--noconfirm'],
    timeout=600
)

if r.returncode == 0:
    exe_path = 'dist/满木工具箱_v1.3.9.exe'
    if os.path.isfile(exe_path):
        size_mb = os.path.getsize(exe_path) / 1048576
        print()
        print("=" * 50)
        print("  ✅ 打包成功！")
        print("=" * 50)
        print()
        print(f"  📦 产物: {os.path.abspath(exe_path)}")
        print(f"  📏 大小: {size_mb:.1f} MB")
        print(f"  🚀 双击即可运行！")
        print()
        print("  🛡️ 防误报提示:")
        print("     - 首次运行如弹窗提示，点击'更多信息'→'仍要运行'")
        print("     - 可提交误报: https://www.microsoft.com/en-us/wdsi/filesubmission")
        print()
        print("  📂 正在打开 dist 目录...")
        os.startfile('dist')
    else:
        print("  ⚠️ 产物未找到，请检查 build 目录日志")
else:
    print(f"  ❌ 打包失败 (退出码 {r.returncode})")

print()
input("按回车退出...")
