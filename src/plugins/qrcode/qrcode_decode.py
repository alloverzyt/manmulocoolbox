import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class QrCodeDecodePlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "qrcode_decode"

    @property
    def name(self) -> str:
        return "识别二维码"

    @property
    def description(self) -> str:
        return "从图片中识别和解码二维码内容"

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
    def supported_input_formats(self) -> List[str]:
        return ["png", "jpg", "jpeg", "bmp", "tiff", "webp"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["txt", "json"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "save_result": {
                "type": "boolean",
                "label": "保存结果到文件",
                "default": True
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        try:
            from pyzbar.pyzbar import decode
            from PIL import Image
        except ImportError:
            return PluginResult(
                success=False,
                error="pyzbar 未安装。请运行: pip install pyzbar\nWindows用户可能还需要安装 Visual C++ Redistributable"
            )

        file_path = input_data.file_paths[0]
        options = input_data.options

        try:
            img = Image.open(file_path)
            results = decode(img)

            if not results:
                return PluginResult(
                    success=False,
                    error="未在图片中检测到二维码"
                )

            decoded_contents = []
            for r in results:
                content = r.data.decode('utf-8', errors='replace')
                decoded_contents.append({
                    "type": r.type,
                    "content": content,
                    "position": {
                        "x": r.rect.left,
                        "y": r.rect.top,
                        "width": r.rect.width,
                        "height": r.rect.height
                    }
                })

            output_paths = []
            if options.get("save_result", True):
                output_dir = get_output_dir(file_path, options.get("output_dir", ""))
                ensure_dir(output_dir)
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_path = os.path.join(output_dir, f"{base_name}_qr_result.json")

                import json
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(decoded_contents, f, ensure_ascii=False, indent=2)
                output_paths.append(output_path)

            contents_text = "\n".join(
                f"[{item['type']}] {item['content'][:100]}"
                for item in decoded_contents
            )

            return PluginResult(
                success=True,
                output_paths=output_paths,
                message=f"识别到 {len(decoded_contents)} 个二维码:\n{contents_text}"
            )

        except Exception as e:
            return PluginResult(success=False, error=f"二维码识别失败: {str(e)}")
