import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class DocToPdfPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "doc_to_pdf"

    @property
    def name(self) -> str:
        return "Word转PDF"

    @property
    def description(self) -> str:
        return "将Word文档(DOC/DOCX)转换为PDF格式"

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
        return ["doc", "docx"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["pdf"]

    def validate_input(self, input_data: PluginInput) -> str:
        error = super().validate_input(input_data)
        if error:
            return error

        from ...utils.libreoffice_helper import find_libreoffice
        if not find_libreoffice():
            return "未检测到 LibreOffice。请先安装 LibreOffice。"
        return None

    def check_environment(self) -> str:
        from ...utils.libreoffice_helper import find_libreoffice
        if not find_libreoffice():
            return "需要 LibreOffice 才能转换。请到「依赖管理」页下载安装。"
        return None

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        file_path = input_data.file_paths[0]
        options = input_data.options

        from ...utils.libreoffice_helper import libreoffice_convert

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        result_path = libreoffice_convert(file_path, output_dir, "pdf")

        if result_path and os.path.isfile(result_path):
            return PluginResult(
                success=True,
                output_paths=[result_path],
                message="Word转PDF成功"
            )
        else:
            return PluginResult(
                success=False,
                error="Word转PDF失败。请确保文件未损坏，且LibreOffice可正常运行。"
            )


class ExcelToPdfPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "excel_to_pdf"

    @property
    def name(self) -> str:
        return "Excel转PDF"

    @property
    def description(self) -> str:
        return "将Excel表格(XLS/XLSX)转换为PDF格式"

    @property
    def category(self) -> str:
        return "document"

    @property
    def icon(self) -> str:
        return "chart"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["xls", "xlsx"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["pdf"]

    def validate_input(self, input_data: PluginInput) -> str:
        error = super().validate_input(input_data)
        if error:
            return error

        from ...utils.libreoffice_helper import find_libreoffice
        if not find_libreoffice():
            return "未检测到 LibreOffice。请先安装 LibreOffice。"
        return None

    def check_environment(self) -> str:
        from ...utils.libreoffice_helper import find_libreoffice
        if not find_libreoffice():
            return "需要 LibreOffice 才能转换。请到「依赖管理」页下载安装。"
        return None

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        file_path = input_data.file_paths[0]
        options = input_data.options

        from ...utils.libreoffice_helper import libreoffice_convert

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        result_path = libreoffice_convert(file_path, output_dir, "pdf")

        if result_path and os.path.isfile(result_path):
            return PluginResult(
                success=True,
                output_paths=[result_path],
                message="Excel转PDF成功"
            )
        else:
            return PluginResult(
                success=False,
                error="Excel转PDF失败。请确保文件未损坏，且LibreOffice可正常运行。"
            )
