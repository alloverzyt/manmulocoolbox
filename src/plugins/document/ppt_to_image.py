import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir, get_filename


class PptToImagePlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "ppt_to_image"

    @property
    def name(self) -> str:
        return "PPT转图片"

    @property
    def description(self) -> str:
        return "将PPT/PPTX演示文稿的每一页转换为高清图片"

    @property
    def category(self) -> str:
        return "document"

    @property
    def icon(self) -> str:
        return "image"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["ppt", "pptx"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["png", "jpg"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "format": {
                "type": "select",
                "label": "输出格式",
                "default": "png",
                "options": [
                    {"label": "PNG (无损)", "value": "png"},
                    {"label": "JPG (有损)", "value": "jpg"}
                ]
            },
            "slides_per_page": {
                "type": "integer",
                "label": "每页幻灯片数",
                "default": 1,
                "min": 1,
                "max": 4
            }
        }

    def validate_input(self, input_data: PluginInput) -> str:
        error = super().validate_input(input_data)
        if error:
            return error

        from ...utils.libreoffice_helper import find_libreoffice
        if not find_libreoffice():
            return (
                "未检测到 LibreOffice。\n"
                "请安装 LibreOffice 后重试，或下载便携版放入 resources/libreoffice 目录。\n"
                "下载地址: https://www.libreoffice.org/download/"
            )
        return None

    def check_environment(self) -> str:
        from ...utils.libreoffice_helper import find_libreoffice
        if not find_libreoffice():
            return "需要 LibreOffice 才能转换。请到「依赖管理」页下载安装。"
        return None

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        file_path = input_data.file_paths[0]
        options = input_data.options
        fmt = options.get("format", "png")

        from ...utils.libreoffice_helper import libreoffice_to_images

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        page_files = libreoffice_to_images(file_path, output_dir)

        if not page_files:
            return PluginResult(
                success=False,
                error="PPT转换失败。请确保已安装 LibreOffice，且PPT文件未损坏。"
            )

        output_paths = []
        for idx, src_path in enumerate(page_files):
            ext = "jpg" if fmt == "jpg" else "png"
            base_name = get_filename(file_path)
            dst_path = os.path.join(output_dir, f"{base_name}_s{idx + 1:03d}.{ext}")

            if fmt == "jpg":
                try:
                    from PIL import Image
                    img = Image.open(src_path)
                    img = img.convert('RGB')
                    img.save(dst_path, quality=95)
                    img.close()
                    os.remove(src_path)
                except Exception:
                    if src_path != dst_path:
                        os.rename(src_path, dst_path)
            else:
                if src_path != dst_path:
                    os.rename(src_path, dst_path)

            output_paths.append(dst_path)

            if progress_callback:
                progress_callback(
                    int((idx + 1) / len(page_files) * 100),
                    f"处理第 {idx + 1}/{len(page_files)} 页幻灯片"
                )

        return PluginResult(
            success=True,
            output_paths=output_paths,
            message=f"成功转换 {len(output_paths)} 页幻灯片为图片"
        )
