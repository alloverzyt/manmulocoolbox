import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_filename, get_output_dir


class ImageCompressPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "image_compress"

    @property
    def name(self) -> str:
        return "批量压缩"

    @property
    def description(self) -> str:
        return "批量压缩图片文件，减小文件大小同时保持较好的画质"

    @property
    def category(self) -> str:
        return "image"

    @property
    def icon(self) -> str:
        return "compress"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["png", "jpg", "jpeg", "bmp", "tiff", "webp"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["png", "jpg", "webp"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "quality": {
                "type": "integer",
                "label": "压缩质量(1-100)",
                "default": 80,
                "min": 10,
                "max": 100
            },
            "max_width": {
                "type": "integer",
                "label": "最大宽度(像素,0=不限)",
                "default": 0,
                "min": 0,
                "max": 10000
            },
            "output_format": {
                "type": "select",
                "label": "输出格式",
                "default": "保持原格式",
                "options": [
                    {"label": "保持原格式", "value": "original"},
                    {"label": "JPG (通用)", "value": "jpg"},
                    {"label": "WebP (高压缩)", "value": "webp"},
                    {"label": "PNG (无损)", "value": "png"}
                ]
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        try:
            from PIL import Image
        except ImportError:
            return PluginResult(success=False, error="Pillow 未安装")

        file_path = input_data.file_paths[0]
        options = input_data.options
        quality = options.get("quality", 80)
        max_width = options.get("max_width", 0)
        output_format = options.get("output_format", "original")

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        base_name = get_filename(file_path)
        original_ext = os.path.splitext(file_path)[1].lower().lstrip('.')

        if output_format == "original":
            fmt = original_ext if original_ext in ('jpg', 'jpeg', 'png', 'webp') else 'jpg'
        else:
            fmt = output_format

        ext = "jpg" if fmt == "jpeg" else fmt
        output_path = os.path.join(output_dir, f"{base_name}_compressed.{ext}")

        try:
            img = Image.open(file_path)

            if max_width > 0 and img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.LANCZOS)

            if fmt in ('jpg', 'webp') and img.mode in ('RGBA', 'LA', 'P'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode == 'RGBA':
                    bg.paste(img, mask=img.split()[-1])
                else:
                    bg.paste(img)
                img = bg

            save_kwargs = {"quality": quality}
            if fmt == "png":
                save_kwargs.pop("quality")
            if fmt in ("jpg", "webp"):
                save_kwargs["optimize"] = True

            img.save(output_path, **save_kwargs)
            img.close()

            original_size = os.path.getsize(file_path)
            compressed_size = os.path.getsize(output_path)
            ratio = (1 - compressed_size / original_size) * 100

            return PluginResult(
                success=True,
                output_paths=[output_path],
                message=f"压缩完成: {original_size // 1024}KB → {compressed_size // 1024}KB (减少 {ratio:.0f}%)"
            )

        except Exception as e:
            return PluginResult(success=False, error=f"压缩失败: {str(e)}")
