import os
import sys
from typing import Any, Dict, List, Optional

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class ImageToPdfPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "image_to_pdf"

    @property
    def name(self) -> str:
        return "图片转PDF"

    @property
    def description(self) -> str:
        return "将多张图片合并为单个PDF文件，保持原始画质"

    @property
    def category(self) -> str:
        return "image"

    @property
    def icon(self) -> str:
        return "document"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["png", "jpg", "jpeg", "bmp", "tiff", "webp"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["pdf"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "page_size": {
                "type": "select",
                "label": "页面尺寸",
                "default": "auto",
                "options": [
                    {"label": "自动(适应图片)", "value": "auto"},
                    {"label": "A4", "value": "a4"},
                    {"label": "A3", "value": "a3"},
                    {"label": "Letter", "value": "letter"}
                ]
            },
            "orientation": {
                "type": "select",
                "label": "方向",
                "default": "portrait",
                "options": [
                    {"label": "纵向", "value": "portrait"},
                    {"label": "横向", "value": "landscape"}
                ]
            },
            "quality": {
                "type": "integer",
                "label": "质量(1-100)",
                "default": 95,
                "min": 1,
                "max": 100
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        try:
            from PIL import Image
        except ImportError:
            return PluginResult(success=False, error="Pillow 未安装")

        file_paths = input_data.file_paths
        options = input_data.options

        output_dir = get_output_dir(file_paths[0], options.get("output_dir", ""))
        ensure_dir(output_dir)

        output_name = f"combined_{os.path.basename(file_paths[0]).rsplit('.', 1)[0]}.pdf"
        output_path = os.path.join(output_dir, output_name)

        images = []
        try:
            for idx, path in enumerate(file_paths):
                img = Image.open(path)

                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                images.append(img.copy())

                if progress_callback:
                    progress_callback(
                        int((idx + 1) / len(file_paths) * 50),
                        f"加载图片 {idx + 1}/{len(file_paths)}"
                    )

            if not images:
                return PluginResult(success=False, error="没有有效的图片文件")

            first_img = images[0]
            page_size = options.get("page_size", "auto")
            orientation = options.get("orientation", "portrait")

            if page_size != "auto":
                sizes = {
                    "a4": (2480, 3508),
                    "a3": (3508, 4961),
                    "letter": (2550, 3300)
                }
                base_size = sizes.get(page_size, sizes["a4"])
                if orientation == "landscape":
                    base_size = (base_size[1], base_size[0])

                from PIL import Image as PILImage
                bg_images = []
                for img in images:
                    bg = PILImage.new('RGB', base_size, (255, 255, 255))
                    ratio = min(base_size[0] / img.width, base_size[1] / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img_resized = img.resize(new_size, PILImage.LANCZOS)
                    x = (base_size[0] - new_size[0]) // 2
                    y = (base_size[1] - new_size[1]) // 2
                    bg.paste(img_resized, (x, y))
                    bg_images.append(bg)
                images = bg_images
            else:
                max_w = max(img.width for img in images)
                max_h = max(img.height for img in images)
                if orientation == "landscape":
                    max_w, max_h = max(max_w, max_h), min(max_w, max_h)

            quality = options.get("quality", 95)

            if hasattr(images[0], 'save'):
                images[0].save(
                    output_path,
                    save_all=True,
                    append_images=images[1:],
                    quality=quality,
                    resolution=300.0
                )
            else:
                images[0].save(output_path, quality=quality)

            if progress_callback:
                progress_callback(90, "生成PDF中...")

            return PluginResult(
                success=True,
                output_paths=[output_path],
                message=f"成功合并 {len(images)} 张图片为PDF"
            )

        except Exception as e:
            return PluginResult(success=False, error=f"图片转PDF失败: {str(e)}")
        finally:
            for img in images:
                try:
                    img.close()
                except Exception:
                    pass
