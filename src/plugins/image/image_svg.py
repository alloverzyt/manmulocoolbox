import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_filename, get_output_dir


class ImageSvgPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "image_svg"

    @property
    def name(self) -> str:
        return "SVG转PNG"

    @property
    def description(self) -> str:
        return "将SVG矢量图转换为PNG位图"

    @property
    def category(self) -> str:
        return "image"

    @property
    def icon(self) -> str:
        return "edit"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_input_formats(self) -> List[str]:
        return ["svg"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["png"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "scale": {
                "type": "integer",
                "label": "缩放倍数",
                "default": 2,
                "min": 1,
                "max": 8
            },
            "background": {
                "type": "select",
                "label": "背景",
                "default": "transparent",
                "options": [
                    {"label": "透明", "value": "transparent"},
                    {"label": "白色", "value": "white"},
                    {"label": "黑色", "value": "black"}
                ]
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        file_path = input_data.file_paths[0]
        options = input_data.options
        scale = options.get("scale", 2)
        bg = options.get("background", "transparent")

        # 用 QtSvg 渲染（应用自带，无需额外安装 cairosvg/cairo DLL）
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import QRectF, Qt
            from PySide6.QtGui import QColor, QImage, QPainter
            from PySide6.QtSvg import QSvgRenderer
        except ImportError:
            return PluginResult(success=False, error="PySide6 未安装，无法渲染SVG")

        output_dir = get_output_dir(file_path, options.get("output_dir", ""))
        ensure_dir(output_dir)

        base_name = get_filename(file_path)
        output_path = os.path.join(output_dir, f"{base_name}.png")

        try:
            # 复用主窗口的 Qt 实例；无 GUI 环境（如命令行）时临时创建
            app = QApplication.instance() or QApplication([])

            renderer = QSvgRenderer(file_path)
            if not renderer.isValid():
                return PluginResult(success=False, error="无法解析该SVG文件")

            base_w = renderer.defaultSize().width() or 100
            base_h = renderer.defaultSize().height() or 100
            w = max(1, int(base_w * scale))
            h = max(1, int(base_h * scale))

            image = QImage(w, h, QImage.Format_ARGB32)
            if bg == "white":
                image.fill(QColor("white"))
            elif bg == "black":
                image.fill(QColor("black"))
            else:
                image.fill(Qt.transparent)

            painter = QPainter(image)
            try:
                renderer.render(painter, QRectF(0, 0, w, h))
            finally:
                painter.end()

            if not image.save(output_path) or not os.path.isfile(output_path):
                return PluginResult(success=False, error="PNG 保存失败")

            return PluginResult(
                success=True,
                output_paths=[output_path],
                message=f"SVG转PNG成功 (缩放{scale}倍)"
            )

        except Exception as e:
            return PluginResult(success=False, error=f"SVG转PNG失败: {str(e)}")
