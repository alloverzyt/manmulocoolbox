import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_filename, get_output_dir


class ImageRemoveBgPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "image_remove_bg"

    @property
    def name(self) -> str:
        return "去除背景"

    @property
    def description(self) -> str:
        return "智能去除图片背景，生成透明PNG"

    @property
    def category(self) -> str:
        return "image"

    @property
    def icon(self) -> str:
        return "target"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["png", "jpg", "jpeg", "bmp", "tiff", "webp"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["png"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "model": {
                "type": "select",
                "label": "模型精度",
                "default": "medium",
                "options": [
                    {"label": "快速(低精度)", "value": "u2netp"},
                    {"label": "标准(推荐)", "value": "u2net"},
                    {"label": "高精度", "value": "u2net_human_seg"}
                ]
            }
        }

    def check_environment(self) -> str:
        try:
            import rembg  # noqa: F401
            return None
        except ImportError:
            return "需要 rembg 库（AI去除背景）。请到「依赖管理」页安装。"
        except Exception:
            return "rembg 可用性检查失败。请到「依赖管理」页安装。"
        return None

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        try:
            from rembg import remove
            from PIL import Image
        except ImportError:
            return PluginResult(
                success=False,
                error="rembg 库未安装。请运行: pip install rembg\n注意: 首次使用需下载AI模型(约200MB)"
            )

        file_path = input_data.file_paths[0]
        options = input_data.options
        model_name = options.get("model", "u2net")

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        base_name = get_filename(file_path)
        output_path = os.path.join(output_dir, f"{base_name}_no_bg.png")

        try:
            input_img = Image.open(file_path)
            if input_img.mode not in ('RGB', 'RGBA'):
                input_img = input_img.convert('RGB')

            output_img = remove(input_img)
            output_img.save(output_path)

            return PluginResult(
                success=True,
                output_paths=[output_path],
                message="背景去除成功"
            )

        except Exception as e:
            return PluginResult(success=False, error=f"背景去除失败: {str(e)}")
