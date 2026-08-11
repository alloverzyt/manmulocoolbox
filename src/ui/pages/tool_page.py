# -*- coding: utf-8 -*-
"""
工具页面模块

卡片区占满页面，操作面板采用「底部抽屉」(bottom sheet) 模式：
选中工具 / 点击底部入口后，面板从底部平滑升起（overlay 浮动层），
只动画面板自身几何与透明度，不触发卡片区重排，杜绝动画抖动。

v1.3 交互：
- 面板收起时底部常驻「展开操作区 ▲」入口按钮
- 面板展开时右上角浮动「收起操作区 ▼」小按钮
- 工具少的分类自动切换为单列大卡片布局，页面不再空旷
- 卡片统一固定高度，同一页面高低一致
"""

from typing import List, Optional
import os
import json

from PySide6.QtCore import Qt, Signal, QTimer, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QGridLayout, QFrame, QSizePolicy, QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect
)

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...core.task_worker import TaskWorker
from ...core.events import EventBus
from ...utils.file_utils import list_files_from_dropped
from ..widgets.file_drop_area import FileDropArea
from ..widgets.tool_options_panel import ToolOptionsPanel
from ..widgets.progress_panel import ProgressPanel
from ..widgets.icon_drawer import create_plugin_icon

# ===== 操作面板高度记忆 =====

def _panel_config_path() -> str:
    """应用配置文件路径（与 main.py 的 _get_config_dir 保持一致）"""
    base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LocalToolbox")
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    return os.path.join(base, "app_config.json")


def _load_panel_height(default: int = 0) -> int:
    """读取记忆的操作面板高度（0 表示从未设置过）"""
    try:
        with open(_panel_config_path(), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return int(cfg.get("panel_height", default))
    except Exception:
        return default


def _save_panel_height(height: int):
    """保存操作面板高度（记忆用户手动拖拽的尺寸）"""
    try:
        path = _panel_config_path()
        cfg = {}
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        cfg["panel_height"] = int(height)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


class ToolPage(QWidget):
    """工具页面"""

    status_changed = Signal(str)
    panel_expanded = Signal()   # 面板展开（窗口右上角显示收起按钮）
    panel_collapsed = Signal()  # 面板收起（窗口右上角隐藏收起按钮）

    def __init__(self, plugins: List[BasePlugin], parent=None):
        super().__init__(parent)
        self._plugins = plugins
        self._current_plugin: Optional[BasePlugin] = None
        self._files: List[str] = []
        self._worker: Optional[TaskWorker] = None
        self._event_bus = EventBus()
        self._card_widgets = []
        self._arrow_labels = []
        self._panel_anim: Optional[QVariantAnimation] = None
        self._panel_target = 320
        # 页面空白区域也接受拖放，自动匹配能处理该文件的工具
        self.setAcceptDrops(True)
        self._setup_ui()
        self._setup_connections()

    # ==================== UI 构建 ====================

    def _setup_ui(self):
        """设置UI：卡片滚动区占满，面板/收起按钮为浮动层"""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # ===== 主滚动容器（卡片区，占满全部空间，不参与动画）=====
        self._main_scroll = QScrollArea()
        self._main_scroll.setWidgetResizable(True)
        self._main_scroll.setFrameShape(QFrame.NoFrame)
        self._main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer_layout.addWidget(self._main_scroll, 1)

        self._content = QWidget()
        self._main_scroll.setWidget(self._content)
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(16)

        # 标题
        self._title_label = QLabel("选择一个工具开始")
        title_font = QFont("Microsoft YaHei UI", 18)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        self._title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        content_layout.addWidget(self._title_label)

        # 工具卡片滚动区（自适应列数）
        self._tools_container = QWidget()
        self._tools_vbox = QVBoxLayout(self._tools_container)
        self._tools_vbox.setContentsMargins(0, 0, 0, 0)
        self._tools_vbox.setSpacing(12)

        self._tools_scroll = QScrollArea()
        self._tools_scroll.setWidget(self._tools_container)
        self._tools_scroll.setWidgetResizable(True)
        self._tools_scroll.setFrameShape(QFrame.NoFrame)
        self._tools_scroll.setMinimumHeight(120)
        self._tools_scroll.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        content_layout.addWidget(self._tools_scroll, 1)

        # ===== 底部「展开操作区」入口（面板收起时显示）=====
        self._expand_btn = QPushButton("展开操作区 ▲")
        self._expand_btn.setObjectName("expandBtn")
        self._expand_btn.setMinimumHeight(42)
        self._expand_btn.setCursor(Qt.PointingHandCursor)
        self._expand_btn.clicked.connect(self._on_expand_btn_clicked)
        expand_row = QHBoxLayout()
        expand_row.setContentsMargins(0, 4, 0, 12)
        expand_row.addStretch()
        expand_row.addWidget(self._expand_btn)
        expand_row.addStretch()
        outer_layout.addLayout(expand_row)

        self._build_tool_cards()

        # ===== 浮动层：操作面板（底部抽屉）=====
        self._build_panel()

    def _build_panel(self):
        """构建底部抽屉操作面板（overlay 浮动层，不占布局空间）"""
        self._panel = QWidget(self)
        self._panel.setObjectName("operationPanel")
        panel_layout = QVBoxLayout(self._panel)
        # 左右留白适配圆角；顶部给标题行让位，标题与按钮不再顶满圆角边缘
        panel_layout.setContentsMargins(20, 12, 20, 16)
        panel_layout.setSpacing(10)

        # 顶部拖拽手柄：鼠标悬浮时显示可上下拖动的提示，拖拽可自由调整面板高度
        self._panel_handle = QWidget()
        self._panel_handle.setObjectName("panelDragHandle")
        self._panel_handle.setFixedHeight(8)
        self._panel_handle.setCursor(Qt.SplitVCursor)
        self._panel_handle.mousePressEvent = self._handle_drag_press
        self._panel_handle.mouseMoveEvent = self._handle_drag_move
        self._panel_handle.mouseReleaseEvent = self._handle_drag_release
        panel_layout.addWidget(self._panel_handle)

        # 面板标题行：左侧工具名（强调色），右侧「收起」按钮（贴面板右上角，随面板出现）
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        self._panel_title = QLabel("操作设置")
        self._panel_title.setObjectName("panelTitle")
        panel_title_font = QFont("Microsoft YaHei UI", 13)
        panel_title_font.setBold(True)
        self._panel_title.setFont(panel_title_font)
        header_layout.addWidget(self._panel_title, 1)
        self._collapse_btn = QPushButton("收起操作区 ▼")
        self._collapse_btn.setObjectName("panelCollapseBtn")
        self._collapse_btn.setMinimumHeight(30)
        self._collapse_btn.setCursor(Qt.PointingHandCursor)
        self._collapse_btn.clicked.connect(self._collapse_panel)
        header_layout.addWidget(self._collapse_btn, 0, Qt.AlignVCenter)
        panel_layout.addLayout(header_layout)

        # 无需文件提示条（无文件工具时显示）
        self._no_file_label = QLabel("此工具无需文件，直接设置参数后点击「开始处理」即可")
        self._no_file_label.setAlignment(Qt.AlignCenter)
        self._no_file_label.setMinimumHeight(36)
        self._no_file_label.setObjectName("hintLabel")
        self._no_file_label.setVisible(False)
        panel_layout.addWidget(self._no_file_label)

        # 可滚动内容区（面板限高后内部仍可滚动查看）
        self._panel_scroll = QScrollArea()
        self._panel_scroll.setWidgetResizable(True)
        self._panel_scroll.setFrameShape(QFrame.NoFrame)
        self._panel_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._panel_content = QWidget()
        content_layout = QVBoxLayout(self._panel_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        # 文件拖拽区域
        self._drop_area = FileDropArea()
        content_layout.addWidget(self._drop_area)

        # 参数配置面板
        self._options_panel = ToolOptionsPanel()
        self._options_panel.setVisible(False)
        content_layout.addWidget(self._options_panel)

        # 进度面板
        self._progress_panel = ProgressPanel()
        self._progress_panel.setVisible(False)
        content_layout.addWidget(self._progress_panel)

        self._panel_scroll.setWidget(self._panel_content)
        panel_layout.addWidget(self._panel_scroll, 1)

        # 运行按钮（固定在面板底部，不随内容滚动）
        self._run_btn = QPushButton("开始处理")
        self._run_btn.setObjectName("primaryBtn")
        self._run_btn.setMinimumHeight(48)
        self._run_btn.setMinimumWidth(220)
        self._run_btn.setDisabled(True)
        self._run_btn.clicked.connect(self._on_run_clicked)
        run_btn_font = QFont("Microsoft YaHei UI", 14)
        run_btn_font.setBold(True)
        self._run_btn.setFont(run_btn_font)

        run_layout = QHBoxLayout()
        run_layout.addStretch()
        run_layout.addWidget(self._run_btn)
        run_layout.addStretch()
        panel_layout.addLayout(run_layout)

        # 透明度效果：展开时 0→1 渐变
        self._panel_effect = QGraphicsOpacityEffect(self._panel)
        self._panel.setGraphicsEffect(self._panel_effect)
        self._panel_effect.setOpacity(0.0)

        # 初始收起
        self._panel.hide()
        self._panel.setFixedHeight(0)

    # ==================== 工具卡片 ====================

    def _build_tool_cards(self):
        """
        构建工具卡片 - 按数量自适应布局，卡片统一固定高度

        ≤3 个：单列大卡片（所有卡片放入同一个限宽容器 → 严格等宽且居中）
        4-6 个：两列大卡片
        >6 个：两列紧凑卡片
        """
        count = len(self._plugins)
        if count <= 3:
            self._tools_cols = 1
            fixed_height, icon_size = 170, 48
            name_pt, desc_pt = 16, 12
        elif count <= 6:
            self._tools_cols = 2
            fixed_height, icon_size = 124, 42
            name_pt, desc_pt = 15, 11
        else:
            self._tools_cols = 2
            fixed_height, icon_size = 88, 26
            name_pt, desc_pt = 13, 10

        # 先创建所有卡片（统一尺寸参数）
        cards = []
        for plugin in self._plugins:
            card = self._create_tool_card(
                plugin, fixed_height=fixed_height, icon_size=icon_size,
                name_pt=name_pt, desc_pt=desc_pt
            )
            self._card_widgets.append(card)
            cards.append(card)

        if self._tools_cols == 1:
            # 单列：全部卡片放入同一个限宽容器（固定宽 → 严格等宽），容器水平居中
            wrapper = QWidget()
            wrapper.setFixedWidth(600)
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.setContentsMargins(0, 0, 0, 0)
            wrapper_layout.setSpacing(12)
            for card in cards:
                wrapper_layout.addWidget(card)
            center_row = QHBoxLayout()
            center_row.setContentsMargins(0, 0, 0, 0)
            center_row.addStretch()
            center_row.addWidget(wrapper)
            center_row.addStretch()
            self._tools_vbox.addLayout(center_row)
            self._tools_vbox.addStretch()
        else:
            # 多列：网格布局，列均分
            grid = QGridLayout()
            grid.setSpacing(12)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 1)
            for i, card in enumerate(cards):
                grid.addWidget(card, i // 2, i % 2)
            total_rows = (count + 1) // 2
            grid.setRowStretch(total_rows, 1)  # 底部弹性行：内容垂直居中
            self._tools_vbox.addLayout(grid)

    def _create_tool_card(self, plugin, fixed_height, icon_size, name_pt, desc_pt) -> QFrame:
        """创建单个工具卡片 - 固定高度，保证同一页面高低一致"""
        card = QFrame()
        card.setObjectName("toolCard")
        card.setFrameShape(QFrame.NoFrame)
        card.setCursor(Qt.PointingHandCursor)
        card.setProperty("selected", "false")
        card.setFixedHeight(fixed_height)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(18, 12, 18, 12)
        card_layout.setSpacing(14)

        # 图标 - 统一大小
        icon_label = QLabel()
        icon_pixmap = create_plugin_icon(plugin.icon, icon_size)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedSize(icon_size + 12, icon_size + 12)
        icon_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(icon_label)

        # 信息区
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)

        name_label = QLabel(plugin.name)
        name_font = QFont("Microsoft YaHei UI", name_pt)
        name_font.setBold(True)
        name_label.setFont(name_font)

        desc_label = QLabel(plugin.description)
        desc_font = QFont("Microsoft YaHei UI", desc_pt)
        desc_label.setFont(desc_font)
        desc_label.setWordWrap(True)

        # 信息区 - 文字垂直居中，避免单列大卡片"头重脚轻"
        info_layout.addStretch()
        info_layout.addWidget(name_label)
        info_layout.addWidget(desc_label)
        info_layout.addStretch()
        card_layout.addLayout(info_layout, 1)

        # 选中箭头 - 初始透明，选中时显示
        arrow_label = QLabel("›")
        arrow_font = QFont("Microsoft YaHei UI", 22)
        arrow_label.setFont(arrow_font)
        arrow_label.setFixedSize(22, 38)
        arrow_label.setAlignment(Qt.AlignCenter)
        self._arrow_labels.append(arrow_label)
        self._set_arrow_idle_style(arrow_label)
        card_layout.addWidget(arrow_label)

        # 点击选择
        card.mousePressEvent = lambda e, p=plugin, c=card, a=arrow_label: self._select_plugin(p, c, a)

        # 轻微上浮悬停：hover 时瞬时启用阴影，离开时关闭。
        # 注意：不能用逐帧动画驱动阴影——每帧重绘整张卡片（含文字/图标光栅化）会导致内容"抽动"
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(0)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 0, 0, 0))
        card.setGraphicsEffect(shadow)

        def _hover_enter(event, card=card):
            shadow.setBlurRadius(12)
            shadow.setOffset(0, 3)
            shadow.setColor(QColor(0, 0, 0, 100))
            QFrame.enterEvent(card, event)

        def _hover_leave(event, card=card):
            shadow.setBlurRadius(0)
            shadow.setOffset(0, 0)
            shadow.setColor(QColor(0, 0, 0, 0))
            QFrame.leaveEvent(card, event)

        card.enterEvent = _hover_enter
        card.leaveEvent = _hover_leave

        return card

    # ==================== 浮动层动画 ====================

    def _stop_panel_anim(self):
        if self._panel_anim and self._panel_anim.state() == QVariantAnimation.Running:
            self._panel_anim.stop()
        self._panel_anim = None

    def _apply_panel_anim(self, val):
        """动画驱动：面板几何 + 透明度"""
        h = int(val)
        self._panel.setFixedHeight(h)
        self._panel.setGeometry(0, self.height() - h, self.width(), h)
        self._panel_effect.setOpacity(min(1.0, h / max(1, self._panel_target)))
        self._panel.raise_()

    def _expand_panel(self):
        """从底部平滑升起操作面板（bottom sheet），不影响卡片区布局"""
        self._stop_panel_anim()
        self._panel.show()
        self._panel.layout().activate()
        target = self._panel.sizeHint().height()
        if target <= 0:
            target = 320
        # 限高：最多占页面高度 88%，超高内容在面板内部滚动查看
        max_h = max(320, int(self.height() * 0.88))
        if target > max_h:
            target = max_h
        # 优先使用记忆的拖拽高度（用户在之前会话中手动调整过的尺寸）
        pref = _load_panel_height()
        if pref > 0:
            target = max(220, min(pref, max_h))
        self._panel_target = target

        self._panel_anim = QVariantAnimation(self)
        self._panel_anim.setDuration(300)
        self._panel_anim.setStartValue(0)
        self._panel_anim.setEndValue(target)
        self._panel_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._panel_anim.valueChanged.connect(self._apply_panel_anim)
        self._panel_anim.start()

        # 切换入口按钮
        self._expand_btn.setVisible(False)
        self._place_overlays()
        self.panel_expanded.emit()

    def _collapse_panel(self):
        """平滑收拢操作面板"""
        if not self._panel.isVisible() or self._panel.height() <= 0:
            return
        self._stop_panel_anim()

        self._panel_anim = QVariantAnimation(self)
        self._panel_anim.setDuration(240)
        self._panel_anim.setStartValue(self._panel.height())
        self._panel_anim.setEndValue(0)
        self._panel_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._panel_anim.valueChanged.connect(self._apply_panel_anim)
        self._panel_anim.finished.connect(self._on_panel_collapsed)
        self._panel_anim.start()

    def _on_panel_collapsed(self):
        """收拢完成：隐藏面板，恢复底部入口"""
        self._panel.hide()
        self._panel.setFixedHeight(0)
        self._expand_btn.setVisible(True)
        self.panel_collapsed.emit()

    def _place_overlays(self):
        """放置浮动层：面板贴底部；窗口变化时自动收缩过高的面板"""
        if self._panel.isVisible():
            h = self._panel.height()
            max_h = max(220, int(self.height() * 0.88))
            if h > max_h:
                h = max_h
                self._panel.setFixedHeight(h)
            self._panel.setGeometry(0, self.height() - h, self.width(), h)
            self._panel.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_overlays()

    def _on_expand_btn_clicked(self):
        """点击底部「展开操作区」入口"""
        self._expand_panel()

    # ==================== 面板高度拖拽 ====================

    def _handle_drag_press(self, event):
        """拖拽开始：记录起始鼠标位置与面板高度"""
        if event.button() == Qt.LeftButton:
            self._drag_start_y = event.globalPosition().y()
            self._drag_start_h = self._panel.height()
            self._dragging = True
            event.accept()

    def _handle_drag_move(self, event):
        """拖拽中：实时调整面板高度（向上拉变高，向下推变矮）"""
        if getattr(self, "_dragging", False):
            new_h = int(self._drag_start_h + (self._drag_start_y - event.globalPosition().y()))
            max_h = max(220, int(self.height() * 0.88))
            new_h = max(220, min(new_h, max_h))
            self._panel.setFixedHeight(new_h)
            self._panel.setGeometry(0, self.height() - new_h, self.width(), new_h)
            self._panel.raise_()
            self._panel_effect.setOpacity(1.0)
            event.accept()

    def _handle_drag_release(self, event):
        """拖拽结束：记忆面板高度，下次展开恢复"""
        if getattr(self, "_dragging", False):
            self._dragging = False
            _save_panel_height(self._panel.height())
            event.accept()

    # ==================== 交互 ====================

    def _set_arrow_idle_style(self, arrow: QLabel):
        is_dark = self.palette().window().color().lightness() < 128
        if is_dark:
            arrow.setStyleSheet("color: rgba(255,255,255,0.12); background: transparent;")
        else:
            arrow.setStyleSheet("color: rgba(0,0,0,0.10); background: transparent;")

    def _select_plugin(self, plugin: BasePlugin, card=None, arrow=None):
        """选择插件 - 加载参数并展开操作面板；重复点击同一卡片则收起面板"""
        # 重复点击已选中的卡片：收起面板并取消选中
        if plugin is self._current_plugin and self._panel.isVisible():
            self._collapse_panel()
            for c in self._card_widgets:
                c.setProperty("selected", "false")
                c.style().unpolish(c)
                c.style().polish(c)
            for a in self._arrow_labels:
                self._set_arrow_idle_style(a)
            self._current_plugin = None
            self._title_label.setText("选择一个工具开始")
            return

        self._current_plugin = plugin

        # 取消之前选中
        for c in self._card_widgets:
            c.setProperty("selected", "false")
            c.style().unpolish(c)
            c.style().polish(c)
        for a in self._arrow_labels:
            self._set_arrow_idle_style(a)

        # 高亮当前
        if card:
            card.setProperty("selected", "true")
            card.style().unpolish(card)
            card.style().polish(card)
        if arrow:
            accent_color = self._get_accent_color()
            arrow.setStyleSheet(f"color: {accent_color}; background: transparent; font-size: 22px; font-weight: bold;")

        self._title_label.setText(plugin.name)
        self._panel_title.setText(plugin.name)
        self._options_panel.setVisible(True)
        self._options_panel.load_plugin_options(plugin)
        self._options_panel.set_files(self._files)

        # 根据插件是否需要文件，切换拖放区 / 无需文件提示
        need_file = plugin.requires_files
        self._drop_area.setVisible(need_file)
        self._no_file_label.setVisible(not need_file)
        self._options_panel.set_need_files(need_file)

        self._expand_panel()
        self._update_run_btn()

    def _update_run_btn(self):
        """根据插件是否需要文件、文件是否就绪，更新运行按钮状态"""
        if not self._current_plugin:
            self._run_btn.setDisabled(True)
            return
        need_file = self._current_plugin.requires_files
        ready = (not need_file) or len(self._files) > 0
        self._run_btn.setEnabled(ready)

    def _get_accent_color(self) -> str:
        """获取当前主题的强调色"""
        from ..styles.theme import get_theme_colors, load_theme_config
        config = load_theme_config()
        colors = get_theme_colors(config.get("current_theme", "dark"), config.get("custom_accent"))
        return colors.get("accent", "#82B1FF")

    def _setup_connections(self):
        """信号连接"""
        self._drop_area.files_dropped.connect(self._on_files_dropped)
        self._drop_area.files_selected.connect(self._on_files_dropped)
        self._progress_panel.cancelled.connect(self._on_cancel)
        self._progress_panel.retry_requested.connect(self._on_retry)
        self._progress_panel.open_dir_requested.connect(self._open_output_dir)

    def _open_output_dir(self, path: str):
        """打开输出目录"""
        try:
            if path and os.path.isdir(path):
                os.startfile(path)  # type: ignore
        except Exception as e:
            self.status_changed.emit(f"无法打开目录: {e}")

    # ==================== 页面级拖放（小白友好：拖到任意位置自动匹配工具） ====================

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and any(
            u.isLocalFile() for u in event.mimeData().urls()
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = list_files_from_dropped(event.mimeData())
        if not files:
            return
        first_ext = files[0].rsplit('.', 1)[-1].lower() if '.' in files[0] else ''
        # 当前选中的工具能处理 → 直接填充
        if self._current_plugin and self._plugin_supports(self._current_plugin, first_ext):
            self._on_files_dropped(files)
            return
        # 自动选中第一个能处理该文件类型的工具并展开
        for plugin in self._plugins:
            if self._plugin_supports(plugin, first_ext):
                self._select_plugin(plugin, None, None)
                self._on_files_dropped(files)
                return
        # 该分类下没有匹配的工具
        self.status_changed.emit(f"当前分类没有能处理 .{first_ext} 文件的工具，请到其他分类试试")

    @staticmethod
    def _plugin_supports(plugin: BasePlugin, ext: str) -> bool:
        """插件是否支持指定扩展名（空格式 / 通配符视为全支持）"""
        fmts = plugin.supported_input_formats or []
        if not fmts or "*" in fmts:
            return True
        return ext in fmts

    def _on_files_dropped(self, files: List[str]):
        """文件拖放"""
        self._files.extend(files)
        self._files = list(dict.fromkeys(self._files))
        self._options_panel.set_files(self._files)
        self._update_run_btn()

    def _on_run_clicked(self):
        """运行"""
        if not self._current_plugin:
            return
        if self._current_plugin.requires_files and not self._files:
            return
        options = self._options_panel.get_options()
        input_data = PluginInput(file_paths=self._files, options=options)
        self._progress_panel.setVisible(True)
        self._progress_panel.start_tasks(max(1, len(self._files)))
        self._run_btn.setDisabled(True)
        self._worker = TaskWorker(self._current_plugin, input_data)
        self._worker.progress.connect(self._progress_panel.update_progress)
        self._worker.file_completed.connect(self._progress_panel.add_file_result)
        self._worker.completed.connect(self._on_worker_completed)
        self._worker.start()

    def _on_worker_completed(self, success: bool, message: str, error: str, output_paths: list):
        """处理完成 - 记录输出目录、显示结果，几秒后自动回到初始界面"""
        # 计算输出目录（优先取第一个输出文件所在目录）
        out_dir = ""
        if output_paths and output_paths[0]:
            out_dir = os.path.dirname(str(output_paths[0]))
        if not out_dir:
            options = self._options_panel.get_options()
            out_dir = options.get("output_dir", "") or ""
        self._progress_panel.set_output_dir(out_dir)
        self._progress_panel.finish_all(success, message, error)
        self._run_btn.setEnabled(False)  # 先禁用，重置后再根据文件启用
        self._worker = None

        # 延迟几秒后自动收尾，回到初始界面
        delay_ms = 3000 if success else 6000  # 失败多停留一点时间
        QTimer.singleShot(delay_ms, self._reset_to_initial_state)

    def _reset_to_initial_state(self):
        """重置为初始状态：清空文件、收拢面板、取消选中、还原标题"""
        # 1. 清空已选文件
        self._files.clear()
        self._options_panel.set_files([])

        # 2. 隐藏进度面板并重置
        self._progress_panel.setVisible(False)
        self._progress_panel._table.hide()
        self._progress_panel._status_label.setText("就绪")
        self._progress_panel._progress_bar.setValue(0)

        # 3. 取消所有工具卡片的选中状态，还原箭头
        for c in self._card_widgets:
            c.setProperty("selected", "false")
            c.style().unpolish(c)
            c.style().polish(c)
        for a in self._arrow_labels:
            self._set_arrow_idle_style(a)

        # 4. 还原标题和当前插件
        self._current_plugin = None
        self._title_label.setText("选择一个工具开始")
        self._panel_title.setText("操作设置")

        # 5. 隐藏参数面板并禁用运行按钮
        self._options_panel.setVisible(False)
        self._run_btn.setDisabled(True)

        # 6. 收拢操作面板，卡片区占满
        self._collapse_panel()

    def _on_cancel(self):
        """取消"""
        if self._worker:
            self._worker.cancel()
            self._progress_panel._status_label.setText("已取消")

    def _on_retry(self):
        """重试"""
        if self._current_plugin and (not self._current_plugin.requires_files or self._files):
            self._on_run_clicked()
