import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_filename, get_output_dir


class ImageSvgPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "image_svg"

    @property
    def name(self) -> str:
        return "SVG转PNG"

    @property
    def description(self) -> str:
        return "将SVG矢量图转换为PNG位图"

    @property
    def category(self) -> str:
        return "image"

    @property
    def icon(self) -> str:
        return "edit"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["svg"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["png"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "scale": {
                "type": "integer",
                "label": "缩放倍数",
                "default": 2,
                "min": 1,
                "max": 8
            },
            "background": {
                "type": "select",
                "label": "背景",
                "default": "transparent",
                "options": [
                    {"label": "透明", "value": "transparent"},
                    {"label": "白色", "value": "white"},
                    {"label": "黑色", "value": "black"}
                ]
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        try:
            import cairosvg
        except ImportError:
            return PluginResult(
                success=False,
                error="cairosvg 未安装。请运行: pip install cairosvg"
            )

        file_path = input_data.file_paths[0]
        options = input_data.options
        scale = options.get("scale", 2)
        bg = options.get("background", "transparent")

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        base_name = get_filename(file_path)
        output_path = os.path.join(output_dir, f"{base_name}.png")

        try:
            kwargs = {"output_width": None, "output_height": None}
            if bg == "white":
                kwargs["background_color"] = "white"
            elif bg == "black":
                kwargs["background_color"] = "black"

            cairosvg.svg2png(
                url=file_path,
                write_to=output_path,
                scale=scale,
                **kwargs
            )

            return PluginResult(
                success=True,
                output_paths=[output_path],
                message=f"SVG转PNG成功 (缩放{scale}倍)"
            )

        except Exception as e:
            return PluginResult(success=False, error=f"SVG转PNG失败: {str(e)}")
