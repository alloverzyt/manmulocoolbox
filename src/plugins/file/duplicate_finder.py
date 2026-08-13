import os
import hashlib
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class DuplicateFinderPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "duplicate_finder"

    @property
    def name(self) -> str:
        return "重复文件查找"

    @property
    def description(self) -> str:
        return "查找指定文件或目录中的重复文件(基于内容哈希比对)"

    @property
    def category(self) -> str:
        return "file"

    @property
    def icon(self) -> str:
        return "search"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["*"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["txt"]

    @property
    def process_files_together(self) -> bool:
        # 重复比对需要一次性看到全部文件，逐文件调用无法发现重复
        return True

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "compare_by": {
                "type": "select",
                "label": "比对方式",
                "default": "content",
                "options": [
                    {"label": "文件名+大小", "value": "name_size"},
                    {"label": "文件内容(精确)", "value": "content"},
                    {"label": "文件大小", "value": "size_only"}
                ]
            },
            "min_size": {
                "type": "integer",
                "label": "最小文件大小(KB)",
                "default": 1,
                "min": 0,
                "max": 100000
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        options = input_data.options
        compare_by = options.get("compare_by", "content")
        min_size = options.get("min_size", 1) * 1024

        files_to_scan = []
        for path in input_data.file_paths:
            if os.path.isdir(path):
                for root, dirs, filenames in os.walk(path):
                    for f in filenames:
                        fp = os.path.join(root, f)
                        try:
                            if os.path.getsize(fp) >= min_size:
                                files_to_scan.append(fp)
                        except OSError:
                            pass
            elif os.path.isfile(path):
                try:
                    if os.path.getsize(path) >= min_size:
                        files_to_scan.append(path)
                except OSError:
                    pass

        if not files_to_scan:
            return PluginResult(success=False, error="没有找到符合条件的文件")

        groups = {}
        total = len(files_to_scan)

        for idx, file_path in enumerate(files_to_scan):
            try:
                key = self._get_key(file_path, compare_by)
                if key not in groups:
                    groups[key] = []
                groups[key].append(file_path)
            except Exception:
                pass

            if progress_callback:
                progress_callback(
                    int((idx + 1) / total * 100),
                    f"扫描中: {idx + 1}/{total}"
                )

        duplicates = {k: v for k, v in groups.items() if len(v) > 1}

        output_dir = os.path.dirname(input_data.file_paths[0]) if input_data.file_paths else os.getcwd()
        output_path = os.path.join(output_dir, "duplicates_report.txt")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"重复文件查找报告\n{'=' * 50}\n")
            f.write(f"扫描文件总数: {total}\n")
            f.write(f"发现重复组: {len(duplicates)}\n\n")

            for group_idx, (key, paths) in enumerate(duplicates.items(), 1):
                f.write(f"重复组 {group_idx} ({len(paths)}个文件):\n")
                for p in paths:
                    size = os.path.getsize(p)
                    f.write(f"  [{size // 1024}KB] {p}\n")
                f.write("\n")

        dup_count = sum(len(v) for v in duplicates.values())
        return PluginResult(
            success=True,
            output_paths=[output_path],
            message=f"扫描{total}个文件,发现{len(duplicates)}组重复({dup_count}个文件)"
        )

    def _get_key(self, file_path: str, method: str) -> str:
        if method == "name_size":
            return f"{os.path.basename(file_path)}_{os.path.getsize(file_path)}"
        elif method == "size_only":
            return str(os.path.getsize(file_path))
        else:
            h = hashlib.md5()
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()
