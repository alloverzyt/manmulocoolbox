import sys
import os
import subprocess
import hashlib
import tempfile
import shutil
import time
from typing import Dict, Optional, Callable
from PySide6.QtCore import QThread, Signal


DOWNLOAD_SOURCES = {
    "libreoffice": {
        "name": "LibreOffice",
        "description": "PPT转图片、Word/Excel转PDF",
        "size_mb": 350,
        "sources": [
            {
                # 腾讯云镜像：国内速度快、带宽足，URL 自动解析最新版本目录
                "name": "腾讯云镜像(自动选版本)",
                "url": "https://mirrors.cloud.tencent.com/libreoffice/libreoffice/stable/",
                "format": "msi"
            },
            {
                # 清华 TUNA 镜像：备选国内源
                # 注意镜像路径是 libreoffice/libreoffice/stable（TUNA 站点子路径嵌套）
                "name": "清华大学镜像(自动选版本)",
                "url": "https://mirrors.tuna.tsinghua.edu.cn/libreoffice/libreoffice/stable/",
                "format": "msi"
            },
            {
                "name": "官方镜像(自动选版本)",
                "url": "https://download.documentfoundation.org/libreoffice/stable/",
                "format": "msi"
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
                # gyan.dev 官方构建：直连可用但国内速度一般，作为保底源
                "name": "gyan.dev 构建",
                "url": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
                "format": "zip"
            },
            {
                # gh-proxy 代理 GitHub release：国内访问 GitHub 被墙/限速时使用
                "name": "BtbN 构建(gh-proxy镜像)",
                "url": "https://gh-proxy.com/https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
                "format": "zip"
            },
            {
                # 直连 GitHub：仅当国内网络可直接访问 GitHub 时有效
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

    def __init__(self, tool_key: str, parent=None, selected_sources: Optional[list] = None):
        super().__init__(parent)
        self.tool_key = tool_key
        self._cancelled = False
        # 用户选定的下载源（探测后选择），None 表示按配置顺序全部尝试
        self._selected_sources = selected_sources or []

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

        sources = self._selected_sources or config["sources"]

        for source in sources:
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
        fmt = source.get("format", "zip")

        # 官方镜像 / 清华 TUNA 镜像：先解析最新版本目录，得到真实 MSI 下载地址
        # （已是完整 .msi 地址的源直接跳过解析，避免二次请求目录页）
        if fmt in ("msi", "msi_tuna") and not url.lower().endswith(".msi"):
            url = self._resolve_tuna_libreoffice_url(url)
            if not url:
                raise RuntimeError("无法解析 LibreOffice 最新版本")
            self.progress.emit(10, f"正在下载 {url.split('/')[-1]}")

        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })

            temp_file = os.path.join(tempfile.gettempdir(), f"localtoolbox_{self.tool_key}_download.tmp")

            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 65536
                start_time = time.time()
                last_emit = 0.0

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
                        now = time.time()
                        speed = downloaded / 1024 / 1024 / max(now - start_time, 0.001)
                        # 节流：至少每 0.2 秒才刷新一次进度，避免高频信号卡 UI
                        if now - last_emit < 0.2:
                            continue
                        last_emit = now
                        if total_size > 0:
                            pct = 10 + int((downloaded / total_size) * 60)
                            self.progress.emit(
                                pct,
                                f"下载中 {pct}% · {downloaded // 1024 // 1024}MB/{total_size // 1024 // 1024}MB · {speed:.1f}MB/s"
                            )
                        else:
                            # 服务器未返回总大小（Content-Length 缺失）：
                            # 不能停在 10%，按已下载大小估算推进，让用户看到在动
                            pct = min(70, 10 + int(downloaded / 1024 / 1024 / 5))
                            self.progress.emit(
                                pct,
                                f"下载中 {pct}% · {downloaded // 1024 // 1024}MB · {speed:.1f}MB/s"
                            )

            self.progress.emit(75, "下载完成，正在解压...")

            if fmt == "zip":
                self._extract_zip(temp_file, target_dir)
            elif fmt == "archive":
                self._extract_portable_exe(temp_file, target_dir, config)
            elif fmt in ("msi", "msi_tuna"):
                # 三种 LibreOffice 源的 format 均为 "msi"；此前只有 "msi_tuna" 分支，
                # 导致下载完的 MSI 无人解包、直接删除后又被判失败
                self._extract_msi(temp_file, target_dir)

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

    def _resolve_tuna_libreoffice_url(self, base_url: str) -> Optional[str]:
        """解析镜像中 LibreOffice 最新稳定版 MSI 下载地址（官方镜像与 TUNA 结构一致）"""
        import re
        import urllib.request
        req = urllib.request.Request(base_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", "ignore")
        versions = re.findall(r'href="(\d+\.\d+\.\d+)/"', html)
        if not versions:
            return None
        latest = max(versions, key=lambda v: tuple(int(x) for x in v.split(".")))
        return f"{base_url}{latest}/win/x86_64/LibreOffice_{latest}_Win_x86-64.msi"

    def _extract_msi(self, msi_path: str, target_dir: str):
        """用 msiexec 管理安装(administrative install)解包 MSI 到目标目录，得到可运行的文件树"""
        import subprocess
        result = subprocess.run(
            ["msiexec", "/a", msi_path, "/qn", f"TARGETDIR={target_dir}"],
            capture_output=True, text=True, timeout=600
        )
        if result.returncode not in (0, 3010):  # 3010 = 成功但需重启，忽略
            raise RuntimeError(f"msiexec 解包失败: {result.returncode} {result.stderr[:200]}")

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


def probe_sources(tool_key: str, timeout: float = 6.0) -> list:
    """
    并发探测所有下载源的可达性，返回 [{name, url, ok, error}]。

    用于下载前先检测哪些源可用，再让用户选择。每个源独立超时，
    最多等待约 timeout 秒；服务器不支持 HEAD 时回退 GET+Range 只读少量字节。
    """
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor

    if tool_key not in DOWNLOAD_SOURCES:
        return []

    def _probe_one(source: Dict) -> Dict:
        url = source["url"]
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        # 1) HEAD 请求：镜像目录页 / 文件直链均可
        try:
            req = urllib.request.Request(url, headers=headers, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return {"name": source["name"], "url": url, "ok": True, "error": ""}
        except Exception as e1:
            pass
        # 2) GET + Range：部分服务器/镜像不支持 HEAD
        try:
            h2 = dict(headers)
            h2["Range"] = "bytes=0-2047"
            req2 = urllib.request.Request(url, headers=h2)
            with urllib.request.urlopen(req2, timeout=timeout) as resp:
                resp.read(256)
                return {"name": source["name"], "url": url, "ok": True, "error": ""}
        except Exception as e2:
            return {"name": source["name"], "url": url, "ok": False, "error": str(e2)[:80]}

    config = DOWNLOAD_SOURCES[tool_key]
    sources = config["sources"]
    if not sources:
        return []
    with ThreadPoolExecutor(max_workers=len(sources)) as ex:
        return list(ex.map(_probe_one, sources))


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
    installed = os.path.isfile(exe_full)

    if not installed and getattr(sys, 'frozen', False):
        # 单文件 EXE 内置的版本（_MEIPASS 内），如打包进 EXE 的 ffmpeg
        meipass = getattr(sys, '_MEIPASS', '')
        if meipass:
            bundled = os.path.join(meipass, "resources", config["install_dir_name"], config["exe_path"])
            if os.path.isfile(bundled):
                installed = True
                exe_full = bundled

    return {
        "key": tool_key,
        "name": config["name"],
        "description": config["description"],
        "size_mb": config["size_mb"],
        "installed": installed,
        "install_dir": install_dir,
        "exe_path": exe_full,
        "sources": config["sources"]
    }


def get_all_tool_status() -> Dict:
    result = {}
    for key in DOWNLOAD_SOURCES:
        result[key] = get_download_info(key)
    return result
