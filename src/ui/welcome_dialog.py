# -*- coding: utf-8 -*-
"""
欢迎对话框模块

首次启动时显示的欢迎向导，用于检测和安装依赖。
使用简洁的界面和黑色简笔画图标。
"""

import sys
import os
import json
import webbrowser
from typing import Optional

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QBrush
from PySide6.QtWidgets import (
    QApplication, QDialog, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QStackedWidget, QProgressBar, QMessageBox, QFrame
)

from .widgets.icon_drawer import get_icon_pixmap


class InstallWorker(QThread):
    """安装工作线程"""

    progress = Signal(int, str)
    finished_ok = Signal()
    finished_error = Signal(str)

    def __init__(self):
        super().__init__()
        self._cancelled = False

    def cancel(self):
        """取消安装"""
        self._cancelled = True

    def run(self):
        """执行安装"""
        try:
            # 在冻结环境中(PyInstaller打包)，所有依赖已内置，直接完成
            if getattr(sys, 'frozen', False):
                self.progress.emit(100, "所有核心依赖已就绪！")
                self.finished_ok.emit()
                return

            from src.core.dependency_manager import (
                check_all_dependencies, install_all_missing_essential,
                CORE_DEPENDENCIES
            )

            self.progress.emit(5, "检测当前环境...")
            status = check_all_dependencies()

            total_essential = sum(1 for d in CORE_DEPENDENCIES if d.get("essential"))
            installed_essential = sum(
                1 for d in status["python"]
                if d.get("essential") and d["installed"]
            )

            if status["all_essential_ok"]:
                self.progress.emit(100, "所有核心依赖已就绪！")
                self.finished_ok.emit()
                return

            self.progress.emit(20, f"发现 {total_essential - installed_essential} 个缺失的核心依赖，开始安装...")

            missing_packages = [
                d for d in status["python"]
                if d.get("essential") and not d["installed"]
            ]

            for i, dep in enumerate(missing_packages):
                if self._cancelled:
                    self.finished_error.emit("用户取消了安装")
                    return

                pct = 20 + int((i / max(len(missing_packages), 1)) * 70)
                self.progress.emit(pct, f"正在安装 {dep['name']}...")

                from src.core.dependency_manager import install_python_package
                ok, msg = install_python_package(dep["pip_name"])

                if not ok:
                    self.finished_error.emit(f"安装 {dep['name']} 失败: {msg[:200]}")
                    return

            self.progress.emit(95, "验证安装...")
            final_status = check_all_dependencies()
            if final_status["all_essential_ok"]:
                self.progress.emit(100, "所有核心依赖安装成功！")
                self.finished_ok.emit()
            else:
                self.finished_error.emit("部分依赖安装失败，请手动检查")

        except Exception as e:
            self.finished_error.emit(str(e))


class WelcomeDialog(QDialog):
    """欢迎对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("满木 - 欢迎")
        self.setMinimumSize(640, 480)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self._worker: Optional[InstallWorker] = None
        self._setup_ui()

    def _setup_ui(self):
        """设置UI组件"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # 应用图标
        icon_label = QLabel()
        icon_pixmap = self._create_app_icon()
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFixedHeight(80)
        layout.addWidget(icon_label)

        # 标题
        title = QLabel("欢迎使用满木工具箱")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 副标题
        subtitle = QLabel("本地文件处理工具箱 - 完全离线运行")
        subtitle.setStyleSheet("color: #8C8FA1; font-size: 14px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        # 内容堆栈
        self._stack = QStackedWidget()
        self._stack.addWidget(self._create_welcome_page())
        self._stack.addWidget(self._create_install_page())
        self._stack.addWidget(self._create_done_page())
        layout.addWidget(self._stack, 1)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setFixedHeight(36)
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)

        self._start_btn = QPushButton("开始使用")
        self._start_btn.setObjectName("primaryBtn")
        self._start_btn.setFixedHeight(36)
        self._start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self._start_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _create_app_icon(self) -> QPixmap:
        """创建应用图标 - 使用满木图片"""
        import os
        # 查找满木图片
        logo_paths = []
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
            logo_paths.append(os.path.join(base, "resources", "满木.png"))
            logo_paths.append(os.path.join(getattr(sys, '_MEIPASS', base), "resources", "满木.png"))
        else:
            current_file = os.path.abspath(__file__)
            # welcome_dialog.py 在 src/ui/ → 往上3层
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
                    target = 80
                    pixmap = pixmap.scaled(target, target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    # 圆角
                    rounded = QPixmap(target, target)
                    rounded.fill(Qt.transparent)
                    painter = QPainter(rounded)
                    painter.setRenderHint(QPainter.Antialiasing)
                    from PySide6.QtGui import QPainterPath
                    path_obj = QPainterPath()
                    path_obj.addRoundedRect(0, 0, target, target, 18, 18)
                    painter.setClipPath(path_obj)
                    painter.drawPixmap(0, 0, pixmap)
                    painter.end()
                    return rounded

        # 备用：画一个简单的图标
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor("#82B1FF")))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 64, 64, 14, 14)
        icon_pixmap = get_icon_pixmap("box", 36, QColor(255, 255, 255))
        painter.drawPixmap(14, 14, icon_pixmap)
        painter.end()
        return pixmap

    def _create_welcome_page(self) -> QWidget:
        """创建欢迎页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        info = QLabel(
            "<div style='line-height: 1.8;'>"
            "<p><b>首次启动检测</b></p>"
            "<p>为确保最佳体验，程序将自动检查并安装所需依赖。</p>"
            "<p style='color: #8C8FA1; font-size: 12px;'>"
            "核心功能（PDF、图片、文档处理等）将自动安装<br>"
            "外部工具（LibreOffice、FFmpeg）可在依赖管理页面按需下载"
            "</p>"
            "<p style='color: #8C8FA1; font-size: 12px;'>"
            "首次安装约需 2-5 分钟，之后启动无需等待"
            "</p>"
            "</div>"
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 14px; padding: 16px; background: rgba(30, 30, 46, 0.1); border-radius: 8px;")
        layout.addWidget(info)

        layout.addStretch()
        return page

    def _create_install_page(self) -> QWidget:
        """创建安装进度页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        self._install_progress = QProgressBar()
        layout.addWidget(self._install_progress)

        self._install_status = QLabel("准备开始...")
        self._install_status.setStyleSheet("font-size: 13px;")
        self._install_status.setWordWrap(True)
        self._install_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._install_status)

        hint = QLabel(
            "<p style='color: #8C8FA1; font-size: 11px; text-align: center;'>"
            "安装过程中请勿关闭此窗口<br>"
            "如遇网络问题，请检查网络连接后重试"
            "</p>"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()
        return page

    def _create_done_page(self) -> QWidget:
        """创建完成页"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        # 成功图标
        success_icon = QLabel()
        success_icon.setAlignment(Qt.AlignCenter)
        success_pixmap = get_icon_pixmap("check", 64, QColor(43, 169, 109))
        success_icon.setPixmap(success_pixmap)
        success_icon.setFixedHeight(80)
        layout.addWidget(success_icon)

        done_text = QLabel(
            "<h3 style='color: #2BA96D; text-align: center;'>一切就绪！</h3>"
            "<p style='text-align: center;'>"
            "核心依赖已安装完成<br>"
            "现在可以开始使用所有功能了"
            "</p>"
        )
        done_text.setWordWrap(True)
        layout.addWidget(done_text)

        layout.addStretch()
        return page

    def _on_start(self):
        """开始按钮点击"""
        if self._stack.currentIndex() == 0:
            self._stack.setCurrentIndex(1)
            self._cancel_btn.setEnabled(True)
            self._start_btn.setEnabled(False)
            self._start_btn.setText("安装中...")
            self._start_btn.setObjectName("")
            self._start_btn.setStyleSheet(
                "QPushButton { background: #6C6F85; color: white; border: none; border-radius: 6px; padding: 6px 24px; font-weight: bold; }"
            )
            self._start_installation()

    def _start_installation(self):
        """开始安装"""
        self._worker = InstallWorker()
        self._worker.progress.connect(self._on_install_progress)
        self._worker.finished_ok.connect(self._on_install_ok)
        self._worker.finished_error.connect(self._on_install_error)
        self._worker.start()

    def _on_install_progress(self, value: int, msg: str):
        """安装进度回调"""
        self._install_progress.setValue(value)
        self._install_status.setText(msg)

    def _on_install_ok(self):
        """安装成功回调"""
        self._stack.setCurrentIndex(2)
        self._cancel_btn.setEnabled(False)
        self._start_btn.setEnabled(True)
        self._start_btn.setText("开始使用")
        self._start_btn.setObjectName("primaryBtn")
        self._start_btn.setStyleSheet("")

    def _on_install_error(self, error_msg: str):
        """安装失败回调"""
        self._stack.setCurrentIndex(2)
        self._cancel_btn.setEnabled(False)
        self._start_btn.setEnabled(True)
        self._start_btn.setText("重试")
        self._start_btn.setObjectName("primaryBtn")
        self._start_btn.setStyleSheet("")

        QMessageBox.critical(
            self,
            "安装失败",
            f"依赖安装遇到问题:\n\n{error_msg}\n\n"
            f"您可以在依赖管理页面手动安装，或点击重试。"
        )

        self._on_install_error_msg = error_msg

    def _on_cancel(self):
        """取消按钮点击"""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
        self.reject()

    def closeEvent(self, event):
        """窗口关闭事件"""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
        event.accept()


def check_and_show_welcome() -> bool:
    """检测并显示欢迎界面"""
    try:
        from src.core.dependency_manager import check_all_dependencies
        status = check_all_dependencies()
        return status["all_essential_ok"]
    except Exception:
        return False
