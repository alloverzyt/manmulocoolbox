import os
import subprocess
import sys
from typing import Optional, List


def find_ffmpeg() -> Optional[str]:
    search_paths = ['ffmpeg']

    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
        search_paths.insert(0, os.path.join(base, 'ffmpeg.exe'))

    for path in search_paths:
        try:
            result = subprocess.run(
                [path, '-version'], capture_output=True, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            if result.returncode == 0:
                return path
        except (FileNotFoundError, OSError):
            continue
    return None


def video_to_gif(input_path: str, output_path: str, fps: int = 10,
                 width: int = 480, ffmpeg_path: str = None) -> Optional[str]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return None

    cmd = [
        ffmpeg, '-y', '-i', input_path,
        '-vf', f'fps={fps},scale={width}:-1:flags=lanczos',
        '-preset', 'slow',
        output_path
    ]

    return _run_ffmpeg(cmd, output_path, "GIF生成")


def extract_audio(input_path: str, output_path: str, format: str = 'mp3',
                  ffmpeg_path: str = None) -> Optional[str]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return None

    cmd = [
        ffmpeg, '-y', '-i', input_path,
        '-vn', '-acodec', 'libmp3lame' if format == 'mp3' else format,
        '-q:a', '2',
        output_path
    ]

    return _run_ffmpeg(cmd, output_path, "音频提取")


def convert_audio(input_path: str, output_path: str, ffmpeg_path: str = None) -> Optional[str]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return None

    cmd = [ffmpeg, '-y', '-i', input_path, output_path]

    return _run_ffmpeg(cmd, output_path, "音频转换")


def _run_ffmpeg(cmd: List[str], output_path: str, action: str) -> Optional[str]:
    """执行 ffmpeg 命令；失败时抛出带真实错误输出的异常，便于插件透传原因"""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{action}超时(600秒)")
    except Exception as e:
        raise RuntimeError(f"{action}启动失败: {str(e)}")

    if result.returncode == 0 and os.path.isfile(output_path):
        return output_path

    # 提取 ffmpeg 最后的错误信息（stderr 末尾），帮助用户定位问题
    detail = ""
    if result.stderr:
        lines = [ln.strip() for ln in result.stderr.splitlines() if ln.strip()]
        detail = lines[-3:][0] if lines else ""
        if not detail and result.returncode != 0:
            detail = lines[-1] if lines else ""
    raise RuntimeError(f"{action}失败" + (f": {detail[:200]}" if detail else ""))
