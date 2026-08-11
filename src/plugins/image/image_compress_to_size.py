import os
import io
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image  # 模块级导入：_compress_to_target/_compress_png 等多个方法使用

# PIL 保存格式映射：'jpg' 是输入扩展名，但 PIL 的 format 参数必须用 'JPEG'
_PIL_FORMAT_MAP = {"jpg": "JPEG"}

def _pil_format(fmt: str) -> str:
    return _PIL_FORMAT_MAP.get(fmt, fmt)

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_filename, get_output_dir


class ImageCompressToSizePlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "image_compress_to_size"

    @property
    def name(self) -> str:
        return "按大小压缩"

    @property
    def description(self) -> str:
        return "将图片精确压缩到指定目标大小(1MB/2MB/5MB)，采用二分搜索确保最高画质"

    @property
    def category(self) -> str:
        return "image"

    @property
    def icon(self) -> str:
        return "target"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["png", "jpg", "jpeg", "bmp", "tiff", "tif", "webp"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["jpg", "webp", "png"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "target_size": {
                "type": "select",
                "label": "目标大小",
                "default": "2mb",
                "options": [
                    {"label": "1 MB", "value": "1mb"},
                    {"label": "2 MB", "value": "2mb"},
                    {"label": "5 MB", "value": "5mb"},
                    {"label": "10 MB", "value": "10mb"},
                    {"label": "自定义", "value": "custom"}
                ]
            },
            "custom_size_mb": {
                "type": "float",
                "label": "自定义大小(MB)",
                "default": 3.0,
                "min": 0.1,
                "max": 50.0
            },
            "output_format": {
                "type": "select",
                "label": "输出格式",
                "default": "auto",
                "options": [
                    {"label": "自动(保持原格式)", "value": "auto"},
                    {"label": "JPG (推荐,有损压缩)", "value": "jpg"},
                    {"label": "WebP (高压缩比)", "value": "webp"},
                    {"label": "PNG (仅无损优化)", "value": "png"}
                ]
            },
            "quality_floor": {
                "type": "integer",
                "label": "最低质量(1-100)",
                "default": 20,
                "min": 1,
                "max": 80
            },
            "allow_resize": {
                "type": "boolean",
                "label": "允许调整尺寸(质量不足时自动缩小)",
                "default": True
            },
            "overwrite_original": {
                "type": "boolean",
                "label": "直接覆盖原图",
                "default": False
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        file_path = input_data.file_paths[0]
        options = input_data.options

        target_size_mb = self._parse_target_size(options)
        if target_size_mb <= 0:
            return PluginResult(success=False, error="无效的目标大小")

        target_bytes = int(target_size_mb * 1024 * 1024)
        quality_floor = options.get("quality_floor", 20)
        allow_resize = options.get("allow_resize", True)
        overwrite = options.get("overwrite_original", False)

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        if overwrite:
            output_dir = os.path.dirname(file_path)
        else:
            ensure_dir(output_dir)

        base_name = get_filename(file_path)
        original_size = os.path.getsize(file_path)
        original_ext = os.path.splitext(file_path)[1].lower().lstrip('.')

        output_format = self._determine_output_format(
            original_ext, options.get("output_format", "auto"), target_bytes, original_size
        )

        try:
            img = Image.open(file_path)
            img.load()

            if img.mode in ('RGBA', 'LA', 'PA') and output_format in ('jpg', 'webp'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            elif img.mode == 'P' and output_format in ('jpg', 'webp'):
                img = img.convert('RGB')
            elif img.mode not in ('RGB', 'RGBA', 'L'):
                img = img.convert('RGB')

            result_img, result_quality, result_size, used_resize = self._compress_to_target(
                img, target_bytes, output_format, quality_floor, allow_resize,
                progress_callback
            )

            if result_img is None:
                return PluginResult(
                    success=False,
                    error=f"无法压缩到 {target_size_mb}MB 以下。请尝试更大的目标值或允许更小的分辨率。"
                )

            ext = output_format
            if ext == "jpg":
                ext = "jpg"
            elif ext == "png":
                ext = "png"
            elif ext == "webp":
                ext = "webp"

            if overwrite:
                output_path = file_path
            else:
                output_path = os.path.join(output_dir, f"{base_name}_{target_size_mb}mb.{ext}")

            save_kwargs = {}
            if ext == "jpg":
                save_kwargs["quality"] = result_quality
                save_kwargs["optimize"] = True
                save_kwargs["progressive"] = True
            elif ext == "webp":
                save_kwargs["quality"] = result_quality
                save_kwargs["method"] = 6
            elif ext == "png":
                save_kwargs["optimize"] = True
                save_kwargs["compress_level"] = 9

            result_img.save(output_path, **save_kwargs)
            actual_size = os.path.getsize(output_path)

            ratio = (1 - actual_size / max(original_size, 1)) * 100
            quality_info = f", 质量={result_quality}" if ext != "png" else ""
            resize_info = " (已调整尺寸)" if used_resize else ""

            size_display = self._format_size(actual_size)
            target_display = f"{target_size_mb}MB"

            if actual_size <= target_bytes:
                msg = (
                    f"压缩成功: {self._format_size(original_size)} → {size_display} "
                    f"(≤{target_display}, 减少{ratio:.1f}%{quality_info}{resize_info})"
                )
            else:
                msg = (
                    f"压缩完成: {self._format_size(original_size)} → {size_display} "
                    f"(接近{target_display}, 减少{ratio:.1f}%{quality_info}{resize_info})"
                )

            return PluginResult(
                success=True,
                output_paths=[output_path],
                message=msg,
                metadata={
                    "original_size": original_size,
                    "compressed_size": actual_size,
                    "target_bytes": target_bytes,
                    "quality": result_quality,
                    "resized": used_resize,
                    "format": ext
                }
            )

        except Exception as e:
            return PluginResult(success=False, error=f"压缩失败: {str(e)}")

    def _parse_target_size(self, options: Dict) -> float:
        target = options.get("target_size", "2mb")
        if target == "custom":
            return options.get("custom_size_mb", 3.0)
        size_map = {"1mb": 1.0, "2mb": 2.0, "5mb": 5.0, "10mb": 10.0}
        return size_map.get(target, 2.0)

    def _determine_output_format(self, original_ext: str, fmt_option: str,
                                  target_bytes: int, original_size: int) -> str:
        if fmt_option != "auto":
            return fmt_option

        if original_ext in ('jpg', 'jpeg'):
            return "jpg"
        elif original_ext == "webp":
            return "webp"
        elif original_ext == "png" and original_size <= target_bytes:
            return "png"
        elif original_ext == "png":
            return "jpg"
        else:
            return "jpg"

    def _compress_to_target(self, img: 'Image.Image', target_bytes: int,
                             output_format: str, quality_floor: int,
                             allow_resize: bool, progress_callback=None) -> Tuple:
        original_width, original_height = img.size

        if output_format == "png":
            return self._compress_png(img, target_bytes, progress_callback)

        best_img = None
        best_quality = 95
        best_size = float('inf')
        best_resized = False

        if output_format in ('jpg', 'webp'):
            # 二分搜索：找到"能达标的最大质量"，保证画质优先
            lo, hi = quality_floor, 95
            best_q = 95
            best_s = float('inf')
            best_image_data = None

            for _ in range(12):
                if lo > hi:
                    break
                mid = (lo + hi) // 2

                buffer = io.BytesIO()
                try:
                    save_kwargs = {"format": _pil_format(output_format)}
                    if output_format == "jpg":
                        save_kwargs["quality"] = mid
                        save_kwargs["optimize"] = True
                        save_kwargs["progressive"] = True
                    elif output_format == "webp":
                        save_kwargs["quality"] = mid
                        save_kwargs["method"] = 6

                    img.save(buffer, **save_kwargs)
                    current_size = buffer.tell()

                    if progress_callback:
                        progress_callback(
                            min(int((95 - mid) / (95 - quality_floor) * 80), 80),
                            f"尝试质量 {mid}: {self._format_size(current_size)}"
                        )

                    if current_size <= target_bytes:
                        if current_size > best_s:
                            best_s = current_size
                            best_q = mid
                            best_image_data = buffer.getvalue()
                        hi = mid - 1
                    else:
                        lo = mid + 1

                except Exception:
                    break

            if best_image_data is not None and best_s <= target_bytes:
                best_quality = best_q
                best_size = best_s
                best_img_data = best_image_data
                best_resized = False

        if best_size <= target_bytes:
            result_img = Image.open(io.BytesIO(best_img_data))
            return result_img, best_quality, best_size, False

        if allow_resize:
            scale = 0.85
            for attempt in range(8):
                current_w = int(original_width * (scale ** (attempt + 1)))
                current_h = int(original_height * (scale ** (attempt + 1)))

                if current_w < 100 or current_h < 100:
                    break

                resized = img.resize((current_w, current_h), Image.LANCZOS)

                buffer = io.BytesIO()
                q = max(quality_floor, best_quality - attempt * 5)
                try:
                    save_kwargs = {"format": _pil_format(output_format)}
                    if output_format == "jpg":
                        save_kwargs["quality"] = q
                        save_kwargs["optimize"] = True
                    elif output_format == "webp":
                        save_kwargs["quality"] = q
                        save_kwargs["method"] = 6

                    resized.save(buffer, **save_kwargs)
                    new_size = buffer.tell()

                    if progress_callback:
                        progress_callback(
                            min(80 + attempt * 2, 95),
                            f"缩小到 {current_w}x{current_h}, 质量{q}: {self._format_size(new_size)}"
                        )

                    if new_size <= target_bytes:
                        result_img = Image.open(io.BytesIO(buffer.getvalue()))
                        return result_img, q, new_size, True

                except Exception:
                    break

        return None, 0, 0, False

    def _compress_png(self, img: 'Image.Image', target_bytes: int,
                       progress_callback=None) -> Tuple:
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True, compress_level=9)
        size = buffer.tell()

        if progress_callback:
            progress_callback(50, f"PNG优化: {self._format_size(size)}")

        if size <= target_bytes:
            result_img = Image.open(io.BytesIO(buffer.getvalue()))
            return result_img, 100, size, False

        w, h = img.size
        for scale in [0.9, 0.8, 0.7, 0.6, 0.5]:
            new_w, new_h = int(w * scale), int(h * scale)
            if new_w < 100:
                break
            resized = img.resize((new_w, new_h), Image.LANCZOS)
            buf = io.BytesIO()
            resized.save(buf, format="PNG", optimize=True, compress_level=9)
            new_size = buf.tell()

            if progress_callback:
                progress_callback(
                    min(60 + int((1 - scale) * 80), 95),
                    f"PNG缩小到 {new_w}x{new_h}: {self._format_size(new_size)}"
                )

            if new_size <= target_bytes:
                result_img = Image.open(io.BytesIO(buf.getvalue()))
                return result_img, 100, new_size, True

        return None, 0, 0, False

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
