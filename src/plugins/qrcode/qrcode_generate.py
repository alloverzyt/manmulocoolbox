import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class QrCodeGeneratePlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "qrcode_generate"

    @property
    def name(self) -> str:
        return "生成二维码"

    @property
    def description(self) -> str:
        return "生成文本、URL、WiFi配置、联系人信息等类型的二维码"

    @property
    def category(self) -> str:
        return "qrcode"

    @property
    def icon(self) -> str:
        return "qrcode"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def requires_files(self) -> bool:
        # 支持直接输入文本/WiFi/联系人，无需文件
        return False

    @property
    def supported_input_formats(self) -> List[str]:
        return ["txt", "text", "log", "csv", "json", "md"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["png", "jpg", "svg"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "content_source": {
                "type": "select",
                "label": "内容来源",
                "default": "text_input",
                "options": [
                    {"label": "直接输入文本", "value": "text_input"},
                    {"label": "从文件读取", "value": "file_input"},
                    {"label": "WiFi配置", "value": "wifi"},
                    {"label": "联系人信息", "value": "contact"}
                ]
            },
            "text_content": {
                "type": "string",
                "label": "文本内容",
                "default": "https://github.com"
            },
            "size": {
                "type": "integer",
                "label": "二维码尺寸(像素)",
                "default": 300,
                "min": 100,
                "max": 2000
            },
            "error_level": {
                "type": "select",
                "label": "纠错级别",
                "default": "M",
                "options": [
                    {"label": "低 (L, 7%)", "value": "L"},
                    {"label": "中 (M, 15%)", "value": "M"},
                    {"label": "高 (Q, 25%)", "value": "Q"},
                    {"label": "最高 (H, 30%)", "value": "H"}
                ]
            },
            "output_format": {
                "type": "select",
                "label": "输出格式",
                "default": "png",
                "options": [
                    {"label": "PNG", "value": "png"},
                    {"label": "JPG", "value": "jpg"},
                    {"label": "SVG", "value": "svg"}
                ]
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        try:
            import qrcode
            from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
        except ImportError:
            return PluginResult(success=False, error="qrcode 库未安装。请运行: pip install qrcode[pil]")

        options = input_data.options
        source = options.get("content_source", "text_input")
        size = options.get("size", 300)
        error_level = options.get("error_level", "M")
        output_format = options.get("output_format", "png")

        error_map = {
            "L": ERROR_CORRECT_L,
            "M": ERROR_CORRECT_M,
            "Q": ERROR_CORRECT_Q,
            "H": ERROR_CORRECT_H
        }

        content = ""
        if source == "text_input":
            content = options.get("text_content", "")
        elif source == "file_input":
            if input_data.file_paths:
                with open(input_data.file_paths[0], 'r', encoding='utf-8') as f:
                    content = f.read()
        elif source == "wifi":
            ssid = options.get("wifi_ssid", "WiFi")
            password = options.get("wifi_password", "")
            encryption = options.get("wifi_encryption", "WPA")
            content = f"WIFI:T:{encryption};S:{ssid};P:{password};;"
        elif source == "contact":
            name = options.get("contact_name", "Name")
            phone = options.get("contact_phone", "")
            content = f"BEGIN:VCARD\nVERSION:3.0\nFN:{name}\nTEL:{phone}\nEND:VCARD"

        if not content:
            return PluginResult(success=False, error="二维码内容不能为空")

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=error_map.get(error_level, ERROR_CORRECT_M),
                box_size=10,
                border=4,
            )
            qr.add_data(content)
            qr.make(fit=True)

            if input_data.file_paths:
                output_dir = get_output_dir(input_data.file_paths[0], options.get("output_dir", ""))
            else:
                output_dir = os.path.expanduser("~")
            ensure_dir(output_dir)

            output_path = os.path.join(output_dir, f"qrcode.{output_format}")

            if output_format == "svg":
                from qrcode.image.svg import SvgPathImage
                qr.make_image(image_factory=SvgPathImage).save(output_path)
            else:
                img = qr.make_image(fill_color="black", back_color="white")
                img = img.resize((size, size))
                if output_format == "jpg":
                    img = img.convert('RGB')
                img.save(output_path)

            return PluginResult(
                success=True,
                output_paths=[output_path],
                message=f"二维码已生成 ({size}x{size})"
            )

        except Exception as e:
            return PluginResult(success=False, error=f"生成二维码失败: {str(e)}")
