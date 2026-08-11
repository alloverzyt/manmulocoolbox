# -*- coding: utf-8 -*-
"""
主题设置对话框（调色盘）
设计原则：简洁直接，点哪个颜色就用哪个颜色。
主题深浅模式由主窗口右上角按钮切换，调色盘内不再重复。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QColorDialog, QGroupBox
)

from ..styles.theme import (
    load_theme_config, save_theme_config,
    PRESET_COLORS, DEFAULT_THEMES,
    get_theme_colors
)


# 「默认颜色」—— 直接做成色块放在预设最前面，替代 Radio 选项
_DEFAULT_COLORS = [
    {"name": "深色·雾蓝默认", "color": DEFAULT_THEMES["dark"]["accent"]},
    {"name": "浅色·雾蓝默认", "color": DEFAULT_THEMES["light"]["accent"]},
]


class ColorButton(QPushButton):
    """单个颜色按钮：被选中时显示粗白描边"""

    def __init__(self, color_hex: str, name: str, parent=None):
        super().__init__(parent)
        self._color = color_hex
        self._selected = False
        self.setFixedSize(52, 52)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"{name}\n{color_hex}")
        self._refresh_style()

    def color(self) -> str:
        return self._color

    def set_selected(self, selected: bool):
        self._selected = selected
        self._refresh_style()

    def _refresh_style(self):
        border_width = 3 if self._selected else 2
        border_color = "#FFFFFF" if self._selected else "rgba(120,120,120,0.25)"
        shadow = "0 0 0 2px rgba(0,0,0,0.08)" if self._selected else "none"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                border: {border_width}px solid {border_color};
                border-radius: 12px;
            }}
            QPushButton:hover {{
                border: {border_width}px solid #FFFFFF;
            }}
        """)


class ThemeSettingsDialog(QDialog):
    """调色盘 - 极简版：只有选颜色 + 预览 + 应用/取消"""

    theme_changed = Signal(str, str)  # theme_name, accent_color

    def __init__(self, config: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("调色盘")
        self.setMinimumWidth(540)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        if config:
            self._config = dict(config)
        else:
            self._config = load_theme_config()
        self._current_theme = self._config.get("current_theme", "dark")

        # 主色调回退：custom_accent 可能存在但值为 None/空（JSON null/未设置）
        # 必须用"显式判断真假值"，不能只靠 dict.get(key, 默认) 因为 key 存在但值为 None 时仍返回 None
        custom = self._config.get("custom_accent")
        if not custom:
            custom = DEFAULT_THEMES[self._current_theme]["accent"]
        self._selected_accent = custom

        self._color_buttons = []  # 所有色块按钮引用，用于切换选中态
        self._setup_ui()

    # ------------------------------------------------------------------ API
    def get_config(self) -> dict:
        return self._config

    # ---------------------------------------------------------------- UI
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(16)

        layout.addWidget(self._build_color_panel())
        layout.addWidget(self._build_preview_panel(), 1)
        layout.addLayout(self._build_button_bar())

        self._sync_selection_from_accent()
        self._update_preview()

    def _build_color_panel(self) -> QGroupBox:
        """主色调面板（默认色 + 预设色 + 自定义按钮，全部同一行风格）"""
        panel = QGroupBox("主色调")
        outer = QVBoxLayout(panel)
        outer.setSpacing(10)

        hint = QLabel("点击颜色方块，即可把整个界面的主色调改为该颜色")
        hint.setStyleSheet("color: rgba(120,120,120,0.85); font-size: 12px;")
        outer.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(80)
        outer.addWidget(scroll)

        row_container = QWidget()
        row = QHBoxLayout(row_container)
        row.setContentsMargins(4, 6, 4, 6)
        row.setSpacing(10)
        scroll.setWidget(row_container)

        # 1) 默认色（2个，替代原来的"使用默认颜色"Radio）
        for p in _DEFAULT_COLORS:
            btn = ColorButton(p["color"], p["name"])
            btn.clicked.connect(lambda _=False, c=p["color"]: self._pick_color(c))
            self._color_buttons.append(btn)
            row.addWidget(btn)

        # 分隔符
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: rgba(120,120,120,0.25);")
        sep.setFixedHeight(52)
        row.addWidget(sep)

        # 2) 预设莫奈色
        for p in PRESET_COLORS:
            btn = ColorButton(p["color"], p["name"])
            btn.clicked.connect(lambda _=False, c=p["color"]: self._pick_color(c))
            self._color_buttons.append(btn)
            row.addWidget(btn)

        # 再一个分隔符
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet("color: rgba(120,120,120,0.25);")
        sep2.setFixedHeight(52)
        row.addWidget(sep2)

        # 3) 自定义按钮（"+"形状，打开颜色选择器）
        self._custom_btn = QPushButton("+")
        self._custom_btn.setFixedSize(52, 52)
        self._custom_btn.setCursor(Qt.PointingHandCursor)
        self._custom_btn.setToolTip("自定义颜色…")
        self._custom_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 2px dashed rgba(120,120,120,0.35);
                border-radius: 12px;
                color: rgba(120,120,120,0.7);
                font-size: 26px;
                font-weight: bold;
            }
            QPushButton:hover {
                border: 2px solid rgba(120,120,120,0.7);
                color: rgba(50,50,50,0.9);
            }
        """)
        self._custom_btn.clicked.connect(self._open_custom_color)
        row.addWidget(self._custom_btn)

        # 当前颜色值（显示在右上角，直观）
        self._code_label = QLabel()
        self._code_label.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 12px;"
            "color: rgba(120,120,120,0.8);"
        )
        code_row = QHBoxLayout()
        code_row.addStretch()
        code_row.addWidget(self._code_label)
        outer.addLayout(code_row)

        return panel

    def _build_preview_panel(self) -> QGroupBox:
        """效果预览：一张卡片 + 两个按钮，直观展示主色调"""
        panel = QGroupBox("效果预览")
        v = QVBoxLayout(panel)
        self._preview_label = QLabel()
        self._preview_label.setMinimumHeight(140)
        self._preview_label.setWordWrap(True)
        self._preview_label.setTextFormat(Qt.RichText)
        v.addWidget(self._preview_label)
        return panel

    def _build_button_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.addStretch()

        cancel = QPushButton("取消")
        cancel.setMinimumWidth(100)
        cancel.setMinimumHeight(40)
        cancel.clicked.connect(self.reject)
        bar.addWidget(cancel)

        apply_ = QPushButton("应用")
        apply_.setMinimumWidth(100)
        apply_.setMinimumHeight(40)
        apply_.setObjectName("primaryBtn")
        apply_.clicked.connect(self._on_apply)
        bar.addWidget(apply_)

        return bar

    # ------------------------------------------------------------ handlers
    def _pick_color(self, color_hex: str):
        """色块被点击 → 直接选中 + 更新预览"""
        self._selected_accent = color_hex
        self._sync_selection_from_accent()
        self._update_preview()

    def _open_custom_color(self):
        """打开系统颜色选择器，选完也像普通色块一样生效"""
        init = QColor(self._selected_accent)
        c = QColorDialog.getColor(init, self, "自定义颜色")
        if c.isValid():
            self._pick_color(c.name())

    def _sync_selection_from_accent(self):
        """根据当前 accent 把对应色块设为选中态，其他取消"""
        # 防御：任何原因导致 accent 为空时回退默认
        if not self._selected_accent:
            self._selected_accent = DEFAULT_THEMES[self._current_theme]["accent"]
        selected = self._selected_accent.lower()
        for btn in self._color_buttons:
            btn.set_selected(btn.color().lower() == selected)
        self._code_label.setText(self._selected_accent.upper())

    def _update_preview(self):
        """刷新预览卡片"""
        colors = get_theme_colors(self._current_theme, self._selected_accent)
        bg = colors["bg_primary"]
        card = colors["bg_tertiary"]
        accent = colors["accent"]
        accent_hover = colors["accent_hover"]
        tp = colors["text_primary"]
        ts = colors["text_secondary"]
        border = colors["border"]

        # 深/浅色模式下按钮文字色
        dark = self._current_theme == "dark"
        btn_text = "#121212" if dark else "#FFFFFF"

        self._preview_label.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                border-radius: 14px;
            }}
        """)
        self._preview_label.setText(f"""
        <div style="padding: 18px;">
          <div style="background: {card}; border: 1px solid {border};
                      border-radius: 14px; padding: 16px;">
            <div style="display: flex; align-items: center; gap: 12px;">
              <div style="width: 44px; height: 44px; border-radius: 10px;
                          background: {accent};"></div>
              <div style="flex: 1;">
                <div style="color: {tp}; font-size: 15px; font-weight: bold;
                            margin-bottom: 4px;">工具名称</div>
                <div style="color: {ts}; font-size: 12px;">这是工具的描述文字示例</div>
              </div>
              <div style="font-size: 18px; color: {ts};">›</div>
            </div>
            <div style="margin-top: 16px; display: flex; gap: 10px;">
              <div style="padding: 8px 18px; border-radius: 10px;
                          background: {accent}; color: {btn_text};
                          font-weight: bold; font-size: 13px;">主按钮</div>
              <div style="padding: 8px 18px; border-radius: 10px;
                          background: {accent_hover}; color: {btn_text};
                          font-size: 13px; opacity: 0.9;">次按钮</div>
            </div>
          </div>
        </div>
        """)

    def _on_apply(self):
        """确认应用：保存并通知主窗口"""
        # 判断当前颜色是否等于该模式下的默认色：等于则不存 custom_accent
        default_accent = DEFAULT_THEMES[self._current_theme]["accent"]
        if self._selected_accent.lower() == default_accent.lower():
            new_accent = None
        else:
            new_accent = self._selected_accent

        self._config["current_theme"] = self._current_theme
        self._config["custom_accent"] = new_accent
        save_theme_config(self._config)

        self.theme_changed.emit(self._current_theme, new_accent or "")
        self.accept()
