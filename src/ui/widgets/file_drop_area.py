# -*- coding: utf-8 -*-
"""
文件拖拽区域组件

支持拖拽文件或点击按钮选择文件/文件夹。
紧凑设计，圆角边框，占比约20%高度。
"""

import os
from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont, QPixmap, QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QFileDialog

from ...utils.file_utils import list_files_from_dropped
from .icon_drawer import get_icon_pixmap, get_icon_color


class FileDropArea(QWidget):
    """文件拖拽区域 - 紧凑圆角设计"""

    files_dropped = Signal(list)
    files_selected = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("fileDropArea")
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.setMaximumHeight(160)
        self.setProperty("dragging", "false")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 14, 20, 14)
        self._layout.setSpacing(4)

        # 图标行 - 水平居中
        icon_row = QHBoxLayout()
        icon_row.addStretch()
        icon_label = QLabel()
        icon_pixmap = get_icon_pixmap("folder", 28, get_icon_color())
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedHeight(34)
        icon_row.addWidget(icon_label)
        icon_row.addStretch()

        # 标题
        self._title = QLabel("拖拽文件到此处")
        self._title.setAlignment(Qt.AlignCenter)
        title_font = QFont("Microsoft YaHei UI", 13)
        title_font.setBold(True)
        self._title.setFont(title_font)

        # 副标题
        self._subtitle = QLabel("或点击下方按钮选择")
        self._subtitle.setAlignment(Qt.AlignCenter)
        sub_font = QFont("Microsoft YaHei UI", 10)
        self._subtitle.setFont(sub_font)

        # 成功提示条：拖入文件后显示，明确告知"已添加"
        self._added_label = QLabel("")
        self._added_label.setAlignment(Qt.AlignCenter)
        added_font = QFont("Microsoft YaHei UI", 11)
        added_font.setBold(True)
        self._added_label.setFont(added_font)
        self._added_label.setMinimumHeight(24)
        self._added_label.hide()

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self._select_btn = QPushButton("选择文件")
        self._select_btn.setObjectName("primaryBtn")
        self._select_btn.setMinimumWidth(110)
        self._select_btn.setMinimumHeight(34)
        self._select_btn.clicked.connect(self._on_select_clicked)

        self._folder_btn = QPushButton("选择文件夹")
        self._folder_btn.setMinimumWidth(110)
        self._folder_btn.setMinimumHeight(34)
        self._folder_btn.clicked.connect(self._on_folder_clicked)

        btn_layout.addWidget(self._select_btn)
        btn_layout.addWidget(self._folder_btn)
        btn_layout.addStretch()

        self._layout.addStretch()
        self._layout.addLayout(icon_row)
        self._layout.addWidget(self._title)
        self._layout.addWidget(self._subtitle)
        self._layout.addWidget(self._added_label)
        self._layout.addSpacing(6)
        self._layout.addLayout(btn_layout)
        self._layout.addStretch()

    def _success_color(self) -> str:
        """成功提示色：深色主题亮绿，浅色主题深绿"""
        is_dark = self.palette().window().color().lightness() < 128
        return "#A5D6A7" if is_dark else "#4CAF50"

    def set_added_count(self, count: int):
        """设置已添加文件数：>0 时显示成功反馈，明确告知文件已就绪"""
        if count > 0:
            self._added_label.setText(f"✓ 已添加 {count} 个文件，可继续拖入或点击按钮追加")
            self._added_label.setStyleSheet(
                f"color: {self._success_color()}; background: transparent; font-size: 12px;"
            )
            self._added_label.show()
            self._title.setText("文件已就绪")
            self._subtitle.setText("可继续拖入文件，或点击下方按钮追加")
        else:
            self._added_label.hide()
            self._title.setText("拖拽文件到此处")
            self._subtitle.setText("或点击下方按钮选择")

    def _on_select_clicked(self):
        """选择文件"""
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件")
        if files:
            self.files_selected.emit(files)

    def _on_folder_clicked(self):
        """选择文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            files = []
            for f in os.listdir(folder):
                path = os.path.join(folder, f)
                if os.path.isfile(path):
                    files.append(path)
            if files:
                self.files_selected.emit(files)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            self.setProperty("dragging", "true")
            self.style().unpolish(self)
            self.style().polish(self)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.setProperty("dragging", "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event: QDropEvent):
        self.setProperty("dragging", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        files = list_files_from_dropped(event.mimeData())
        if files:
            self.files_dropped.emit(files)
