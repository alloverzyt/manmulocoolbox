# -*- coding: utf-8 -*-
"""
主窗口模块

包含主窗口、侧边栏导航、依赖管理页面。
所有UI使用黑色简笔画图标，主题可切换。
"""

import sys
import os
import json
import webbrowser
from typing import Optional

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QStackedWidget, QPushButton,
    QStatusBar, QMessageBox, QSizePolicy, QFrame, QProgressBar,
    QScrollArea, QTabWidget, QDialog
)

from ..core.plugin_manager import PluginManager
from ..core.events import EventBus
from ..core.dependency_manager import (
    check_all_dependencies, CORE_DEPENDENCIES, OPTIONAL_DEPENDENCIES,
    EXTERNAL_TOOLS, install_python_package, install_essential_dependencies
)
from ..utils.tool_downloader import (
    ToolDownloader, get_all_tool_status, get_download_info, DOWNLOAD_SOURCES
)
from .pages.tool_page import ToolPage
from .widgets.icon_drawer import get_icon_pixmap, set_icon_color, ICON_MAP
from .styles.theme import (
    load_theme_config, save_theme_config,
    generate_stylesheet, get_theme_colors,
    PRESET_COLORS
)
from .dialogs.theme_settings import ThemeSettingsDialog


class InstallWorker(QThread):
    """安装工作线程 - pip_name=None 时安装所有缺失核心依赖，否则安装指定包"""
    progress = Signal(int, str)
    finished_ok = Signal(bool, str)
    error = Signal(str)

    def __init__(self, pip_name=None, parent=None):
        super().__init__(parent)
        self._pip_name = pip_name

    def run(self):
        try:
            if self._pip_name:
                # 安装单个可选/核心包
                self.progress.emit(10, "正在安装依赖...")
                ok, msg = install_python_package(self._pip_name)
                if ok:
                    self.progress.emit(100, "安装完成")
                    self.finished_ok.emit(True, "安装成功")
                else:
                    self.finished_ok.emit(False, f"安装失败: {msg}")
            else:
                # 一键安装所有缺失核心依赖
                self.progress.emit(10, "正在检测依赖...")
                ok = install_essential_dependencies()
                if ok:
                    self.progress.emit(100, "安装完成")
                    self.finished_ok.emit(True, "核心依赖安装完成")
                else:
                    self.finished_ok.emit(False, "部分依赖安装失败，请手动安装")
        except Exception as e:
            self.error.emit(str(e))


class SourceProbeWorker(QThread):
    """外部工具下载源可达性探测线程（不阻塞 UI）"""
    finished = Signal(list)

    def __init__(self, tool_key: str, parent=None):
        super().__init__(parent)
        self._tool_key = tool_key

    def run(self):
        from ..utils.tool_downloader import probe_sources
        try:
            results = probe_sources(self._tool_key)
        except Exception as e:
            results = [{"name": "未知", "url": "", "ok": False, "error": str(e)[:100]}]
        self.finished.emit(results)


class SourceSelectDialog(QDialog):
    """下载源选择对话框：展示各源可达性检测结果，让用户选择用哪个源下载"""

    def __init__(self, tool_name: str, results: list, parent=None):
        super().__init__(parent)
        self._selected = None
        self.setWindowTitle(f"选择 {tool_name} 下载源")
        self.setMinimumSize(520, 320)
        self.resize(540, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        tip = QLabel("已检测各下载源的可达性，请选择一个源开始下载：")
        tip.setWordWrap(True)
        tip.setStyleSheet("font-size: 13px; background: transparent;")
        layout.addWidget(tip)

        self._list = QListWidget()
        layout.addWidget(self._list, 1)

        has_ok = False
        for r in results:
            item = QListWidgetItem()
            if r.get("ok"):
                has_ok = True
                item.setText(f"[可用] {r['name']}")
                item.setForeground(QColor("#4CAF50"))
            else:
                item.setText(f"[不可用] {r['name']}（{r.get('error', '无法连接')}）")
                item.setForeground(QColor("#999999"))
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            item.setData(Qt.UserRole, r)
            self._list.addItem(item)

        if not has_ok:
            warn = QLabel("所有下载源当前都不可用，请检查网络后重试。")
            warn.setStyleSheet("color: #EF9A9A; background: transparent;")
            layout.addWidget(warn)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._ok_btn = QPushButton("开始下载")
        self._ok_btn.setObjectName("primaryBtn")
        self._ok_btn.setMinimumHeight(36)
        self._ok_btn.setMinimumWidth(100)
        self._ok_btn.setEnabled(has_ok)
        self._ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("取消")
        cancel_btn.setMinimumHeight(36)
        cancel_btn.setMinimumWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        # 默认选中第一个可用的源
        for i in range(self._list.count()):
            if self._list.item(i).flags() & Qt.ItemIsEnabled:
                self._list.setCurrentRow(i)
                break

    def _on_ok(self):
        item = self._list.currentItem()
        if item and (item.flags() & Qt.ItemIsEnabled):
            self._selected = item.data(Qt.UserRole)
            self.accept()
        else:
            QMessageBox.warning(self, "提示", "请先选择一个可用的下载源")

    def selected_source(self) -> Optional[dict]:
        return self._selected


class DependencyPage(QWidget):
    """依赖管理页面 - 卡片式布局"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._downloader = None
        self._current_theme = "dark"
        self._setup_ui()

    def set_theme(self, theme_name: str):
        self._current_theme = theme_name

    def _get_current_theme(self) -> str:
        return self._current_theme

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(12)

        header = QLabel("依赖管理")
        header.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        layout.addWidget(header)

        subtitle = QLabel("管理运行环境所需的依赖项。核心依赖必须安装，可选依赖和外部工具按需安装。")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("background: transparent;")
        layout.addWidget(subtitle)

        # 概览统计卡片
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(10)
        self._summary_labels = {}
        for key, label_text in [("core", "核心依赖"), ("optional", "可选依赖"), ("external", "外部工具")]:
            card = QFrame()
            card.setObjectName("toolCard")
            card.setMinimumHeight(68)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 8, 14, 8)
            card_layout.setSpacing(2)
            lbl_title = QLabel(label_text)
            lbl_title.setStyleSheet("font-size: 12px; font-weight: bold; background: transparent;")
            lbl_count = QLabel("检测中...")
            lbl_count.setStyleSheet("font-size: 22px; font-weight: bold; background: transparent;")
            lbl_count.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(lbl_title)
            card_layout.addWidget(lbl_count)
            self._summary_labels[key] = lbl_count
            summary_layout.addWidget(card, 1)
        layout.addLayout(summary_layout)

        # ===== Tab 分组：核心依赖 / 可选依赖 / 外部工具 =====
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        # ---- 核心依赖 Tab ----
        core_tab = QWidget()
        core_tab_layout = QVBoxLayout(core_tab)
        core_tab_layout.setContentsMargins(8, 12, 8, 8)
        core_tab_layout.setSpacing(8)
        self._core_scroll = QScrollArea()
        self._core_scroll.setWidgetResizable(True)
        self._core_scroll.setFrameShape(QFrame.NoFrame)
        self._core_container = QWidget()
        self._core_list_layout = QVBoxLayout(self._core_container)
        self._core_list_layout.setSpacing(8)
        self._core_list_layout.setContentsMargins(0, 0, 4, 0)
        self._core_scroll.setWidget(self._core_container)
        core_tab_layout.addWidget(self._core_scroll, 1)

        core_btn_row = QHBoxLayout()
        core_btn_row.setSpacing(8)
        self._install_core_btn = QPushButton("一键安装缺失的核心依赖")
        self._install_core_btn.setObjectName("primaryBtn")
        self._install_core_btn.setMinimumHeight(40)
        self._install_core_btn.clicked.connect(self._install_core)
        core_btn_row.addWidget(self._install_core_btn)
        core_btn_row.addStretch()
        core_tab_layout.addLayout(core_btn_row)
        self._tabs.addTab(core_tab, "核心依赖")

        # ---- 可选依赖 Tab ----
        opt_tab = QWidget()
        opt_tab_layout = QVBoxLayout(opt_tab)
        opt_tab_layout.setContentsMargins(8, 12, 8, 8)
        opt_tab_layout.setSpacing(8)
        self._opt_scroll = QScrollArea()
        self._opt_scroll.setWidgetResizable(True)
        self._opt_scroll.setFrameShape(QFrame.NoFrame)
        self._opt_container = QWidget()
        self._opt_list_layout = QVBoxLayout(self._opt_container)
        self._opt_list_layout.setSpacing(8)
        self._opt_list_layout.setContentsMargins(0, 0, 4, 0)
        self._opt_scroll.setWidget(self._opt_container)
        opt_tab_layout.addWidget(self._opt_scroll, 1)
        self._tabs.addTab(opt_tab, "可选依赖")

        # ---- 外部工具 Tab ----
        ext_tab = QWidget()
        ext_tab_layout = QVBoxLayout(ext_tab)
        ext_tab_layout.setContentsMargins(8, 12, 8, 8)
        ext_tab_layout.setSpacing(8)
        self._ext_scroll = QScrollArea()
        self._ext_scroll.setWidgetResizable(True)
        self._ext_scroll.setFrameShape(QFrame.NoFrame)
        self._ext_container = QWidget()
        self._ext_list_layout = QVBoxLayout(self._ext_container)
        self._ext_list_layout.setSpacing(8)
        self._ext_list_layout.setContentsMargins(0, 0, 4, 0)
        self._ext_scroll.setWidget(self._ext_container)
        ext_tab_layout.addWidget(self._ext_scroll, 1)
        self._tabs.addTab(ext_tab, "外部工具")

        layout.addWidget(self._tabs, 1)

        # 底部：进度 + 状态
        # 进度条高度 16px，隐藏内部百分比文本（8px 高度会导致文字上下被遮挡），
        # 进度与速度信息显示在下方独立状态标签中，避免与整体 UI 风格冲突
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setFixedHeight(16)
        self._progress.setTextVisible(False)
        layout.addWidget(self._progress)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _create_dep_card(self, name, installed, description, is_dark, pip_name=None):
        card = QFrame()
        card.setObjectName("toolCard")
        card.setMinimumHeight(70)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(16, 10, 16, 10)
        card_layout.setSpacing(12)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        name_label = QLabel(name)
        nf = QFont("Microsoft YaHei UI", 13)
        nf.setBold(True)
        name_label.setFont(nf)
        name_label.setStyleSheet("background: transparent;")
        desc_label = QLabel(description)
        df = QFont("Microsoft YaHei UI", 10)
        desc_label.setFont(df)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("background: transparent;")
        info_layout.addWidget(name_label)
        info_layout.addWidget(desc_label)
        card_layout.addLayout(info_layout, 1)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(4)
        state_text = "已安装" if installed else "未安装"
        state_label = QLabel(state_text)
        sf = QFont("Microsoft YaHei UI", 12)
        sf.setBold(True)
        state_label.setFont(sf)
        state_label.setAlignment(Qt.AlignCenter)
        if installed:
            state_label.setStyleSheet(f"color: {'#A5D6A7' if is_dark else '#4CAF50'}; background: transparent; font-weight: bold; font-size: 13px;")
        else:
            state_label.setStyleSheet(f"color: {'#EF9A9A' if is_dark else '#E53935'}; background: transparent; font-weight: bold; font-size: 13px;")
        right_layout.addWidget(state_label)

        # 未安装且提供 pip_name 时，给出「安装」按钮（可选依赖使用）
        if not installed and pip_name:
            install_btn = QPushButton("安装")
            install_btn.setObjectName("primaryBtn")
            install_btn.setMinimumHeight(32)
            install_btn.setMinimumWidth(72)
            btn_font = QFont("Microsoft YaHei UI", 10)
            install_btn.setFont(btn_font)
            install_btn.clicked.connect(lambda checked, p=pip_name: self._install_optional(p))
            right_layout.addWidget(install_btn)

        card_layout.addLayout(right_layout)
        return card

    def _create_tool_card(self, name, installed, size_mb, is_dark, tool_key):
        card = QFrame()
        card.setObjectName("toolCard")
        card.setMinimumHeight(100)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(14)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        name_label = QLabel(name)
        nf = QFont("Microsoft YaHei UI", 13)
        nf.setBold(True)
        name_label.setFont(nf)
        name_label.setStyleSheet("background: transparent;")
        size_label = QLabel(f"大小: {size_mb}MB")
        df = QFont("Microsoft YaHei UI", 10)
        size_label.setFont(df)
        size_label.setStyleSheet("background: transparent;")
        info_layout.addWidget(name_label)
        info_layout.addWidget(size_label)
        info_layout.addStretch()
        card_layout.addLayout(info_layout, 1)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(6)
        state_text = "已安装" if installed else "未安装"
        state_label = QLabel(state_text)
        sf = QFont("Microsoft YaHei UI", 12)
        sf.setBold(True)
        state_label.setFont(sf)
        state_label.setAlignment(Qt.AlignCenter)
        if installed:
            state_label.setStyleSheet(f"color: {'#A5D6A7' if is_dark else '#4CAF50'}; background: transparent; font-weight: bold; font-size: 13px;")
        else:
            state_label.setStyleSheet(f"color: {'#EF9A9A' if is_dark else '#E53935'}; background: transparent; font-weight: bold; font-size: 13px;")
        right_layout.addWidget(state_label)

        if not installed:
            # 按钮改为水平排列，避免遮挡
            btn_row = QHBoxLayout()
            btn_row.setSpacing(8)
            dl_btn = QPushButton("下载")
            dl_btn.setObjectName("primaryBtn")
            dl_btn.setMinimumHeight(32)
            dl_btn.setMinimumWidth(64)
            dl_btn_font = QFont("Microsoft YaHei UI", 10)
            dl_btn.setFont(dl_btn_font)
            dl_btn.clicked.connect(lambda checked, k=tool_key: self._download_tool(k))
            btn_row.addWidget(dl_btn)

            web_btn = QPushButton("官网")
            web_btn.setMinimumHeight(32)
            web_btn.setMinimumWidth(64)
            web_btn.setFont(dl_btn_font)
            web_btn.clicked.connect(
                lambda checked, k=tool_key: webbrowser.open(
                    next((t.get("download_url", "") for t in EXTERNAL_TOOLS if t["key"] == k), "")
                )
            )
            btn_row.addWidget(web_btn)
            right_layout.addLayout(btn_row)

        card_layout.addLayout(right_layout)
        return card

    def refresh(self):
        """刷新依赖状态 - 重建核心/可选/外部三个Tab的卡片列表"""
        status = check_all_dependencies()
        is_dark = self._get_current_theme() == "dark"

        # 按名称查安装状态
        py_status = {d["name"]: d for d in status["python"]}

        core_count = len(CORE_DEPENDENCIES)
        core_installed = sum(1 for d in CORE_DEPENDENCIES if py_status.get(d["name"], {}).get("installed"))
        opt_count = len(OPTIONAL_DEPENDENCIES)
        opt_installed = sum(1 for d in OPTIONAL_DEPENDENCIES if py_status.get(d["name"], {}).get("installed"))
        ext_count = len(EXTERNAL_TOOLS)
        ext_installed = sum(1 for t in status["external"] if t["installed"])

        self._summary_labels["core"].setText(f"{core_installed}/{core_count}")
        self._summary_labels["optional"].setText(f"{opt_installed}/{opt_count}")
        self._summary_labels["external"].setText(f"{ext_installed}/{ext_count}")

        # 重建核心依赖卡片（未安装时不显示安装按钮，统一走一键安装）
        self._clear_layout(self._core_list_layout)
        for dep in CORE_DEPENDENCIES:
            info = py_status.get(dep["name"], {})
            card = self._create_dep_card(dep["name"], info.get("installed", False), dep["description"], is_dark)
            self._core_list_layout.addWidget(card)
        self._core_list_layout.addStretch()

        # 重建可选依赖卡片（未安装时显示单个安装按钮）
        self._clear_layout(self._opt_list_layout)
        for dep in OPTIONAL_DEPENDENCIES:
            info = py_status.get(dep["name"], {})
            card = self._create_dep_card(
                dep["name"], info.get("installed", False), dep["description"],
                is_dark, pip_name=dep["pip_name"] if not info.get("installed") else None
            )
            self._opt_list_layout.addWidget(card)
        self._opt_list_layout.addStretch()

        # 重建外部工具卡片
        self._clear_layout(self._ext_list_layout)
        ext_status = get_all_tool_status()
        for tool in EXTERNAL_TOOLS:
            info = ext_status.get(tool["key"], {})
            card = self._create_tool_card(
                tool["name"], info.get("installed", False),
                info.get("size_mb", 0), is_dark, tool["key"]
            )
            self._ext_list_layout.addWidget(card)
        self._ext_list_layout.addStretch()

        self._install_core_btn.setEnabled(not status["all_essential_ok"])

    def _install_optional(self, pip_name: str):
        """安装单个可选依赖"""
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._status_label.setText("正在安装依赖...")
        self._install_worker = InstallWorker(pip_name=pip_name)
        self._install_worker.progress.connect(self._on_install_progress)
        self._install_worker.finished_ok.connect(self._on_install_done)
        self._install_worker.error.connect(self._on_install_error)
        self._install_worker.start()

    def _install_core(self):
        """一键安装核心依赖"""
        self._install_core_btn.setDisabled(True)
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._status_label.setText("正在安装核心依赖...")

        self._install_worker = InstallWorker()
        self._install_worker.progress.connect(self._on_install_progress)
        self._install_worker.finished_ok.connect(self._on_install_done)
        self._install_worker.error.connect(self._on_install_error)
        self._install_worker.start()

    def _on_install_progress(self, value, msg):
        self._progress.setValue(value)
        self._status_label.setText(msg)

    def _on_install_done(self, success, msg):
        self._progress.setVisible(False)
        self._install_core_btn.setEnabled(True)
        self._status_label.setText(msg)
        self.refresh()

    def _on_install_error(self, err):
        self._progress.setVisible(False)
        self._install_core_btn.setEnabled(True)
        self._status_label.setText(f"安装出错: {err}")
        QMessageBox.critical(self, "安装失败", err)

    def _download_tool(self, tool_key: str):
        """下载外部工具：先并发探测各下载源可达性，再让用户选择用哪个源下载"""
        tool_info = next((t for t in EXTERNAL_TOOLS if t["key"] == tool_key), None)
        if not tool_info:
            return
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._status_label.setText(f"正在检测 {tool_info['name']} 的下载源可用性...")

        self._probe_worker = SourceProbeWorker(tool_key)
        self._probe_worker.finished.connect(lambda results: self._on_sources_probed(tool_key, results))
        self._probe_worker.start()

    def _on_sources_probed(self, tool_key: str, results: list):
        """探测完成：弹出源选择对话框，用户选定后开始下载"""
        self._progress.setVisible(False)
        tool_name = next((t["name"] for t in EXTERNAL_TOOLS if t["key"] == tool_key), tool_key)

        if not results:
            QMessageBox.critical(self, "下载失败", f"未找到 {tool_name} 的下载源配置")
            return

        dlg = SourceSelectDialog(tool_name, results, parent=self)
        if dlg.exec() != QDialog.Accepted:
            self._status_label.setText("已取消下载")
            return

        selected = dlg.selected_source()
        if not selected:
            return

        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._status_label.setText(f"正在从 {selected['name']} 下载...")

        self._downloader = ToolDownloader(tool_key, selected_sources=[selected])
        self._downloader.progress.connect(self._on_download_progress)
        self._downloader.finished_ok.connect(self._on_download_ok)
        self._downloader.finished_error.connect(self._on_download_error)
        self._downloader.start()

    def _on_download_progress(self, value, msg):
        self._progress.setValue(value)
        self._status_label.setText(msg)

    def _on_download_ok(self, tool_key, path):
        self._progress.setVisible(False)
        self._status_label.setText(f"下载完成: {path}")
        self.refresh()

    def _on_download_error(self, error_msg):
        self._progress.setVisible(False)
        self._status_label.setText(f"下载失败: {error_msg}")
        QMessageBox.critical(self, "下载失败", error_msg)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("满木 - 本地工具箱")
        self.setMinimumSize(1100, 700)
        self.resize(1200, 750)

        self._plugin_manager = PluginManager()
        self._event_bus = EventBus()
        self._pages = {}
        self._theme_config = load_theme_config()

        self._setup_ui()
        self._apply_theme()
        self._set_window_icon()
        self._load_plugins()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== 侧边栏 =====
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # 标题区域
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(16, 14, 16, 14)
        title_layout.setSpacing(10)

        self._logo_label = QLabel()
        self._load_app_logo(self._logo_label)
        title_layout.addWidget(self._logo_label)

        title = QLabel("满木工具箱")
        title.setObjectName("sidebarTitle")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_layout.addWidget(title, 1)
        sidebar_layout.addLayout(title_layout)

        # 导航列表
        self._nav_list = QListWidget()
        self._nav_list.setObjectName("navList")
        self._nav_list.currentRowChanged.connect(self._on_nav_changed)
        sidebar_layout.addWidget(self._nav_list, 1)

        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(14, 8, 14, 14)
        bottom_layout.setSpacing(8)

        self._theme_btn = QPushButton()
        self._theme_btn.setFixedSize(42, 42)
        self._theme_btn.setToolTip("切换主题")
        self._theme_btn.clicked.connect(self._toggle_theme)
        self._update_theme_button()
        bottom_layout.addWidget(self._theme_btn)

        self._palette_btn = QPushButton()
        self._palette_btn.setFixedSize(42, 42)
        self._palette_btn.setToolTip("主题设置")
        self._palette_btn.clicked.connect(self._open_theme_settings)
        self._update_palette_button()
        bottom_layout.addWidget(self._palette_btn)

        self._about_btn = QPushButton()
        self._about_btn.setFixedSize(42, 42)
        self._about_btn.setToolTip("关于")
        self._about_btn.clicked.connect(self._show_about)
        self._update_about_button()
        bottom_layout.addWidget(self._about_btn)
        bottom_layout.addStretch()
        sidebar_layout.addLayout(bottom_layout)

        main_layout.addWidget(sidebar)

        # ===== 内容区 =====
        self._stack = QStackedWidget()
        main_layout.addWidget(self._stack, 1)

        # 依赖管理页
        self._dep_page = DependencyPage()
        self._dep_index = self._stack.addWidget(self._dep_page)

        # 状态栏
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("就绪")

    def _load_plugins(self):
        """加载插件并构建导航"""
        self._plugin_manager.discover_plugins()

        category_names = {
            "pdf": ("PDF处理", "pdf"),
            "image": ("图片处理", "image"),
            "document": ("文档转换", "document"),
            "file": ("文件工具", "file"),
            "qrcode": ("二维码", "qrcode"),
            "media": ("媒体工具", "media"),
            "utility": ("实用工具", "tools"),
        }

        categories = self._plugin_manager.get_categories()
        for cat in categories:
            plugins = self._plugin_manager.get_plugins_by_category(cat)
            if not plugins:
                continue
            display_name, icon_key = category_names.get(cat, (cat, "tools"))
            page = ToolPage(plugins)
            # 页面消息（如拖放匹配提示）显示到状态栏
            page.status_changed.connect(
                lambda msg, sb=self._status_bar: sb.showMessage(msg, 5000)
            )
            idx = self._stack.addWidget(page)
            self._pages[cat] = idx

            icon_pixmap = get_icon_pixmap(icon_key, 20)
            item = QListWidgetItem(icon_pixmap, display_name)
            item.setTextAlignment(Qt.AlignVCenter)
            self._nav_list.addItem(item)

        # 依赖管理项
        dep_pixmap = get_icon_pixmap("download", 20)
        dep_item = QListWidgetItem(dep_pixmap, "依赖管理")
        dep_item.setTextAlignment(Qt.AlignVCenter)
        self._nav_list.addItem(dep_item)
        self._nav_list.setCurrentRow(0)

        self._dep_page.refresh()

    def _on_nav_changed(self, row: int):
        """导航切换"""
        if row < 0:
            return
        total_cats = len(self._pages)
        if row < total_cats:
            cat_keys = list(self._pages.keys())
            self._stack.setCurrentIndex(self._pages[cat_keys[row]])
        else:
            self._stack.setCurrentIndex(self._dep_index)
            self._dep_page.refresh()

    def _apply_theme(self):
        """应用主题 - 统一入口：全应用级QSS + 刷新所有缓存
        （经验322696：避免主窗口切了但子页面/弹窗仍残留旧样式）
        """
        from PySide6.QtWidgets import QApplication
        from PySide6.QtWidgets import QStyle

        theme_name = self._theme_config.get("current_theme", "dark")
        accent = self._theme_config.get("custom_accent")
        colors = get_theme_colors(theme_name, accent)

        icon_color = QColor(colors.get("icon_color", "#D0D5E0"))
        set_icon_color(icon_color)

        # 统一生成完整QSS，并设置到整个app（避免弹窗、子页面残留旧主题）
        stylesheet = generate_stylesheet(theme_name, accent)
        QApplication.instance().setStyleSheet(stylesheet)
        self.setStyleSheet(stylesheet)

        # 经验1395153：强制unpolish/polish刷新Qt的样式缓存，解决"子QWidget仍用旧背景"
        self.style().unpolish(self)
        self.style().polish(self)
        for w in self.findChildren(QWidget):
            w.style().unpolish(w)
            w.style().polish(w)
            w.update()

        self._dep_page.set_theme(theme_name)

        self._update_theme_button()
        self._update_palette_button()
        self._update_about_button()
        self._rebuild_nav_icons()
        self._update_app_icon()

    def _rebuild_nav_icons(self):
        """重建导航图标"""
        category_names = {
            "pdf": "pdf", "image": "image", "document": "document",
            "file": "file", "qrcode": "qrcode", "media": "media", "utility": "tools",
        }
        categories = self._plugin_manager.get_categories()
        cat_idx = 0
        for i, cat in enumerate(categories):
            plugins = self._plugin_manager.get_plugins_by_category(cat)
            if not plugins:
                continue
            icon_key = category_names.get(cat, "tools")
            icon_pixmap = get_icon_pixmap(icon_key, 20)
            item = self._nav_list.item(cat_idx)
            if item:
                item.setIcon(icon_pixmap)
            cat_idx += 1

        dep_item = self._nav_list.item(self._nav_list.count() - 1)
        if dep_item:
            dep_pixmap = get_icon_pixmap("download", 20)
            dep_item.setIcon(dep_pixmap)

    def _load_app_logo(self, label: QLabel):
        """加载满木logo"""
        import os
        logo_paths = []
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
            logo_paths.append(os.path.join(base, "resources", "满木.png"))
            logo_paths.append(os.path.join(getattr(sys, '_MEIPASS', base), "resources", "满木.png"))
        else:
            current_file = os.path.abspath(__file__)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            logo_paths.append(os.path.join(project_root, "resources", "满木.png"))
            logo_paths.append(os.path.join(os.getcwd(), "resources", "满木.png"))

        for path in logo_paths:
            if os.path.isfile(path):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    w, h = pixmap.width(), pixmap.height()
                    size = min(w, h)
                    x = (w - size) // 2
                    y = (h - size) // 2
                    pixmap = pixmap.copy(x, y, size, size)
                    target = 42
                    pixmap = pixmap.scaled(target, target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    rounded = QPixmap(target, target)
                    rounded.fill(Qt.transparent)
                    painter = QPainter(rounded)
                    painter.setRenderHint(QPainter.Antialiasing)
                    path_obj = QPainterPath()
                    path_obj.addRoundedRect(0, 0, target, target, 11, 11)
                    painter.setClipPath(path_obj)
                    painter.drawPixmap(0, 0, pixmap)
                    painter.end()
                    label.setPixmap(rounded)
                    label.setFixedSize(target, target)
                    return

        # 备用图标
        colors = get_theme_colors(
            self._theme_config.get("current_theme", "dark"),
            self._theme_config.get("custom_accent")
        )
        icon_pixmap = get_icon_pixmap("box", 24, QColor(255, 255, 255))
        bg_pixmap = QPixmap(42, 42)
        bg_pixmap.fill(Qt.transparent)
        painter = QPainter(bg_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor(colors["accent"])))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 42, 42, 11, 11)
        painter.drawPixmap(9, 9, icon_pixmap)
        painter.end()
        label.setPixmap(bg_pixmap)
        label.setFixedSize(42, 42)

    def _update_app_icon(self):
        """更新侧边栏logo（主题切换时）"""
        self._load_app_logo(self._logo_label)

    def _set_window_icon(self):
        """设置窗口任务栏图标"""
        import os
        logo_paths = []
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
            logo_paths.append(os.path.join(base, "resources", "满木.png"))
            logo_paths.append(os.path.join(getattr(sys, '_MEIPASS', base), "resources", "满木.png"))
        else:
            current_file = os.path.abspath(__file__)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
            logo_paths.append(os.path.join(project_root, "resources", "满木.png"))
        for path in logo_paths:
            if os.path.isfile(path):
                self.setWindowIcon(QIcon(path))
                return

    def _update_theme_button(self):
        is_dark = self._theme_config.get("current_theme", "dark") == "dark"
        icon_name = "sun" if is_dark else "moon"
        pixmap = get_icon_pixmap(icon_name, 20)
        self._theme_btn.setIcon(pixmap)
        self._theme_btn.setIconSize(pixmap.size())

    def _update_palette_button(self):
        pixmap = get_icon_pixmap("palette", 20)
        self._palette_btn.setIcon(pixmap)
        self._palette_btn.setIconSize(pixmap.size())

    def _update_about_button(self):
        pixmap = get_icon_pixmap("about", 20)
        self._about_btn.setIcon(pixmap)
        self._about_btn.setIconSize(pixmap.size())

    def _toggle_theme(self):
        current = self._theme_config.get("current_theme", "dark")
        self._theme_config["current_theme"] = "light" if current == "dark" else "dark"
        save_theme_config(self._theme_config)
        self._apply_theme()

    def _open_theme_settings(self):
        dialog = ThemeSettingsDialog(self._theme_config, self)
        if dialog.exec():
            self._theme_config = dialog.get_config()
            save_theme_config(self._theme_config)
            self._apply_theme()

    def _show_about(self):
        from .dialogs.about_dialog import AboutDialog
        dialog = AboutDialog(self._theme_config, self)
        dialog.exec()
