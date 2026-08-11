import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_extension, get_output_dir


class ImageConvertPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "image_convert"

    @property
    def name(self) -> str:
        return "格式转换"

    @property
    def description(self) -> str:
        return "批量转换图片格式，支持PNG/JPG/WebP/BMP/TIFF/HEIC互转"

    @property
    def category(self) -> str:
        return "image"

    @property
    def icon(self) -> str:
        return "refresh"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp", "gif"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["png", "jpg", "jpeg", "bmp", "tiff", "webp", "gif"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "target_format": {
                "type": "select",
                "label": "目标格式",
                "default": "png",
                "options": [
                    {"label": "PNG", "value": "png"},
                    {"label": "JPG", "value": "jpg"},
                    {"label": "WebP", "value": "webp"},
                    {"label": "BMP", "value": "bmp"},
                    {"label": "TIFF", "value": "tiff"},
                    {"label": "GIF", "value": "gif"}
                ]
            },
            "quality": {
                "type": "integer",
                "label": "质量(1-100)",
                "default": 95,
                "min": 1,
                "max": 100
            },
            "overwrite": {
                "type": "boolean",
                "label": "覆盖原文件",
                "default": False
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        try:
            from PIL import Image
        except ImportError:
            return PluginResult(success=False, error="Pillow 未安装")

        file_path = input_data.file_paths[0]
        options = input_data.options
        target_format = options.get("target_format", "png")
        quality = options.get("quality", 95)
        overwrite = options.get("overwrite", False)

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.{target_format}")

        try:
            img = Image.open(file_path)

            if target_format == "jpg" and img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
            elif target_format == "png" and img.mode not in ('RGBA', 'RGB', 'LA', 'L', 'P'):
                img = img.convert('RGBA')
            elif target_format in ('jpg', 'bmp') and img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')

            save_kwargs = {}
            if target_format in ('jpg', 'webp', 'tiff'):
                save_kwargs["quality"] = quality
            if target_format == "tiff":
                save_kwargs["compression"] = "lzw"

            img.save(output_path, **save_kwargs)
            img.close()

            return PluginResult(
                success=True,
                output_paths=[output_path],
                message=f"成功转换为{target_format.upper()}格式"
            )

        except Exception as e:
            return PluginResult(success=False, error=f"格式转换失败: {str(e)}")
