# -*- coding: utf-8 -*-
"""
工具卡片组件

展示单个工具/插件信息，包含图标、名称、描述。
点击整个卡片选择工具，不用单独的按钮。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap, QColor
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy

from .icon_drawer import get_icon_pixmap, create_plugin_icon


class ToolCard(QFrame):
    """工具卡片 - 点击选择"""

    run_requested = Signal()

    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self._plugin = plugin
        self.setObjectName("toolCard")
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("selected", "false")
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        # 图标
        icon_label = QLabel()
        icon_pixmap = create_plugin_icon(self._plugin.icon, 28)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # 信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)

        name_label = QLabel(self._plugin.name)
        name_font = QFont("Microsoft YaHei UI", 14)
        name_font.setBold(True)
        name_label.setFont(name_font)

        desc_label = QLabel(self._plugin.description)
        desc_font = QFont("Microsoft YaHei UI", 11)
        desc_label.setFont(desc_font)
        desc_label.setWordWrap(True)

        info_layout.addWidget(name_label)
        info_layout.addWidget(desc_label)
        layout.addLayout(info_layout, 1)

        # 选中箭头
        arrow_label = QLabel("›")
        arrow_font = QFont("Microsoft YaHei UI", 22)
        arrow_label.setFont(arrow_font)
        arrow_label.setFixedSize(20, 20)
        arrow_label.setAlignment(Qt.AlignCenter)
        arrow_label.setStyleSheet("color: rgba(255,255,255,0.15);")
        layout.addWidget(arrow_label)

    def mousePressEvent(self, event):
        """点击发出信号"""
        if event.button() == Qt.LeftButton:
            self.run_requested.emit()
        super().mousePressEvent(event)
