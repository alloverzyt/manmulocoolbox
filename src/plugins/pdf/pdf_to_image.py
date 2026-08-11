import os
import sys
import time
from typing import Any, Dict, List, Optional

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_filename, get_output_dir


class PdfToImagePlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "pdf_to_image"

    @property
    def name(self) -> str:
        return "PDF转图片"

    @property
    def description(self) -> str:
        return "将PDF文件的每一页转换为高清图片，支持自定义DPI和输出格式"

    @property
    def category(self) -> str:
        return "pdf"

    @property
    def icon(self) -> str:
        return "image"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["pdf"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["png", "jpg", "bmp", "tiff"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "dpi": {
                "type": "integer",
                "label": "分辨率(DPI)",
                "default": 300,
                "min": 72,
                "max": 1200
            },
            "format": {
                "type": "select",
                "label": "输出格式",
                "default": "png",
                "options": [
                    {"label": "PNG (无损)", "value": "png"},
                    {"label": "JPG (有损)", "value": "jpg"},
                    {"label": "BMP", "value": "bmp"},
                    {"label": "TIFF", "value": "tiff"}
                ]
            },
            "start_page": {
                "type": "integer",
                "label": "起始页",
                "default": 1,
                "min": 1,
                "max": 9999
            },
            "end_page": {
                "type": "integer",
                "label": "结束页(0=全部)",
                "default": 0,
                "min": 0,
                "max": 9999
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        try:
            import fitz
        except ImportError:
            return PluginResult(
                success=False,
                error="PyMuPDF 未安装。请运行: pip install PyMuPDF"
            )

        file_path = input_data.file_paths[0]
        options = input_data.options
        dpi = options.get("dpi", 300)
        fmt = options.get("format", "png")
        start_page = max(0, options.get("start_page", 1) - 1)
        end_page = options.get("end_page", 0)

        try:
            doc = fitz.open(file_path)
            page_count = len(doc)

            if end_page <= 0 or end_page > page_count:
                end_page = page_count

            output_dir = get_output_dir(file_path, options.get("output_dir", ""))
            base_name = get_filename(file_path)
            ensure_dir(output_dir)

            zoom = dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            output_paths = []

            for page_num in range(start_page, end_page):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=matrix, alpha=False)

                ext = "jpg" if fmt == "jpg" else fmt
                if ext == "jpg":
                    ext = "jpeg"

                output_path = os.path.join(
                    output_dir,
                    f"{base_name}_p{page_num + 1:03d}.{ext}"
                )

                save_kwargs = {}
                if fmt == "jpg":
                    save_kwargs["quality"] = 95
                elif fmt == "tiff":
                    save_kwargs["compression"] = "lzw"

                pix.save(output_path, **save_kwargs if save_kwargs else {})
                output_paths.append(output_path)

                if progress_callback:
                    progress = int((page_num - start_page + 1) / max(end_page - start_page, 1) * 100)
                    progress_callback(progress, f"处理第 {page_num + 1}/{end_page} 页")

            doc.close()

            return PluginResult(
                success=True,
                output_paths=output_paths,
                message=f"成功转换 {len(output_paths)} 页图片"
            )

        except Exception as e:
            return PluginResult(success=False, error=f"PDF转换失败: {str(e)}")
