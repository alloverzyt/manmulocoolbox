import os
import subprocess
import sys
from typing import Optional, List


def _app_resources_dir() -> str:
    """应用自带资源目录：开发模式为项目根/resources，打包后为 exe 旁 resources/"""
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), 'resources')
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'resources'
    )


def find_ffmpeg() -> Optional[str]:
    # 优先应用自带 FFmpeg（工具下载器从官方源安装的完整版），
    # 避免命中系统 PATH 中残缺或被其他软件替换的 ffmpeg.exe
    search_paths = [
        os.path.join(_app_resources_dir(), 'ffmpeg', 'bin', 'ffmpeg.exe'),
    ]

    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
        search_paths.append(os.path.join(base, 'ffmpeg.exe'))

    search_paths.append('ffmpeg')  # PATH 兜底

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
                 width: int = 480, start_time: str = "0", duration: str = "10",
                 ffmpeg_path: str = None) -> Optional[str]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return None

    cmd = [ffmpeg, '-y', '-i', input_path]

    # 起始时间 / 持续时长（用户可能填非法数字，解析失败则忽略）
    try:
        if start_time and float(start_time) > 0:
            cmd += ['-ss', str(start_time)]
    except (TypeError, ValueError):
        pass
    try:
        if duration and float(duration) > 0:
            cmd += ['-t', str(duration)]
    except (TypeError, ValueError):
        pass

    cmd += [
        '-vf', f'fps={fps},scale={width}:-1:flags=lanczos',
        '-preset', 'slow',
        output_path
    ]

    return _run_ffmpeg(cmd, output_path, "GIF生成")


def _audio_codec(fmt: str) -> str:
    """把输出格式映射为 ffmpeg 编码器名（容器格式名 ≠ 编码器名，如 wav→pcm_s16le、ogg→libvorbis）"""
    return {
        'mp3': 'libmp3lame',
        'wav': 'pcm_s16le',
        'aac': 'aac',
        'flac': 'flac',
        'ogg': 'libvorbis',
        'm4a': 'aac',
    }.get(fmt, fmt)


def extract_audio(input_path: str, output_path: str, format: str = 'mp3',
                  quality: int = 2, ffmpeg_path: str = None) -> Optional[str]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return None

    codec = _audio_codec(format)
    cmd = [
        ffmpeg, '-y', '-i', input_path,
        '-vn', '-acodec', codec,
    ]
    # 仅有损编码（mp3/aac/ogg）支持 -q:a VBR 质量；WAV/FLAC 无损编码不支持
    if codec in ('libmp3lame', 'aac', 'libvorbis'):
        cmd += ['-q:a', str(quality)]
    cmd.append(output_path)

    return _run_ffmpeg(cmd, output_path, "音频提取")


def convert_audio(input_path: str, output_path: str, bitrate: str = None,
                  ffmpeg_path: str = None) -> Optional[str]:
    ffmpeg = ffmpeg_path or find_ffmpeg()
    if not ffmpeg:
        return None

    cmd = [ffmpeg, '-y', '-i', input_path]

    # 仅对有损格式应用比特率；WAV/FLAC 等无损格式不支持 -b:a
    out_ext = os.path.splitext(output_path)[1].lower().lstrip('.')
    if bitrate and out_ext in ('mp3', 'aac', 'ogg', 'm4a', 'wma'):
        cmd += ['-b:a', bitrate]

    cmd.append(output_path)

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
