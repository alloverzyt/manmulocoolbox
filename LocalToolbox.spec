# -*- mode: python ; coding: utf-8 -*-
# LocalToolbox PyInstaller 打包配置
# 模式: onefile (单文件 exe)
# 目标: 生成单个 LocalToolbox.exe，双击即用
#
# 防误报优化:
# 1. onefile 单文件模式（用户体验最佳）
# 2. 版本信息 + 图标（显示产品名，避免"未知程序"）
# 3. 禁用 UPX（UPX 壳易被杀软标记）
# 4. 最小化依赖（减小体积，降低启发式匹配概率）
# 5. 无控制台窗口（用户体验）
#
# 注意: onefile 模式每次启动会解压到临时目录，
#       杀毒软件可能首次扫描，请添加白名单。

import os

# 动态收集所有插件模块（插件通过 importlib 字符串动态导入 src.plugins.*，
# PyInstaller 无法静态分析，必须显式加入 hiddenimports 并打包插件目录数据）
_plugin_modules = []
for _root, _dirs, _files in os.walk('src/plugins'):
    for _f in _files:
        if _f.endswith('.py') and not _f.startswith('_'):
            _rel = os.path.relpath(os.path.join(_root, _f), 'src')
            _plugin_modules.append(_rel[:-3].replace(os.sep, '.'))

# 动态收集 src/utils 模块：ffmpeg_helper / libreoffice_helper 在插件「函数内部延迟导入」，
# PyInstaller 依赖分析不可靠，必须显式 hiddenimports + datas 双保险
_utils_modules = []
for _f in os.listdir('src/utils'):
    if _f.endswith('.py') and not _f.startswith('_'):
        _utils_modules.append('src.utils.' + _f[:-3])

# 资源按文件逐一收集：目录级 ('resources','resources') 不会被 a.datas 展开成
# 单个文件条目，无法在 Analysis 之后过滤。这里直接跳过打包版用不到的
# ffplay.exe/ffprobe.exe（各约 140MB，应用只调用 ffmpeg.exe）与源图 满木_raw.png。
def _collect_resources():
    entries = []
    for _r, _dirs, _files in os.walk('resources'):
        for _f in _files:
            if _f in ('ffplay.exe', 'ffprobe.exe', '满木_raw.png'):
                continue
            _src = os.path.join(_r, _f)
            entries.append((_src, os.path.dirname(_src)))
    return entries


a = Analysis(
    ['run.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('config/plugin_config.json', 'config'),
        *_collect_resources(),
        ('CHANGELOG.md', '.'),
        # 插件目录整体复制进解压目录：_load_all 需要 os.listdir 遍历真实目录
        ('src/plugins', 'src/plugins'),
        # utils 目录整体复制：函数内延迟导入的 ffmpeg_helper 等在解压目录可直接 import
        ('src/utils', 'src/utils'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
        'fitz',
        'PIL',
        'pypdf',
        'qrcode',
        'docx',
        'markdown',
        'yaml',
        'pyzbar',
        'reportlab',
        'img2pdf',
    ] + _plugin_modules + _utils_modules,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # GUI 框架 (只保留 PySide6)
        'PyQt5', 'PyQt6', 'PySide2', 'PyGTK', 'PyGObject', 'wx',
        # 不需要的 GUI 组件
        'tkinter', 'turtle',
        # 测试框架
        'unittest', 'pytest', 'test',
        # Jupyter/IPython
        'IPython', 'jupyter', 'notebook', 'sphinx',
        # Web 框架
        'django', 'flask', 'fastapi', 'starlette', 'bottle', 'cherrypy',
        # 爬虫/自动化
        'scrapy', 'selenium', 'playwright',
        # 科学计算 (已用 numpy/pandas, 排除 scipy)
        'scipy', 'sympy',
        # 机器学习
        'sklearn', 'tensorflow', 'torch', 'torchvision', 'xgboost', 'lightgbm',
        # 可选依赖不打包（体积控制）：pdf2docx→numpy+opencv 会增大 EXE 160MB 以上。
        # 这些在源码运行 / 依赖管理页可 pip 安装，打包版里对应工具会提示"未安装"。
        'pdf2docx', 'numpy', 'pandas', 'openpyxl',
        'cv2', 'opencv', 'opencv_python', 'opencv-python-headless',
        'rembg', 'onnxruntime', 'onnxruntime-gpu',
        # 数据库
        'pymysql', 'psycopg2', 'sqlalchemy',
        # 消息队列
        'redis', 'celery', 'kafka', 'pika',
        # 网络
        'twisted', 'paramiko', 'fabric',
        # 服务器
        'http.server', 'xmlrpc',
        # Python 工具 (不需要打包)
        'pydoc', 'doctest', 'lib2to3', 'ensurepip',
        'venv', 'zipapp',
        # 声音/音频
        'audioop', 'wave', 'aifc', 'ossaudiodev', 'winsound',
        # 系统工具
        'profile', 'cProfile', 'pstats',
        'distutils', 'setuptools', 'pip', 'wheel',
        'pkg_resources', 'easy_install',
        # 可选 GUI 后端
        'PIL._tkinter_finder',
        # 重复项
        'idle_test',
        # PySide6 用不到的 Qt 模块（每个可省数 MB~10+MB，体积优化）
        'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuickWidgets',
        'PySide6.QtQmlModels', 'PySide6.QtQmlWorkerScript', 'PySide6.QtQmlMeta',
        'PySide6.QtVirtualKeyboard', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
        'PySide6.QtNetwork',
    ],
    noarchive=False,
)

# ===== Qt 瘦身：手工过滤用不到的 Qt 动态库 =====
# excludes 对 Qt6*.dll 无效（PySide6 的 hook 按目录 glob 收集全部 dll），
# 必须在收集完成后按文件名过滤 binaries。
_skip_qt_dlls = (
    'Qt6Qml', 'Qt6Quick', 'Qt6QmlModels', 'Qt6QmlMeta', 'Qt6QmlWorkerScript',
    'Qt6VirtualKeyboard', 'Qt6Pdf', 'Qt6Network',
)
_bin_before = len(a.binaries)
a.binaries = [
    b for b in a.binaries
    if not (b[0].startswith('PySide6\\') and any(s in b[0] for s in _skip_qt_dlls))
]
print(f"[spec] Qt 瘦身: 二进制 {_bin_before} -> {len(a.binaries)}")

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LocalToolbox',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon='resources/app.ico',
)
