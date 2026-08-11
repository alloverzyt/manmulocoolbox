import os
import hashlib
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult


class FileHashPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "file_hash"

    @property
    def name(self) -> str:
        return "哈希校验"

    @property
    def description(self) -> str:
        return "计算文件的MD5/SHA1/SHA256哈希值，用于文件完整性校验"

    @property
    def category(self) -> str:
        return "file"

    @property
    def icon(self) -> str:
        return "hash"

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
    def options_schema(self) -> Dict[str, Any]:
        return {
            "algorithm": {
                "type": "select",
                "label": "哈希算法",
                "default": "sha256",
                "options": [
                    {"label": "MD5", "value": "md5"},
                    {"label": "SHA1", "value": "sha1"},
                    {"label": "SHA256 (推荐)", "value": "sha256"},
                    {"label": "SHA512", "value": "sha512"}
                ]
            },
            "save_result": {
                "type": "boolean",
                "label": "保存结果到文件",
                "default": True
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        file_path = input_data.file_paths[0]
        options = input_data.options
        algorithm = options.get("algorithm", "sha256")
        save_result = options.get("save_result", True)

        hash_func = {
            "md5": hashlib.md5,
            "sha1": hashlib.sha1,
            "sha256": hashlib.sha256,
            "sha512": hashlib.sha512
        }.get(algorithm)

        if not hash_func:
            return PluginResult(success=False, error=f"不支持的算法: {algorithm}")

        try:
            hash_obj = hash_func()
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    hash_obj.update(chunk)

            hash_value = hash_obj.hexdigest()
            file_size = os.path.getsize(file_path)

            result_message = f"文件: {os.path.basename(file_path)}\n"
            result_message += f"大小: {file_size} 字节\n"
            result_message += f"算法: {algorithm.upper()}\n"
            result_message += f"哈希值: {hash_value}"

            output_paths = []
            if save_result:
                output_dir = os.path.dirname(file_path)
                output_name = f"{os.path.basename(file_path)}_{algorithm}.txt"
                output_path = os.path.join(output_dir, output_name)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result_message)
                output_paths.append(output_path)

            return PluginResult(
                success=True,
                output_paths=output_paths,
                message=f"{algorithm.upper()}: {hash_value[:20]}...",
                metadata={"hash": hash_value, "algorithm": algorithm, "file_size": file_size}
            )

        except Exception as e:
            return PluginResult(success=False, error=f"哈希计算失败: {str(e)}")
