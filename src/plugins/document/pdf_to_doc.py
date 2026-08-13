import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_filename, get_output_dir

# pdf2docx 首次导入需加载 numpy/opencv（2~4秒），缓存检测结果避免每次点卡片卡 UI
_pdf2docx_env: str = ""  # "" = 未检测；None = 已就绪；其他 = 缺失原因


class PdfToDocPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "pdf_to_doc"

    @property
    def name(self) -> str:
        return "PDF转Word"

    @property
    def description(self) -> str:
        return "将PDF文件转换为可编辑的Word文档(DOCX)"

    @property
    def category(self) -> str:
        return "document"

    @property
    def icon(self) -> str:
        return "document"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["pdf"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["docx"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "extract_tables": {
                "type": "boolean",
                "label": "提取表格",
                "default": True
            },
            "extract_images": {
                "type": "boolean",
                "label": "提取图片",
                "default": False
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

    def check_environment(self) -> str:
        # pdf2docx 首次导入需加载 numpy/opencv（2~4秒），缓存结果避免每次点卡片都卡 UI
        global _pdf2docx_env
        if _pdf2docx_env == "":
            try:
                import pdf2docx  # noqa: F401
                _pdf2docx_env = None
            except ImportError:
                _pdf2docx_env = "需要 pdf2docx 库才能转换。请到「依赖管理」页安装。"
        return _pdf2docx_env

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        try:
            from pdf2docx import Converter
        except ImportError:
            return PluginResult(
                success=False,
                error="pdf2docx 未安装。请运行: pip install pdf2docx"
            )

        file_path = input_data.file_paths[0]
        options = input_data.options

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        base_name = get_filename(file_path)
        output_path = os.path.join(output_dir, f"{base_name}.docx")

        try:
            cv = Converter(file_path)

            start_page = max(0, options.get("start_page", 1) - 1)
            end_page = options.get("end_page", 0)
            if end_page <= 0:
                end_page = None

            cv.convert(
                output_path,
                start=start_page,
                end=end_page,
                multi_processing=False
            )
            cv.close()

            return PluginResult(
                success=True,
                output_paths=[output_path],
                message="PDF转Word成功"
            )

        except Exception as e:
            return PluginResult(success=False, error=f"PDF转Word失败: {str(e)}")
