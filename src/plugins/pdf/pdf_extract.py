import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir, get_filename


class PdfExtractPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "pdf_extract"

    @property
    def name(self) -> str:
        return "PDF提取"

    @property
    def description(self) -> str:
        return "提取PDF中的文本或图片内容"

    @property
    def category(self) -> str:
        return "pdf"

    @property
    def icon(self) -> str:
        return "upload"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["pdf"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["txt", "json", "png", "jpg"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "extract_type": {
                "type": "select",
                "label": "提取内容",
                "default": "text",
                "options": [
                    {"label": "文本", "value": "text"},
                    {"label": "图片", "value": "images"},
                    {"label": "表格", "value": "tables"}
                ]
            },
            "output_format": {
                "type": "select",
                "label": "输出格式",
                "default": "txt",
                "options": [
                    {"label": "TXT文本", "value": "txt"},
                    {"label": "JSON结构化", "value": "json"}
                ]
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        file_path = input_data.file_paths[0]
        options = input_data.options
        extract_type = options.get("extract_type", "text")

        try:
            import fitz
        except ImportError:
            return PluginResult(success=False, error="PyMuPDF 未安装")

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        base_name = get_filename(file_path)
        doc = fitz.open(file_path)

        output_paths = []

        if extract_type == "text":
            output_format = options.get("output_format", "txt")
            results = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                results.append({
                    "page": page_num + 1,
                    "text": text.strip()
                })

            if output_format == "json":
                import json
                output_path = os.path.join(output_dir, f"{base_name}_text.json")
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
            else:
                output_path = os.path.join(output_dir, f"{base_name}_text.txt")
                with open(output_path, 'w', encoding='utf-8') as f:
                    for r in results:
                        f.write(f"=== 第 {r['page']} 页 ===\n")
                        f.write(r['text'])
                        f.write("\n\n")

            output_paths.append(output_path)

        elif extract_type == "images":
            img_dir = os.path.join(output_dir, f"{base_name}_images")
            ensure_dir(img_dir)
            img_count = 0

            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images(full=True)

                for img_idx, img_info in enumerate(image_list):
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    img_path = os.path.join(
                        img_dir,
                        f"p{page_num + 1:03d}_img{img_idx + 1:02d}.{image_ext}"
                    )
                    with open(img_path, 'wb') as f:
                        f.write(image_bytes)
                    output_paths.append(img_path)
                    img_count += 1

            if img_count == 0:
                doc.close()
                return PluginResult(success=True, output_paths=[], message="PDF中没有发现图片")

        elif extract_type == "tables":
            try:
                import pdfplumber
                tables_data = []

                with pdfplumber.open(file_path) as pdf:
                    for page_num, page in enumerate(pdf.pages):
                        tables = page.extract_tables()
                        for t_idx, table in enumerate(tables):
                            tables_data.append({
                                "page": page_num + 1,
                                "table_index": t_idx + 1,
                                "data": table
                            })

                if not tables_data:
                    doc.close()
                    return PluginResult(success=True, output_paths=[], message="PDF中没有发现表格")

                output_path = os.path.join(output_dir, f"{base_name}_tables.json")
                import json
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(tables_data, f, ensure_ascii=False, indent=2)
                output_paths.append(output_path)

            except ImportError:
                doc.close()
                return PluginResult(success=False, error="pdfplumber 未安装。请运行: pip install pdfplumber")

        doc.close()

        return PluginResult(
            success=True,
            output_paths=output_paths,
            message=f"提取完成: {len(output_paths)} 项内容"
        )
