import sys
import os
import subprocess
import hashlib
import tempfile
import shutil
from typing import Dict, Optional, Callable
from PySide6.QtCore import QThread, Signal


DOWNLOAD_SOURCES = {
    "libreoffice": {
        "name": "LibreOffice",
        "description": "PPT转图片、Word/Excel转PDF",
        "size_mb": 350,
        "sources": [
            {
                "name": "官方镜像",
                "url": "https://download.libreoffice.org/",
                "format": "archive"
            }
        ],
        "portable_archive_pattern": "LibreOffice*_Portable*.exe",
        "install_dir_name": "libreoffice",
        "exe_path": "program/soffice.exe",
        "fallback_hint": "请访问 https://www.libreoffice.org/download/ 下载便携版"
    },
    "ffmpeg": {
        "name": "FFmpeg",
        "description": "视频转GIF、提取音频、格式转换",
        "size_mb": 80,
        "sources": [
            {
                "name": "gyan.dev 构建",
                "url": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
                "format": "zip"
            },
            {
                "name": "BtbN 构建",
                "url": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
                "format": "zip"
            }
        ],
        "install_dir_name": "ffmpeg",
        "exe_path": "bin/ffmpeg.exe",
        "fallback_hint": "请访问 https://ffmpeg.org/download.html 下载 Windows 版本"
    }
}


class ToolDownloader(QThread):
    progress = Signal(int, str)
    finished_ok = Signal(str, str)
    finished_error = Signal(str)
    status_msg = Signal(str)

    def __init__(self, tool_key: str, parent=None):
        super().__init__(parent)
        self.tool_key = tool_key
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        if self.tool_key not in DOWNLOAD_SOURCES:
            self.finished_error.emit(f"未知工具: {self.tool_key}")
            return

        config = DOWNLOAD_SOURCES[self.tool_key]
        tool_name = config["name"]

        base_dir = self._get_base_dir()
        target_dir = os.path.join(base_dir, config["install_dir_name"])

        self.status_msg.emit(f"准备下载 {tool_name}...")
        self.progress.emit(5, "初始化下载环境")

        os.makedirs(target_dir, exist_ok=True)

        for source in config["sources"]:
            if self._cancelled:
                self.finished_error.emit("用户取消")
                return

            try:
                self.status_msg.emit(f"尝试从 {source['name']} 下载...")
                success = self._download_and_extract(source, target_dir, config)
                if success:
                    self.progress.emit(100, f"{tool_name} 安装完成")
                    exe_full_path = os.path.join(target_dir, config["exe_path"])
                    self.finished_ok.emit(self.tool_key, exe_full_path)
                    return
            except Exception as e:
                self.status_msg.emit(f"源失败: {str(e)[:100]}")
                continue

        self.finished_error.emit(
            f"所有下载源均失败。\n\n"
            f"请手动下载 {tool_name}:\n"
            f"{config['fallback_hint']}\n\n"
            f"解压到: {target_dir}"
        )

    def _get_base_dir(self) -> str:
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, "resources")

    def _download_and_extract(self, source: Dict, target_dir: str, config: Dict) -> bool:
        import urllib.request
        import zipfile
        import tarfile

        url = source["url"]
        self.progress.emit(10, f"正在下载 {url.split('/')[-1]}")

        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })

            temp_file = os.path.join(tempfile.gettempdir(), f"localtoolbox_{self.tool_key}_download.tmp")

            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 8192

                with open(temp_file, "wb") as f:
                    while True:
                        if self._cancelled:
                            f.close()
                            os.remove(temp_file)
                            return False
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = 10 + int((downloaded / total_size) * 60)
                            self.progress.emit(pct, f"下载中... {downloaded // 1024 // 1024}MB")

            self.progress.emit(75, "下载完成，正在解压...")

            if source["format"] == "zip":
                self._extract_zip(temp_file, target_dir)
            elif source["format"] == "archive":
                self._extract_portable_exe(temp_file, target_dir, config)

            os.remove(temp_file)
            self.progress.emit(95, "验证安装...")

            exe_path = os.path.join(target_dir, config["exe_path"])
            if os.path.isfile(exe_path):
                return True

            self._fix_libreoffice_structure(target_dir, config)
            exe_path = os.path.join(target_dir, config["exe_path"])
            return os.path.isfile(exe_path)

        except Exception as e:
            self.status_msg.emit(f"下载失败: {str(e)[:150]}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            return False

    def _extract_zip(self, zip_path: str, target_dir: str):
        import zipfile
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)

        for root, dirs, files in os.walk(target_dir):
            for d in dirs:
                dpath = os.path.join(root, d)
                if d.lower().endswith("libreoffice") or d.lower().endswith("ffmpeg"):
                    if root != target_dir:
                        for item in os.listdir(dpath):
                            shutil.move(os.path.join(dpath, item), os.path.join(target_dir, item))
                        shutil.rmtree(dpath, ignore_errors=True)
                    return

    def _extract_portable_exe(self, exe_path: str, target_dir: str, config: Dict):
        self.progress.emit(78, "运行安装程序（可能需要用户交互）...")

        import subprocess
        result = subprocess.run(
            [exe_path, "/S", f"/D={target_dir}"],
            capture_output=True, text=True, timeout=120, shell=True
        )

        self._fix_libreoffice_structure(target_dir, config)

    def _fix_libreoffice_structure(self, target_dir: str, config: Dict):
        for root, dirs, files in os.walk(target_dir):
            for d in dirs:
                dpath = os.path.join(root, d)
                program_dir = os.path.join(dpath, "program")
                if os.path.isdir(program_dir):
                    for item in os.listdir(dpath):
                        if item != "program":
                            src = os.path.join(dpath, item)
                            dst = os.path.join(target_dir, item)
                            if not os.path.exists(dst):
                                shutil.move(src, dst)
                    break


def get_download_info(tool_key: str) -> Optional[Dict]:
    if tool_key not in DOWNLOAD_SOURCES:
        return None
    config = DOWNLOAD_SOURCES[tool_key]
    base_dir = None
    if getattr(sys, 'frozen', False):
        base_dir = os.path.join(os.path.dirname(sys.executable), "resources")
    else:
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")

    install_dir = os.path.join(base_dir, config["install_dir_name"])
    exe_full = os.path.join(install_dir, config["exe_path"])

    return {
        "key": tool_key,
        "name": config["name"],
        "description": config["description"],
        "size_mb": config["size_mb"],
        "installed": os.path.isfile(exe_full),
        "install_dir": install_dir,
        "exe_path": exe_full,
        "sources": config["sources"]
    }


def get_all_tool_status() -> Dict:
    result = {}
    for key in DOWNLOAD_SOURCES:
        result[key] = get_download_info(key)
    return result
