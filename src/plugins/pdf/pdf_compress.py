import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class PdfCompressPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "pdf_compress"

    @property
    def name(self) -> str:
        return "PDF压缩"

    @property
    def description(self) -> str:
        return "压缩PDF文件大小，支持多级压缩质量"

    @property
    def category(self) -> str:
        return "pdf"

    @property
    def icon(self) -> str:
        return "compress"

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
            "quality": {
                "type": "select",
                "label": "压缩质量",
                "default": "medium",
                "options": [
                    {"label": "低压缩(高质量)", "value": "low"},
                    {"label": "中等压缩(推荐)", "value": "medium"},
                    {"label": "高压缩(小体积)", "value": "high"},
                    {"label": "最大压缩(最小体积)", "value": "maximum"}
                ]
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        file_path = input_data.file_paths[0]
        options = input_data.options
        quality = options.get("quality", "medium")

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}_compressed.pdf")

        try:
            import fitz

            # 兼容不同 PyMuPDF 版本：1.25+ 已移除 fitz.GARBAGE_REMOVE/COMPRESS_DEFLATE 常量
            garbage_full = getattr(fitz, 'GARBAGE_FULL', 3)          # 全面清理: 删除未用对象+去重
            compress_deflate = getattr(fitz, 'COMPRESS_DEFLATE', 1)  # 1 = DEFLATE 流压缩

            doc = fitz.open(file_path)
            original_size = os.path.getsize(file_path)

            quality_map = {
                "low": 90,
                "medium": 70,
                "high": 50,
                "maximum": 20
            }
            target_quality = quality_map.get(quality, 70)

            # 1) 按所选质量重编码嵌入图像（PyMuPDF 1.25+ 提供 rewrite_images）
            rewrite = getattr(doc, 'rewrite_images', None)
            if rewrite is not None:
                try:
                    rewrite(quality=target_quality, set_to_gray=False)
                except Exception:
                    pass

            # 2) 结构级压缩：未用对象清理 + 流 deflate 压缩
            for page in doc:
                for img in page.get_images(full=True):
                    xref = img[0]
                    try:
                        doc.update_stream(xref, compress=compress_deflate)
                    except Exception:
                        pass

            doc.save(
                output_path,
                garbage=garbage_full,
                deflate=True,
                clean=True
            )
            doc.close()

            compressed_size = os.path.getsize(output_path)
            ratio = (1 - compressed_size / max(original_size, 1)) * 100

            if ratio > 0:
                return PluginResult(
                    success=True,
                    output_paths=[output_path],
                    message=f"压缩完成: {original_size // 1024}KB → {compressed_size // 1024}KB (减少 {ratio:.1f}%)"
                )
            else:
                return PluginResult(
                    success=True,
                    output_paths=[output_path],
                    message=f"已优化: {original_size // 1024}KB → {compressed_size // 1024}KB"
                )

        except ImportError:
            return PluginResult(success=False, error="PyMuPDF 未安装")
        except Exception as e:
            return PluginResult(success=False, error=f"压缩失败: {str(e)}")
