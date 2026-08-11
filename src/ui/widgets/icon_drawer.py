# -*- coding: utf-8 -*-
"""
图标绘制模块

使用 Lucide Icons（ISC License，免费商用）内嵌SVG数据，
通过 QSvgRenderer 渲染到 QPixmap，支持任意尺寸和颜色。
深色模式自动使用浅色图标，浅色模式自动使用深色图标。
"""

from PySide6.QtCore import Qt, QByteArray, QSize
from PySide6.QtGui import QPixmap, QColor, QPainter
from PySide6.QtSvg import QSvgRenderer

from ._svg_icons import SVG_ICONS

# 默认图标颜色
_DEFAULT_LIGHT_COLOR = QColor("#4B5563")
_DEFAULT_DARK_COLOR = QColor("#D1D5DB")

# 当前全局图标颜色
_icon_color = _DEFAULT_DARK_COLOR


def set_icon_color(color: QColor):
    """设置全局图标颜色（主题切换时调用）"""
    global _icon_color
    _icon_color = color


def get_icon_color() -> QColor:
    """获取当前图标颜色"""
    return _icon_color


def get_icon_pixmap(icon_key: str, size: int = 24, color: QColor = None) -> QPixmap:
    """
    根据图标键名获取渲染好的 QPixmap

    Args:
        icon_key: 图标键名（如 "pdf", "folder", "settings"）
        size: 图标像素尺寸
        color: 图标颜色，为 None 时使用全局颜色

    Returns:
        QPixmap 图标，透明背景
    """
    if color is None:
        color = _icon_color

    # 查找SVG
    svg_template = SVG_ICONS.get(icon_key)
    if svg_template is None:
        # 尝试直接用键名查找
        svg_template = SVG_ICONS.get(icon_key.lower())

    # 创建透明pixmap (考虑HiDPI)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    if svg_template is None:
        # 找不到图标，画一个简单的圆形占位符
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        pen_color = QColor(color)
        pen_color.setAlpha(80)
        painter.setPen(pen_color)
        painter.drawEllipse(4, 4, size - 8, size - 8)
        painter.end()
        return pixmap

    # 替换currentColor为目标颜色
    color_str = color.name() if isinstance(color, QColor) else str(color)
    svg_str = svg_template.replace("currentColor", color_str)

    # 使用QSvgRenderer渲染
    renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
    if renderer.isValid():
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        renderer.render(painter)
        painter.end()

    return pixmap


def create_plugin_icon(icon_key: str, size: int = 24) -> QPixmap:
    """
    创建插件图标（使用当前主题颜色）

    Args:
        icon_key: 图标键名
        size: 尺寸

    Returns:
        QPixmap
    """
    return get_icon_pixmap(icon_key, size)


def create_icon_label(icon_key: str, size: int = 20, parent=None) -> 'QLabel':
    """创建带图标的QLabel"""
    from PySide6.QtWidgets import QLabel
    label = QLabel(parent)
    pixmap = get_icon_pixmap(icon_key, size)
    label.setPixmap(pixmap)
    label.setFixedSize(size, size)
    label.setAlignment(Qt.AlignCenter)
    return label


# 保持向后兼容：图标键名映射（插件icon属性 -> SVG图标键）
ICON_MAP = {k: k for k in SVG_ICONS.keys()}
