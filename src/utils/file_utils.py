import os
import shutil
from typing import List, Optional


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def get_output_dir(input_path: str, output_dir: str = "") -> str:
    if output_dir:
        return ensure_dir(output_dir)
    return os.path.dirname(os.path.abspath(input_path))


def get_filename(file_path: str) -> str:
    return os.path.splitext(os.path.basename(file_path))[0]


def get_extension(file_path: str) -> str:
    return os.path.splitext(file_path)[1].lower()


def list_files_from_dropped(data) -> List[str]:
    if hasattr(data, 'urls'):
        paths = []
        for url in data.urls():
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        return paths
    if hasattr(data, 'text'):
        text = data.text()
        if text:
            return [p.strip() for p in text.split('\n') if p.strip()]
    return []


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def is_image(file_path: str) -> bool:
    image_exts = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.gif', '.heic'}
    return get_extension(file_path).lower() in image_exts


def is_pdf(file_path: str) -> bool:
    return get_extension(file_path).lower() == '.pdf'


def is_video(file_path: str) -> bool:
    video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
    return get_extension(file_path).lower() in video_exts


def is_audio(file_path: str) -> bool:
    audio_exts = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'}
    return get_extension(file_path).lower() in audio_exts
