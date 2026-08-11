import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class ExtractAudioPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "extract_audio"

    @property
    def name(self) -> str:
        return "提取音频"

    @property
    def description(self) -> str:
        return "从视频文件中提取音频轨道"

    @property
    def category(self) -> str:
        return "media"

    @property
    def icon(self) -> str:
        return "media"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["mp4", "avi", "mov", "mkv", "webm", "flv", "wmv"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["mp3", "wav", "aac", "ogg", "flac"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "format": {
                "type": "select",
                "label": "输出格式",
                "default": "mp3",
                "options": [
                    {"label": "MP3 (通用)", "value": "mp3"},
                    {"label": "WAV (无损)", "value": "wav"},
                    {"label": "AAC", "value": "aac"},
                    {"label": "FLAC (无损)", "value": "flac"},
                    {"label": "OGG", "value": "ogg"}
                ]
            },
            "quality": {
                "type": "integer",
                "label": "音频质量(1-10)",
                "default": 2,
                "min": 1,
                "max": 10
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        from ...utils.ffmpeg_helper import find_ffmpeg, extract_audio

        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            return PluginResult(
                success=False,
                error="未检测到 FFmpeg。请安装 FFmpeg。"
            )

        file_path = input_data.file_paths[0]
        options = input_data.options
        format = options.get("format", "mp3")

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.{format}")

        try:
            result = extract_audio(file_path, output_path, format=format)
        except Exception as e:
            return PluginResult(success=False, error=str(e))

        if result and os.path.isfile(result):
            file_size = os.path.getsize(result)
            return PluginResult(
                success=True,
                output_paths=[result],
                message=f"音频提取成功 ({file_size // 1024}KB)"
            )
        else:
            return PluginResult(success=False, error="音频提取失败。请确保已安装 FFmpeg。")
