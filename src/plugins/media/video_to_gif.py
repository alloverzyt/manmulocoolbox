import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class VideoToGifPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "video_to_gif"

    @property
    def name(self) -> str:
        return "视频转GIF"

    @property
    def description(self) -> str:
        return "将视频文件转换为GIF动图"

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
        return ["mp4", "avi", "mov", "mkv", "webm", "flv"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["gif"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "fps": {
                "type": "integer",
                "label": "帧率(FPS)",
                "default": 10,
                "min": 1,
                "max": 60
            },
            "width": {
                "type": "integer",
                "label": "输出宽度(像素,0=保持原宽)",
                "default": 480,
                "min": 0,
                "max": 1920
            },
            "start_time": {
                "type": "string",
                "label": "起始时间(秒)",
                "default": "0"
            },
            "duration": {
                "type": "string",
                "label": "持续时间(秒)",
                "default": "10"
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        from ...utils.ffmpeg_helper import find_ffmpeg, video_to_gif

        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            return PluginResult(
                success=False,
                error="未检测到 FFmpeg。请安装 FFmpeg 后重试。\n下载地址: https://ffmpeg.org/download.html"
            )

        file_path = input_data.file_paths[0]
        options = input_data.options
        fps = options.get("fps", 10)
        width = options.get("width", 480)

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.gif")

        try:
            result = video_to_gif(file_path, output_path, fps=fps, width=width)
        except Exception as e:
            return PluginResult(success=False, error=str(e))

        if result and os.path.isfile(result):
            file_size = os.path.getsize(result)
            return PluginResult(
                success=True,
                output_paths=[result],
                message=f"GIF生成成功 ({file_size // 1024}KB)"
            )
        else:
            return PluginResult(success=False, error="GIF生成失败。请确保已安装 FFmpeg。")
