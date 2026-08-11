import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class FileOrganizerPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "file_organizer"

    @property
    def name(self) -> str:
        return "文件整理"

    @property
    def description(self) -> str:
        return "按日期或文件类型自动整理文件到不同文件夹"

    @property
    def category(self) -> str:
        return "file"

    @property
    def icon(self) -> str:
        return "folder"

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
            "organize_by": {
                "type": "select",
                "label": "整理方式",
                "default": "extension",
                "options": [
                    {"label": "按文件类型/扩展名", "value": "extension"},
                    {"label": "按修改日期(年-月)", "value": "date"},
                    {"label": "按大小", "value": "size"}
                ]
            },
            "action": {
                "type": "select",
                "label": "操作方式",
                "default": "copy",
                "options": [
                    {"label": "复制(推荐,保留原文件)", "value": "copy"},
                    {"label": "移动", "value": "move"}
                ]
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        options = input_data.options
        organize_by = options.get("organize_by", "extension")
        action = options.get("action", "copy")

        import shutil
        from datetime import datetime

        if input_data.file_paths:
            target_dir = os.path.dirname(input_data.file_paths[0])
        else:
            target_dir = os.getcwd()

        if not os.path.isdir(target_dir):
            target_dir = os.path.dirname(target_dir)

        output_dir = os.path.join(target_dir, "organized")
        ensure_dir(output_dir)

        operations = []
        errors = []

        for file_path in input_data.file_paths:
            try:
                if organize_by == "extension":
                    ext = os.path.splitext(file_path)[1].lower().lstrip('.') or '_no_ext'
                    category_dir = os.path.join(output_dir, ext)
                elif organize_by == "date":
                    mtime = os.path.getmtime(file_path)
                    date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m")
                    category_dir = os.path.join(output_dir, date_str)
                elif organize_by == "size":
                    size = os.path.getsize(file_path)
                    if size < 1024 * 1024:
                        cat = "small_<1MB"
                    elif size < 100 * 1024 * 1024:
                        cat = "medium_1-100MB"
                    else:
                        cat = "large_>100MB"
                    category_dir = os.path.join(output_dir, cat)
                else:
                    category_dir = os.path.join(output_dir, "misc")

                ensure_dir(category_dir)
                dest = os.path.join(category_dir, os.path.basename(file_path))

                counter = 1
                while os.path.exists(dest):
                    base, ext = os.path.splitext(os.path.basename(file_path))
                    dest = os.path.join(category_dir, f"{base}_{counter}{ext}")
                    counter += 1

                if action == "copy":
                    shutil.copy2(file_path, dest)
                else:
                    shutil.move(file_path, dest)

                operations.append((file_path, dest))

            except Exception as e:
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")

        return PluginResult(
            success=len(operations) > 0,
            output_paths=[output_dir],
            message=f"成功整理 {len(operations)}/{len(input_data.file_paths)} 个文件",
            error="\n".join(errors) if errors else ""
        )
