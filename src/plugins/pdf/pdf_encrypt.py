import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class PdfEncryptPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "pdf_encrypt"

    @property
    def name(self) -> str:
        return "PDF加密解密"

    @property
    def description(self) -> str:
        return "为PDF添加密码保护，或移除已有密码"

    @property
    def category(self) -> str:
        return "pdf"

    @property
    def icon(self) -> str:
        return "lock"

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
                "label": "操作模式",
                "default": "encrypt",
                "options": [
                    {"label": "加密", "value": "encrypt"},
                    {"label": "解密", "value": "decrypt"}
                ]
            },
            "password": {
                "type": "string",
                "label": "密码",
                "default": ""
            },
            "owner_password": {
                "type": "string",
                "label": "所有者密码(可选)",
                "default": ""
            },
            "permissions": {
                "type": "select",
                "label": "权限限制",
                "default": "print_only",
                "options": [
                    {"label": "仅允许打印", "value": "print_only"},
                    {"label": "允许打印和复制", "value": "print_copy"},
                    {"label": "允许全部操作", "value": "all"}
                ]
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            return PluginResult(success=False, error="pypdf 未安装")

        file_path = input_data.file_paths[0]
        options = input_data.options
        mode = options.get("mode", "encrypt")

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        base_name = os.path.splitext(os.path.basename(file_path))[0]

        try:
            reader = PdfReader(file_path)

            if mode == "decrypt":
                password = options.get("password", "")
                if reader.is_encrypted:
                    result = reader.decrypt(password)
                    if result == 0:
                        return PluginResult(success=False, error="密码错误或解密失败")

                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)

                output_path = os.path.join(output_dir, f"{base_name}_decrypted.pdf")
                with open(output_path, 'wb') as f:
                    writer.write(f)

                return PluginResult(
                    success=True,
                    output_paths=[output_path],
                    message="PDF解密成功"
                )

            elif mode == "encrypt":
                password = options.get("password", "")
                if not password:
                    return PluginResult(success=False, error="请设置密码")

                owner_password = options.get("owner_password", "")
                permissions = options.get("permissions", "print_only")

                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)

                output_path = os.path.join(output_dir, f"{base_name}_encrypted.pdf")

                from pypdf.generic import NameObject, ArrayObject, NumberObject

                permissions_flag = {
                    "print_only": 0x0004,
                    "print_copy": 0x0004 | 0x0002,
                    "all": -1
                }.get(permissions, 0x0004)

                writer.encrypt(
                    user_password=password,
                    owner_password=owner_password or password,
                    algorithm="AES-256"
                )

                with open(output_path, 'wb') as f:
                    writer.write(f)

                return PluginResult(
                    success=True,
                    output_paths=[output_path],
                    message="PDF加密成功"
                )

        except Exception as e:
            return PluginResult(success=False, error=f"操作失败: {str(e)}")
