import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class PdfMergePlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "pdf_merge"

    @property
    def name(self) -> str:
        return "PDF合并"

    @property
    def description(self) -> str:
        return "将多个PDF文件按顺序合并为一个文件"

    @property
    def category(self) -> str:
        return "pdf"

    @property
    def icon(self) -> str:
        return "link"

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
            "output_name": {
                "type": "string",
                "label": "输出文件名",
                "default": "merged.pdf"
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        # pypdf>=6.0 已移除 PdfMerger，统一用 PdfWriter + PdfReader 逐页合并
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            return PluginResult(success=False, error="pypdf 未安装")

        file_paths = input_data.file_paths
        options = input_data.options

        if len(file_paths) < 2:
            return PluginResult(success=False, error="请至少选择2个PDF文件")

        output_dir = get_output_dir(file_paths[0], options.get("output_dir", ""))
        ensure_dir(output_dir)
        output_name = options.get("output_name", "merged.pdf")
        if not output_name.endswith('.pdf'):
            output_name += '.pdf'
        output_path = os.path.join(output_dir, output_name)

        writer = PdfWriter()
        try:
            total_pages = 0
            for idx, path in enumerate(file_paths):
                reader = PdfReader(path)
                for page in reader.pages:
                    writer.add_page(page)
                total_pages += len(reader.pages)
                if progress_callback:
                    progress_callback(
                        int((idx + 1) / len(file_paths) * 100),
                        f"合并中: {os.path.basename(path)}"
                    )

            with open(output_path, 'wb') as f:
                writer.write(f)
            writer.close()

            return PluginResult(
                success=True,
                output_paths=[output_path],
                message=f"成功合并 {len(file_paths)} 个PDF文件, 共 {total_pages} 页"
            )
        except Exception as e:
            writer.close()
            return PluginResult(success=False, error=f"合并失败: {str(e)}")


class PdfSplitPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "pdf_split"

    @property
    def name(self) -> str:
        return "PDF拆分"

    @property
    def description(self) -> str:
        return "将PDF文件按页码范围拆分为多个独立文件"

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
            "mode": {
                "type": "select",
                "label": "拆分模式",
                "default": "every_page",
                "options": [
                    {"label": "每页一个文件", "value": "every_page"},
                    {"label": "按页数拆分", "value": "by_count"},
                    {"label": "按范围拆分", "value": "by_range"}
                ]
            },
            "pages_per_file": {
                "type": "integer",
                "label": "每个文件页数",
                "default": 1,
                "min": 1,
                "max": 100
            },
            "range_spec": {
                "type": "string",
                "label": "页码范围(如: 1-3,5,7-10)",
                "default": "1-3"
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            return PluginResult(success=False, error="pypdf 未安装")

        file_path = input_data.file_paths[0]
        options = input_data.options
        mode = options.get("mode", "every_page")

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)
        base_name = os.path.splitext(os.path.basename(file_path))[0]

        try:
            reader = PdfReader(file_path)
            total_pages = len(reader.pages)
            output_paths = []

            if mode == "every_page":
                for page_num in range(total_pages):
                    writer = PdfWriter()
                    writer.add_page(reader.pages[page_num])
                    out_path = os.path.join(output_dir, f"{base_name}_p{page_num + 1:03d}.pdf")
                    with open(out_path, 'wb') as f:
                        writer.write(f)
                    output_paths.append(out_path)
                    if progress_callback:
                        progress_callback(
                            int((page_num + 1) / total_pages * 100),
                            f"拆分第 {page_num + 1}/{total_pages} 页"
                        )

            elif mode == "by_count":
                pages_per = max(1, options.get("pages_per_file", 1))
                file_idx = 0
                for start in range(0, total_pages, pages_per):
                    end = min(start + pages_per, total_pages)
                    writer = PdfWriter()
                    for p in range(start, end):
                        writer.add_page(reader.pages[p])
                    file_idx += 1
                    out_path = os.path.join(output_dir, f"{base_name}_part{file_idx:02d}.pdf")
                    with open(out_path, 'wb') as f:
                        writer.write(f)
                    output_paths.append(out_path)

            elif mode == "by_range":
                range_str = options.get("range_spec", "1-3")
                ranges = self._parse_range(range_str)
                for idx, (start, end) in enumerate(ranges):
                    start = max(0, start - 1)
                    end = min(end, total_pages)
                    writer = PdfWriter()
                    for p in range(start, end):
                        writer.add_page(reader.pages[p])
                    out_path = os.path.join(output_dir, f"{base_name}_range{idx + 1:02d}.pdf")
                    with open(out_path, 'wb') as f:
                        writer.write(f)
                    output_paths.append(out_path)

            return PluginResult(
                success=True,
                output_paths=output_paths,
                message=f"成功拆分为 {len(output_paths)} 个PDF文件"
            )

        except Exception as e:
            return PluginResult(success=False, error=f"拆分失败: {str(e)}")

    def _parse_range(self, range_str: str) -> List[tuple]:
        ranges = []
        for part in range_str.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-')
                ranges.append((int(start), int(end)))
            else:
                p = int(part)
                ranges.append((p, p))
        return ranges
