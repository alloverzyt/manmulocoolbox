import os
import re
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class BatchRenamePlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "batch_rename"

    @property
    def name(self) -> str:
        return "批量重命名"

    @property
    def description(self) -> str:
        return "批量重命名文件，支持序号、日期、正则替换等模式"

    @property
    def category(self) -> str:
        return "file"

    @property
    def icon(self) -> str:
        return "edit"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["*"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["*"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "pattern": {
                "type": "select",
                "label": "命名模式",
                "default": "numbered",
                "options": [
                    {"label": "序号 (file_001, file_002...)", "value": "numbered"},
                    {"label": "在原文件名前加前缀", "value": "prefix"},
                    {"label": "在原文件名后加后缀", "value": "suffix"},
                    {"label": "正则替换", "value": "regex"},
                    {"label": "日期+序号", "value": "date_numbered"}
                ]
            },
            "template": {
                "type": "string",
                "label": "模板/文本",
                "default": "file_{n}"
            },
            "start_number": {
                "type": "integer",
                "label": "起始编号",
                "default": 1,
                "min": 0,
                "max": 99999
            },
            "digits": {
                "type": "integer",
                "label": "编号位数",
                "default": 3,
                "min": 1,
                "max": 6
            },
            "recursive": {
                "type": "boolean",
                "label": "递归处理子目录",
                "default": False
            },
            "output_dir": {
                "type": "string",
                "label": "输出目录(留空则重命名原文件)",
                "default": ""
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        options = input_data.options
        pattern = options.get("pattern", "numbered")
        template = options.get("template", "file_{n}")
        start_num = options.get("start_number", 1)
        digits = options.get("digits", 3)
        recursive = options.get("recursive", False)
        output_dir = options.get("output_dir", "")

        file_paths = input_data.file_paths

        if recursive and file_paths:
            all_files = []
            for path in file_paths:
                if os.path.isdir(path):
                    for root, dirs, files in os.walk(path):
                        for f in files:
                            all_files.append(os.path.join(root, f))
                else:
                    all_files.append(path)
            file_paths = all_files

        if not file_paths:
            return PluginResult(success=False, error="没有可处理的文件")

        output_paths = []
        errors = []

        for idx, file_path in enumerate(file_paths):
            try:
                new_name = self._generate_name(
                    file_path, pattern, template,
                    start_num + idx, digits
                )
                new_path = os.path.join(
                    os.path.dirname(file_path) if not output_dir else output_dir,
                    new_name
                )
                # 目标已存在时自动追加序号避让，避免整批重命名因单个冲突失败
                new_path = self._unique_path(new_path)

                if output_dir:
                    ensure_dir(output_dir)
                    import shutil
                    shutil.copy2(file_path, new_path)
                else:
                    os.rename(file_path, new_path)

                output_paths.append(new_path)

                if progress_callback:
                    progress_callback(
                        int((idx + 1) / len(file_paths) * 100),
                        f"重命名: {os.path.basename(file_path)} → {new_name}"
                    )

            except Exception as e:
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")

        success_count = len(output_paths)
        return PluginResult(
            success=success_count > 0,
            output_paths=output_paths,
            message=f"成功重命名 {success_count}/{len(file_paths)} 个文件"
            + (f", {len(errors)} 个失败" if errors else ""),
            error="\n".join(errors) if errors else ""
        )

    def _generate_name(self, file_path: str, pattern: str, template: str,
                       number: int, digits: int) -> str:
        base, ext = os.path.splitext(os.path.basename(file_path))

        if pattern == "numbered":
            num_str = str(number).zfill(digits)
            name = template.replace("{n}", num_str)
            return f"{name}{ext}"

        elif pattern == "prefix":
            return f"{template}{base}{ext}"

        elif pattern == "suffix":
            return f"{base}{template}{ext}"

        elif pattern == "regex":
            try:
                parts = template.split("|")
                if len(parts) == 3:
                    pattern_str, replace_str, target = parts
                    target = target.strip()
                    source = base if target == "name" else base + ext
                    result = re.sub(pattern_str, replace_str, source)
                    return result
            except Exception:
                pass
            return f"{base}_modified{ext}"

        elif pattern == "date_numbered":
            from datetime import datetime
            date_str = datetime.now().strftime("%Y%m%d")
            num_str = str(number).zfill(digits)
            return f"{date_str}_{num_str}{ext}"

        return f"{base}_renamed{ext}"

    @staticmethod
    def _unique_path(path: str) -> str:
        """目标路径已存在时自动追加序号（file_001 → file_001_1），避免重命名冲突"""
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        i = 1
        while os.path.exists(f"{base}_{i}{ext}"):
            i += 1
        return f"{base}_{i}{ext}"
