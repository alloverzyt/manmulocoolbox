import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class AudioConvertPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "audio_convert"

    @property
    def name(self) -> str:
        return "音频格式转换"

    @property
    def description(self) -> str:
        return "在MP3/WAV/FLAC/AAC/OGG等音频格式之间转换"

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
        return ["mp3", "wav", "flac", "aac", "ogg", "m4a", "wma"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["mp3", "wav", "flac", "aac", "ogg", "m4a"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "target_format": {
                "type": "select",
                "label": "目标格式",
                "default": "mp3",
                "options": [
                    {"label": "MP3", "value": "mp3"},
                    {"label": "WAV", "value": "wav"},
                    {"label": "FLAC (无损)", "value": "flac"},
                    {"label": "AAC", "value": "aac"},
                    {"label": "OGG", "value": "ogg"},
                    {"label": "M4A", "value": "m4a"}
                ]
            },
            "bitrate": {
                "type": "select",
                "label": "比特率",
                "default": "320k",
                "options": [
                    {"label": "128 kbps", "value": "128k"},
                    {"label": "192 kbps", "value": "192k"},
                    {"label": "256 kbps", "value": "256k"},
                    {"label": "320 kbps", "value": "320k"}
                ]
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        from ...utils.ffmpeg_helper import find_ffmpeg, convert_audio

        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            return PluginResult(
                success=False,
                error="未检测到 FFmpeg。请安装 FFmpeg。"
            )

        file_path = input_data.file_paths[0]
        options = input_data.options
        target_fmt = options.get("target_format", "mp3")

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.{target_fmt}")

        try:
            result = convert_audio(file_path, output_path)
        except Exception as e:
            return PluginResult(success=False, error=str(e))

        if result and os.path.isfile(result):
            file_size = os.path.getsize(result)
            return PluginResult(
                success=True,
                output_paths=[result],
                message=f"音频转换成功 ({file_size // 1024}KB)"
            )
        else:
            return PluginResult(success=False, error="音频转换失败。请确保已安装 FFmpeg。")
