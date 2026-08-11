import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class ImageExifPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "image_exif"

    @property
    def name(self) -> str:
        return "EXIF管理"

    @property
    def description(self) -> str:
        return "查看或清除图片的EXIF元数据(拍摄信息、GPS等)"

    @property
    def category(self) -> str:
        return "image"

    @property
    def icon(self) -> str:
        return "tag"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["jpg", "jpeg", "tiff", "tif"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["txt", "jpg"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "mode": {
                "type": "select",
                "label": "操作模式",
                "default": "read",
                "options": [
                    {"label": "查看EXIF信息", "value": "read"},
                    {"label": "清除EXIF信息", "value": "remove"}
                ]
            },
            "save_to_file": {
                "type": "boolean",
                "label": "保存结果到文件",
                "default": True
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        try:
            from PIL import Image
        except ImportError:
            return PluginResult(success=False, error="Pillow 未安装")

        file_path = input_data.file_paths[0]
        options = input_data.options
        mode = options.get("mode", "read")

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        base_name = os.path.splitext(os.path.basename(file_path))[0]

        try:
            img = Image.open(file_path)

            if mode == "read":
                exif_data = {}
                exif = img.getexif()

                if exif:
                    tag_names = {
                        0x010e: "ImageDescription",
                        0x010f: "Make",
                        0x0110: "Model",
                        0x0112: "Orientation",
                        0x011a: "XResolution",
                        0x011b: "YResolution",
                        0x0132: "DateTime",
                        0x8825: "GPSInfo",
                        0x9000: "ExifVersion",
                        0x9003: "DateTimeOriginal",
                        0x9286: "UserComment",
                        0xA002: "ExifImageWidth",
                        0xA003: "ExifImageHeight",
                        0x8298: "Copyright",
                    }

                    for tag_id, value in exif.items():
                        name = tag_names.get(tag_id, f"0x{tag_id:04x}")
                        if isinstance(value, bytes):
                            try:
                                value = value.decode('utf-8', errors='replace')
                            except Exception:
                                value = str(value[:50]) + "..."
                        exif_data[name] = str(value)

                info_lines = [f"EXIF 信息 - {os.path.basename(file_path)}", "=" * 50]
                info_lines.append(f"图片尺寸: {img.width} x {img.height}")
                info_lines.append(f"图片模式: {img.mode}")
                info_lines.append(f"文件大小: {os.path.getsize(file_path)} 字节")
                info_lines.append("")

                if exif_data:
                    info_lines.append("EXIF 元数据:")
                    for key, val in exif_data.items():
                        info_lines.append(f"  {key}: {val}")
                else:
                    info_lines.append("此图片没有 EXIF 元数据")

                result_text = "\n".join(info_lines)

                if options.get("save_to_file", True):
                    output_path = os.path.join(output_dir, f"{base_name}_exif.txt")
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(result_text)
                    img.close()
                    return PluginResult(
                        success=True,
                        output_paths=[output_path],
                        message=f"已保存EXIF信息({len(exif_data)}项)"
                    )
                else:
                    img.close()
                    return PluginResult(
                        success=True,
                        output_paths=[],
                        message=f"EXIF信息:\n" + "\n".join(
                            f"{k}: {v}" for k, v in list(exif_data.items())[:10]
                        ) + ("..." if len(exif_data) > 10 else "")
                    )

            elif mode == "remove":
                data = list(img.getdata())
                cleaned = Image.new(img.mode, img.size)
                cleaned.putdata(data)

                output_path = os.path.join(output_dir, f"{base_name}_clean.jpg")
                cleaned.save(output_path, "JPEG", quality=95)
                img.close()
                cleaned.close()

                original_size = os.path.getsize(file_path)
                clean_size = os.path.getsize(output_path)

                return PluginResult(
                    success=True,
                    output_paths=[output_path],
                    message=f"EXIF已清除 ({original_size // 1024}KB → {clean_size // 1024}KB)"
                )

        except Exception as e:
            return PluginResult(success=False, error=f"EXIF操作失败: {str(e)}")
