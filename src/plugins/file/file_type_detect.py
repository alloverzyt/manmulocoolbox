import os
import json
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir, format_size


class FileTypeDetectPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "file_type_detect"

    @property
    def name(self) -> str:
        return "格式识别"

    @property
    def description(self) -> str:
        return "识别文件的真实格式(Magic Number检测)，查看详细文件信息"

    @property
    def category(self) -> str:
        return "file"

    @property
    def icon(self) -> str:
        return "search"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["*"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["txt", "json"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "save_report": {
                "type": "boolean",
                "label": "保存报告到文件",
                "default": True
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        file_path = input_data.file_paths[0]
        options = input_data.options

        results = []
        try:
            file_size = os.path.getsize(file_path)
            ext = os.path.splitext(file_path)[1].lower()

            mime_type = self._guess_mime(file_path)
            real_type = self._detect_by_magic(file_path)

            result = {
                "file_name": os.path.basename(file_path),
                "file_path": file_path,
                "file_size": file_size,
                "file_size_readable": format_size(file_size),
                "extension": ext,
                "mime_type": mime_type,
                "detected_type": real_type,
                "extension_match": ext.lstrip('.').lower() in real_type.lower().split('/')[0] if real_type else "unknown",
                "modified_time": os.path.getmtime(file_path),
                "is_hidden": os.path.basename(file_path).startswith('.')
            }
            results.append(result)

            report_lines = [
                f"文件格式检测报告",
                f"{'=' * 50}",
                f"文件名: {result['file_name']}",
                f"路径: {result['file_path']}",
                f"大小: {result['file_size_readable']} ({file_size} 字节)",
                f"扩展名: {result['extension'] or '(无)'}",
                f"MIME类型: {result['mime_type']}",
                f"真实类型: {result['detected_type']}",
                f"扩展名匹配: {'✓ 匹配' if result['extension_match'] else '✗ 不匹配或未知'}",
                f"",
                f"建议: {self._get_suggestion(result)}",
            ]

            output_paths = []
            if options.get("save_report", True):
                output_dir = get_output_dir(file_path, options.get("output_dir", ""))
                ensure_dir(output_dir)
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_path = os.path.join(output_dir, f"{base_name}_info.json")

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                output_paths.append(output_path)

            return PluginResult(
                success=True,
                output_paths=output_paths,
                message="\n".join(report_lines)
            )

        except Exception as e:
            return PluginResult(success=False, error=f"格式识别失败: {str(e)}")

    def _guess_mime(self, file_path: str) -> str:
        ext_map = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.tiff': 'image/tiff',
            '.mp3': 'audio/mpeg',
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.zip': 'application/zip',
            '.rar': 'application/x-rar-compressed',
            '.7z': 'application/x-7z-compressed',
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.py': 'text/x-python',
        }
        ext = os.path.splitext(file_path)[1].lower()
        return ext_map.get(ext, 'application/octet-stream')

    def _detect_by_magic(self, file_path: str) -> str:
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)

            if len(header) < 4:
                return "文件太小，无法检测"

            magic = header[:8]

            if magic[:4] == b'%PDF':
                return 'PDF文档'
            elif magic[:4] == b'PK\x03\x04':
                return 'ZIP压缩包(或DOCX/XLSX/PPTX)'
            elif magic[:4] == b'\xd0\xcf\x11\xe0':
                return 'OLE复合文档(DOC/XLS/PPT旧格式)'
            elif magic[:4] == b'\x89PNG':
                return 'PNG图片'
            elif magic[:3] == b'\xff\xd8\xff':
                return 'JPEG图片'
            elif magic[:4] == b'GIF8':
                return 'GIF图片'
            elif magic[:2] == b'BM':
                return 'BMP图片'
            elif magic[:4] == b'RIFF' and header[8:12] == b'WEBP':
                return 'WebP图片'
            elif magic[:4] == b'RIFF' and header[8:12] == b'WAVE':
                return 'WAV音频'
            elif magic[:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'):
                return 'MP3音频'
            elif magic[:4] == b'\x1aE\xdf\xa3':
                return 'WEBM/Matroska视频'
            elif magic[:3] == b'MZ\x90':
                return 'PE可执行文件/DLL'
            elif magic[:4] == b'7z\xbc\xaf\x27\x1c':
                return '7z压缩包'
            elif magic[:4] == b'Rar!':
                return 'RAR压缩包'
            elif header[:1] == b'{':
                return 'JSON或文本文件'
            elif header[:1] == b'[':
                return 'JSON数组或文本文件'
            elif all(32 <= b < 127 or b in (9, 10, 13) for b in header):
                return '文本/代码文件'
            else:
                return f'未知二进制文件 (头部: {magic.hex()})'

        except Exception:
            return "无法读取文件"

    def _get_suggestion(self, result: Dict) -> str:
        ext = result['extension'].lstrip('.').lower()
        detected = result['detected_type']

        suggestions = []

        if ext == 'pdf' and 'PDF' in detected:
            suggestions.append("✓ 正常的PDF文件")
        elif ext == 'pdf' and 'PDF' not in detected:
            suggestions.append("⚠️ 扩展名是PDF但内容不是PDF，文件可能已损坏或被篡改")

        if ext in ('png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp') and '图片' not in detected:
            suggestions.append("⚠️ 扩展名是图片格式但内容不匹配")

        if 'ZIP' in detected and ext not in ('zip', 'docx', 'xlsx', 'pptx', 'jar'):
            suggestions.append("💡 实际是ZIP格式，可能是DOCX/XLSX/PPTX或其他ZIP容器")

        if not suggestions:
            suggestions.append("✓ 文件格式正常")

        return "; ".join(suggestions)
