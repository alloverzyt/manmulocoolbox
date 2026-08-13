import sys
import os
import subprocess
import importlib
import json
from typing import Dict, List, Tuple, Optional


CORE_DEPENDENCIES = [
    {
        "name": "PySide6",
        "import_name": "PySide6",
        "pip_name": "PySide6>=6.6.0",
        "description": "Qt6 GUI框架",
        "essential": True
    },
    {
        "name": "PyMuPDF",
        "import_name": "fitz",
        "pip_name": "PyMuPDF>=1.24.0",
        "description": "PDF处理引擎",
        "essential": True
    },
    {
        "name": "Pillow",
        "import_name": "PIL",
        "pip_name": "Pillow>=10.0.0",
        "description": "图像处理库",
        "essential": True
    },
    {
        "name": "pypdf",
        "import_name": "pypdf",
        "pip_name": "pypdf>=4.0.0",
        "description": "PDF读写操作",
        "essential": False
    },
    {
        "name": "qrcode",
        "import_name": "qrcode",
        "pip_name": "qrcode[pil]>=7.4.0",
        "description": "二维码生成",
        "essential": False
    },
    {
        "name": "python-docx",
        "import_name": "docx",
        "pip_name": "python-docx>=1.0.0",
        "description": "Word文档操作",
        "essential": False
    },
    {
        "name": "python-markdown",
        "import_name": "markdown",
        "pip_name": "markdown>=3.5.0",
        "description": "Markdown解析",
        "essential": False
    },
    {
        "name": "PyYAML",
        "import_name": "yaml",
        "pip_name": "pyyaml>=6.0",
        "description": "YAML解析",
        "essential": False
    },
    {
        "name": "pyzbar",
        "import_name": "pyzbar",
        "pip_name": "pyzbar>=0.1.9",
        "description": "二维码识别",
        "essential": False
    },
    {
        "name": "pdf2docx",
        "import_name": "pdf2docx",
        "pip_name": "pdf2docx>=0.5.0",
        "description": "PDF转Word",
        "essential": False
    },
    {
        "name": "reportlab",
        "import_name": "reportlab",
        "pip_name": "reportlab>=4.0.0",
        "description": "PDF生成",
        "essential": False
    },
    {
        "name": "img2pdf",
        "import_name": "img2pdf",
        "pip_name": "img2pdf>=0.5.0",
        "description": "图片转PDF",
        "essential": False
    },
]


OPTIONAL_DEPENDENCIES = [
    {
        "name": "rembg",
        "import_name": "rembg",
        "pip_name": "rembg>=2.0.0",
        "description": "AI去除背景(首次使用下载模型)"
    },
    {
        "name": "cairosvg",
        "import_name": "cairosvg",
        "pip_name": "cairosvg>=2.5.0",
        "description": "SVG转PNG"
    },
    {
        "name": "pdfplumber",
        "import_name": "pdfplumber",
        "pip_name": "pdfplumber>=0.10.0",
        "description": "PDF表格提取"
    },
]

EXTERNAL_TOOLS = [
    {
        "name": "LibreOffice",
        "key": "libreoffice",
        "description": "PPT转图片、Word/Excel转PDF",
        "download_url": "https://www.libreoffice.org/download/download-libreoffice/",
        "portable_url": "https://www.libreoffice.org/download/portable/",
        "check_paths": [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ],
        "project_relative_path": "resources/libreoffice/program/soffice.exe"
    },
    {
        "name": "FFmpeg",
        "key": "ffmpeg",
        "description": "视频转GIF、提取音频",
        "download_url": "https://ffmpeg.org/download.html",
        "windows_url": "https://www.gyan.dev/ffmpeg/builds/",
        "check_paths": [],
        "project_relative_path": "resources/ffmpeg/bin/ffmpeg.exe"
    }
]


def check_python_dependency(dep: Dict) -> Tuple[bool, str]:
    """
    检查 Python 依赖是否已安装

    冻结环境(PyInstaller)下同样做真实导入检测：已内置的模块返回「已内置」；
    pdf2docx/rembg 等体积较大的可选依赖不在打包范围内，如实显示「未安装」。
    """
    try:
        importlib.import_module(dep["import_name"])
        if getattr(sys, 'frozen', False):
            return True, "已内置"
        return True, "已安装"
    except ImportError:
        if getattr(sys, 'frozen', False):
            return False, "未安装（未内置，仅源码版可用）"
        return False, "未安装"


def check_all_dependencies() -> Dict:
    result = {
        "python": [],
        "external": [],
        "all_essential_ok": True,
        "total": 0,
        "installed": 0,
        "missing_essential": []
    }

    for dep in CORE_DEPENDENCIES + OPTIONAL_DEPENDENCIES:
        installed, status = check_python_dependency(dep)
        dep_info = {**dep, "installed": installed, "status": status}
        result["python"].append(dep_info)
        result["total"] += 1
        if installed:
            result["installed"] += 1
        elif dep.get("essential", False):
            result["all_essential_ok"] = False
            result["missing_essential"].append(dep["name"])

    for tool in EXTERNAL_TOOLS:
        tool_info = {**tool, "installed": False, "status": "未检测到"}

        if getattr(sys, 'frozen', False):
            # 单文件 EXE 内置的版本（_MEIPASS）优先，其次 exe 旁 resources/
            candidates = []
            meipass = getattr(sys, '_MEIPASS', '')
            if meipass:
                candidates.append(meipass)
            candidates.append(os.path.dirname(sys.executable))
            base = None
            for c in candidates:
                p = os.path.join(c, tool["project_relative_path"])
                if os.path.isfile(p):
                    base = c
                    break
            if base is None:
                base = candidates[-1]
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        project_path = os.path.join(base, tool["project_relative_path"])
        if os.path.isfile(project_path):
            tool_info["installed"] = True
            tool_info["status"] = f"项目内置: {project_path}"
            result["external"].append(tool_info)
            continue

        for check_path in tool.get("check_paths", []):
            if os.path.isfile(check_path):
                tool_info["installed"] = True
                tool_info["status"] = f"系统安装: {check_path}"
                break

        if not tool_info["installed"]:
            tool_info["status"] = "未检测到(可选)"

        result["external"].append(tool_info)

    return result


def install_python_package(pip_name: str) -> Tuple[bool, str]:
    """
    安装 Python 包
    
    优先使用 --user 选项安装到用户目录，避免权限问题
    """
    try:
        # 先尝试用 --user 安装到用户目录（避免权限问题）
        cmd = [sys.executable, "-m", "pip", "install", "--user", pip_name]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            return True, "安装成功"
        
        # 如果 --user 失败，尝试普通安装
        if "WinError 5" in (result.stderr or "") or "PermissionError" in (result.stderr or ""):
            # 普通安装也可能失败，但先尝试
            cmd2 = [sys.executable, "-m", "pip", "install", pip_name]
            result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=300)
            if result2.returncode == 0:
                return True, "安装成功"
            return False, result2.stderr or result2.stdout
        
        return False, result.stderr or result.stdout
    except subprocess.TimeoutExpired:
        return False, "安装超时，请检查网络连接"
    except Exception as e:
        return False, str(e)


def install_all_missing_essential() -> Dict:
    results = {"success": [], "failed": [], "skipped": []}
    for dep in CORE_DEPENDENCIES:
        if dep.get("essential", False):
            installed, _ = check_python_dependency(dep)
            if not installed:
                ok, msg = install_python_package(dep["pip_name"])
                if ok:
                    results["success"].append(dep["name"])
                else:
                    results["failed"].append({"name": dep["name"], "error": msg})
    return results


def install_essential_dependencies() -> bool:
    """
    安装所有缺失的核心依赖，返回是否全部成功
    """
    result = install_all_missing_essential()
    return len(result["failed"]) == 0


def install_optional_package(pip_name: str) -> Tuple[bool, str]:
    return install_python_package(pip_name)


def ensure_runtime_env():
    result = check_all_dependencies()

    if not result["all_essential_ok"]:
        missing = result["missing_essential"]
        print(f"[LocalToolbox] 检测到缺失的核心依赖: {', '.join(missing)}")
        print("[LocalToolbox] 正在自动安装...")

        install_result = install_all_missing_essential()

        if install_result["failed"]:
            print(f"[LocalToolbox] 部分依赖安装失败: {[f['name'] for f in install_result['failed']]}")
            print(f"[LocalToolbox] 请手动运行: pip install {' '.join(d['pip_name'] for d in CORE_DEPENDENCIES if d['name'] in [f['name'] for f in install_result['failed']])}")
            return False

        if install_result["success"]:
            print(f"[LocalToolbox] 成功安装: {', '.join(install_result['success'])}")

    return True


if __name__ == "__main__":
    status = check_all_dependencies()
    print(json.dumps({
        "total": status["total"],
        "installed": status["installed"],
        "all_essential_ok": status["all_essential_ok"],
        "missing_essential": status["missing_essential"]
    }, indent=2, ensure_ascii=False))
