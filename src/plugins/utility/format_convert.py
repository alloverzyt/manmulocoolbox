import os
import json
import csv
import yaml
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_filename, get_output_dir


class FormatConvertPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "format_convert"

    @property
    def name(self) -> str:
        return "JSON/CSV/YAML互转"

    @property
    def description(self) -> str:
        return "在JSON、CSV、YAML格式之间相互转换数据"

    @property
    def category(self) -> str:
        return "utility"

    @property
    def icon(self) -> str:
        return "refresh"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["json", "csv", "yaml", "yml"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["json", "csv", "yaml"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "target_format": {
                "type": "select",
                "label": "目标格式",
                "default": "json",
                "options": [
                    {"label": "JSON", "value": "json"},
                    {"label": "CSV", "value": "csv"},
                    {"label": "YAML", "value": "yaml"}
                ]
            },
            "indent": {
                "type": "integer",
                "label": "缩进空格数",
                "default": 4,
                "min": 2,
                "max": 8
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        file_path = input_data.file_paths[0]
        options = input_data.options
        target_fmt = options.get("target_format", "json")
        indent = options.get("indent", 4)

        ext = os.path.splitext(file_path)[1].lower()
        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        base_name = get_filename(file_path)
        output_path = os.path.join(output_dir, f"{base_name}.{target_fmt}")

        try:
            data = None

            if ext in ('.json',):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            elif ext in ('.csv',):
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    data = list(reader)
            elif ext in ('.yaml', '.yml'):
                try:
                    import yaml
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                except ImportError:
                    return PluginResult(success=False, error="PyYAML 未安装")
            else:
                return PluginResult(success=False, error=f"不支持的输入格式: {ext}")

            if target_fmt == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=indent)
            elif target_fmt == "csv":
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    fieldnames = list(data[0].keys())
                    with open(output_path, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(data)
                else:
                    return PluginResult(success=False, error="CSV格式需要列表字典结构")
            elif target_fmt == "yaml":
                try:
                    import yaml
                    with open(output_path, 'w', encoding='utf-8') as f:
                        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
                except ImportError:
                    return PluginResult(success=False, error="PyYAML 未安装")

            return PluginResult(
                success=True,
                output_paths=[output_path],
                message=f"成功转换为 {target_fmt.upper()} 格式"
            )

        except Exception as e:
            return PluginResult(success=False, error=f"格式转换失败: {str(e)}")
