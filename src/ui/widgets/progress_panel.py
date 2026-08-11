from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QSizePolicy
)


class ProgressPanel(QWidget):
    cancelled = Signal()
    retry_requested = Signal()
    completed_all = Signal()
    open_dir_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._task_count = 0
        self._completed_count = 0
        self._success_count = 0
        self._failed_count = 0
        self._last_output_dir = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()

        self._status_label = QLabel("就绪")
        status_font = QFont()
        status_font.setPointSize(11)
        self._status_label.setFont(status_font)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(20)

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setFixedSize(80, 28)
        self._cancel_btn.clicked.connect(self.cancelled.emit)
        self._cancel_btn.hide()

        self._retry_btn = QPushButton("重试失败")
        self._retry_btn.setFixedSize(100, 28)
        self._retry_btn.clicked.connect(self.retry_requested.emit)
        self._retry_btn.hide()

        self._open_dir_btn = QPushButton("打开目录")
        self._open_dir_btn.setFixedSize(100, 28)
        self._open_dir_btn.clicked.connect(
            lambda: self.open_dir_requested.emit(self._last_output_dir)
        )
        self._open_dir_btn.hide()

        header_layout.addWidget(self._status_label, 1)
        header_layout.addWidget(self._open_dir_btn)
        header_layout.addWidget(self._cancel_btn)
        header_layout.addWidget(self._retry_btn)

        layout.addLayout(header_layout)
        layout.addWidget(self._progress_bar)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["文件", "状态", "结果"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setMaximumHeight(180)
        self._table.hide()

        layout.addWidget(self._table)

    def set_output_dir(self, path: str):
        """记录输出目录，供「打开目录」按钮使用"""
        self._last_output_dir = path or ""

    def start_tasks(self, task_count: int):
        self._task_count = task_count
        self._completed_count = 0
        self._success_count = 0
        self._failed_count = 0
        self._last_output_dir = ""
        self._progress_bar.setValue(0)
        self._progress_bar.setMaximum(100)
        self._status_label.setText(f"处理中... 0/{task_count}")
        self._cancel_btn.show()
        self._retry_btn.hide()
        self._open_dir_btn.hide()
        self._table.setRowCount(0)
        if task_count > 1:
            self._table.show()

    def update_progress(self, value: int, message: str = ""):
        self._progress_bar.setValue(value)
        if message:
            self._status_label.setText(message)

    def add_file_result(self, file_path: str, success: bool, message: str = ""):
        row = self._table.rowCount()
        self._table.insertRow(row)

        filename = file_path.split('/')[-1].split('\\')[-1]
        self._table.setItem(row, 0, QTableWidgetItem(filename))

        status_item = QTableWidgetItem("✓ 成功" if success else "✗ 失败")
        status_item.setForeground(
            QColor("#A6E3A1") if success else QColor("#F38BA8")
        )
        self._table.setItem(row, 1, status_item)

        self._table.setItem(row, 2, QTableWidgetItem(message))

        self._completed_count += 1
        if success:
            self._success_count += 1
        else:
            self._failed_count += 1

        self._status_label.setText(
            f"处理中... {self._completed_count}/{self._task_count}"
        )

    def finish_all(self, success: bool, message: str, error: str = ""):
        self._cancel_btn.hide()
        self._progress_bar.setValue(100 if success else self._progress_bar.value())
        if self._failed_count > 0:
            self._retry_btn.show()
        else:
            self._retry_btn.hide()
        # 成功且有输出目录时显示「打开目录」
        if success and self._last_output_dir:
            self._open_dir_btn.show()
        else:
            self._open_dir_btn.hide()
        status_text = f"{message}"
        if error:
            status_text += f"  ({error})"
        self._status_label.setText(status_text)
        self.completed_all.emit()
