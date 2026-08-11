import os
from datetime import datetime
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult


class TimestampConvertPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "timestamp_convert"

    @property
    def name(self) -> str:
        return "时间戳转换"

    @property
    def description(self) -> str:
        return "在时间戳和日期字符串之间相互转换，支持多种格式"

    @property
    def category(self) -> str:
        return "utility"

    @property
    def icon(self) -> str:
        return "clock"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def requires_files(self) -> bool:
        return False

    @property
    def supported_input_formats(self) -> List[str]:
        return ["*"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["txt"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "direction": {
                "type": "select",
                "label": "转换方向",
                "default": "to_timestamp",
                "options": [
                    {"label": "日期→时间戳", "value": "to_timestamp"},
                    {"label": "时间戳→日期", "value": "to_date"}
                ]
            },
            "date_string": {
                "type": "string",
                "label": "日期字符串",
                "default": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "timestamp": {
                "type": "string",
                "label": "时间戳(秒)",
                "default": str(int(datetime.now().timestamp()))
            },
            "output_format": {
                "type": "select",
                "label": "日期输出格式",
                "default": "%Y-%m-%d %H:%M:%S",
                "options": [
                    {"label": "2024-01-15 14:30:05", "value": "%Y-%m-%d %H:%M:%S"},
                    {"label": "2024/01/15 14:30", "value": "%Y/%m/%d %H:%M"},
                    {"label": "15/01/2024 14:30", "value": "%d/%m/%Y %H:%M"},
                    {"label": "2024年01月15日 14时30分", "value": "%Y年%m月%d日 %H时%M分"},
                    {"label": "ISO 8601", "value": "iso"}
                ]
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        options = input_data.options
        direction = options.get("direction", "to_timestamp")

        try:
            if direction == "to_timestamp":
                date_str = options.get("date_string", "")
                formats_to_try = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y/%m/%d %H:%M:%S",
                    "%Y-%m-%d %H:%M",
                    "%Y/%m/%d %H:%M",
                    "%d/%m/%Y %H:%M:%S",
                    "%d/%m/%Y %H:%M",
                    "%Y年%m月%d日 %H时%M分%S秒",
                    "%Y年%m月%d日 %H:%M:%S",
                    "%Y-%m-%d",
                    "%Y/%m/%d",
                ]

                parsed = None
                for fmt in formats_to_try:
                    try:
                        parsed = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue

                if not parsed:
                    return PluginResult(success=False, error=f"无法解析日期: {date_str}")

                timestamp = int(parsed.timestamp())
                timestamp_ms = parsed.timestamp() * 1000

                return PluginResult(
                    success=True,
                    output_paths=[],
                    message=f"秒级时间戳: {timestamp}\n毫秒时间戳: {int(timestamp_ms)}"
                )

            else:
                ts_str = options.get("timestamp", "")
                try:
                    ts = float(ts_str)
                    if len(ts_str) > 13 or ts > 1e12:
                        ts = ts / 1000.0
                    dt = datetime.fromtimestamp(ts)
                except (ValueError, OSError):
                    return PluginResult(success=False, error=f"无效的时间戳: {ts_str}")

                out_fmt = options.get("output_format", "%Y-%m-%d %H:%M:%S")
                if out_fmt == "iso":
                    result = dt.isoformat()
                else:
                    result = dt.strftime(out_fmt)

                return PluginResult(
                    success=True,
                    output_paths=[],
                    message=f"日期: {result}"
                )

        except Exception as e:
            return PluginResult(success=False, error=f"转换失败: {str(e)}")
