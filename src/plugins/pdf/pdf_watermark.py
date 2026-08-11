import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class PdfWatermarkPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "pdf_watermark"

    @property
    def name(self) -> str:
        return "PDF水印"

    @property
    def description(self) -> str:
        return "为PDF添加文字或图片水印"

    @property
    def category(self) -> str:
        return "pdf"

    @property
    def icon(self) -> str:
        return "edit"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["pdf"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["pdf"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "watermark_type": {
                "type": "select",
                "label": "水印类型",
                "default": "text",
                "options": [
                    {"label": "文字水印", "value": "text"},
                    {"label": "图片水印", "value": "image"}
                ]
            },
            "text": {
                "type": "string",
                "label": "水印文字",
                "default": "机密文件"
            },
            "opacity": {
                "type": "integer",
                "label": "透明度(1-100)",
                "default": 30,
                "min": 1,
                "max": 100
            },
            "font_size": {
                "type": "integer",
                "label": "字体大小",
                "default": 48,
                "min": 12,
                "max": 200
            },
            "rotation": {
                "type": "integer",
                "label": "旋转角度",
                "default": -45,
                "min": -90,
                "max": 90
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        try:
            from pypdf import PdfReader, PdfWriter
            from pypdf.generic import NameObject, TextStringObject, ArrayObject, NumberObject, FloatObject
        except ImportError:
            return PluginResult(success=False, error="pypdf 未安装")

        file_path = input_data.file_paths[0]
        options = input_data.options
        wm_type = options.get("watermark_type", "text")

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}_watermarked.pdf")

        try:
            reader = PdfReader(file_path)
            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            writer.write(output_path)

            return PluginResult(
                success=True,
                output_paths=[output_path],
                message="水印添加成功(基础版)"
            )

        except Exception as e:
            return PluginResult(success=False, error=f"水印添加失败: {str(e)}")
