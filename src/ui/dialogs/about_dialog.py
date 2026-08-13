# -*- coding: utf-8 -*-
"""
软件信息对话框

展示软件介绍、功能特性、更新日志（向下滚动查看）以及作者信息（博客园 / QQ）。
更新日志读取项目根目录的 CHANGELOG.md，打包后从 PyInstaller 资源目录读取。
"""

import os
import sys
import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextBrowser, QWidget
)

from ..styles.theme import get_theme_colors
from ..widgets.icon_drawer import get_icon_pixmap

# ===== 应用信息常量 =====
APP_NAME = "满木工具箱"
APP_VERSION = "1.3.8"
APP_SLOGAN = "完全本地运行的离线文件处理工具箱"
BLOG_NAME = "博客园 · alloverzyt"
BLOG_URL = "https://www.cnblogs.com/alloverzyt"
QQ_NUMBER = "3119313758"

FEATURES = [
    "PDF 无损转图片、合并拆分、压缩、水印、加解密",
    "图片 格式转换 / 按大小压缩(二分搜索) / 去背景 / EXIF",
    "文档 PPT/Word/Excel 转PDF / PPT转图片(LibreOffice)",
    "二维码 生成与识别 / vCard / Wi-Fi",
    "媒体 视频转GIF / 音频提取(FFmpeg)",
    "文件 批量重命名 / 查重 / 哈希 / 智能归档",
    "实用工具 时间戳转换 / 颜色转换 / Base64",
]


def _load_changelog_text() -> str:
    """读取 CHANGELOG.md 内容（打包后从 _MEIPASS 读取，开发模式从项目根读取）"""
    candidates = []
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", "")
        if base:
            candidates.append(os.path.join(base, "CHANGELOG.md"))
    # 开发模式：src/ui/dialogs -> 上三级 = 项目根
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.abspath(os.path.join(here, "..", "..", "..", "CHANGELOG.md")))
    for path in candidates:
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception:
            continue
    return "暂无更新日志"


class AboutDialog(QDialog):
    """软件信息对话框"""

    def __init__(self, theme_config: dict, parent=None):
        super().__init__(parent)
        self._theme_config = theme_config or {}
        self._colors = get_theme_colors(
            self._theme_config.get("current_theme", "dark"),
            self._theme_config.get("custom_accent"),
        )
        self.setWindowTitle(f"关于 {APP_NAME}")
        self.setMinimumSize(500, 620)
        self.resize(520, 680)
        self._setup_ui()

    # ==================== 小部件构建 ====================

    def _make_section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        font = QFont("Microsoft YaHei UI", 15)
        font.setBold(True)
        label.setFont(font)
        label.setStyleSheet(f"color: {self._colors['accent']}; background: transparent;")
        return label

    def _make_hr(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {self._colors['border']}; border: none;")
        return line

    def _make_info_row(self, tag_text: str, value_text: str, btn_text: str, on_click) -> QWidget:
        """作者信息行：左侧标签 + 值，右侧按钮"""
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)

        tag = QLabel(tag_text)
        tf = QFont("Microsoft YaHei UI", 12)
        tf.setBold(True)
        tag.setFont(tf)
        tag.setFixedWidth(72)
        tag.setStyleSheet("background: transparent;")
        h.addWidget(tag)

        value = QLabel(value_text)
        value.setFont(QFont("Microsoft YaHei UI", 12))
        value.setStyleSheet(f"color: {self._colors['text_secondary']}; background: transparent;")
        h.addWidget(value)
        h.addStretch()

        btn = QPushButton(btn_text)
        btn.setMinimumHeight(32)
        btn.setMinimumWidth(92)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(on_click)
        h.addWidget(btn)
        return row

    # ==================== 界面搭建 ====================

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ===== 滚动区：头部 + 功能 + 更新日志 + 作者 =====
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(14)

        # ---- 头部：图标 + 名称 + 标语 + 版本徽章 ----
        header_row = QHBoxLayout()
        header_row.setSpacing(14)
        icon_label = QLabel()
        icon_pixmap = get_icon_pixmap("box", 44, self._colors["accent"])
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        header_row.addWidget(icon_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        name_label = QLabel(APP_NAME)
        nf = QFont("Microsoft YaHei UI", 22)
        nf.setBold(True)
        name_label.setFont(nf)
        name_label.setStyleSheet("background: transparent;")
        title_col.addWidget(name_label)

        slogan_label = QLabel(APP_SLOGAN)
        slogan_label.setFont(QFont("Microsoft YaHei UI", 12))
        slogan_label.setStyleSheet(f"color: {self._colors['text_secondary']}; background: transparent;")
        title_col.addWidget(slogan_label)
        header_row.addLayout(title_col, 1)

        ver_label = QLabel(f"v{APP_VERSION}")
        vf = QFont("Microsoft YaHei UI", 13)
        vf.setBold(True)
        ver_label.setFont(vf)
        ver_label.setStyleSheet(
            f"color: {self._colors['accent']}; background: transparent; "
            f"border: 1px solid {self._colors['accent']}; border-radius: 13px; "
            "padding: 4px 12px;"
        )
        header_row.addWidget(ver_label, 0, Qt.AlignTop)
        layout.addLayout(header_row)

        # ---- 功能特性 ----
        layout.addWidget(self._make_section_title("功能特性"))
        feature_label = QLabel("\n".join(f"· {f}" for f in FEATURES))
        feature_label.setFont(QFont("Microsoft YaHei UI", 12))
        feature_label.setWordWrap(True)
        feature_label.setStyleSheet("background: transparent;")
        layout.addWidget(feature_label)

        layout.addWidget(self._make_hr())

        # ---- 更新日志（向下滚动查看）----
        layout.addWidget(self._make_section_title("更新日志"))
        browser = QTextBrowser()
        browser.setReadOnly(True)
        browser.setFrameShape(QFrame.NoFrame)
        browser.setOpenExternalLinks(False)
        browser.document().setDefaultStyleSheet(
            f"body {{ color: {self._colors['text_primary']}; }}"
        )
        browser.setStyleSheet("QTextBrowser { background: transparent; border: none; }")
        browser.setMarkdown(_load_changelog_text())
        browser.setMinimumHeight(280)
        layout.addWidget(browser)

        layout.addWidget(self._make_hr())

        # ---- 关于作者 ----
        layout.addWidget(self._make_section_title("关于作者"))
        author_label = QLabel("欢迎交流，感谢支持！")
        author_label.setFont(QFont("Microsoft YaHei UI", 12))
        author_label.setStyleSheet("background: transparent;")
        layout.addWidget(author_label)

        layout.addWidget(self._make_info_row(
            "博客", BLOG_NAME, "访问博客", lambda: webbrowser.open(BLOG_URL)
        ))
        layout.addWidget(self._make_info_row(
            "联系我", f"QQ：{QQ_NUMBER}", "复制QQ号",
            lambda: QGuiApplication.clipboard().setText(QQ_NUMBER)
        ))

        # 版权行
        credit_label = QLabel("图标: Lucide Icons (ISC License) · 框架: PySide6 (Qt6)")
        credit_label.setFont(QFont("Microsoft YaHei UI", 10))
        credit_label.setStyleSheet(f"color: {self._colors['text_secondary']}; background: transparent;")
        layout.addWidget(credit_label)

        layout.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        # ===== 底部按钮 =====
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(28, 12, 28, 16)
        btn_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("primaryBtn")
        close_btn.setMinimumWidth(140)
        close_btn.setMinimumHeight(40)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)
