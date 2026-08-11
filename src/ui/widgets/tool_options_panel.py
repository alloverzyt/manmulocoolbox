# -*- coding: utf-8 -*-
"""
工具参数配置面板

参数区域的GroupBox使用自适应文字高度、大字号滑轨。
"""

from typing import Dict, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QFormLayout, QGroupBox, QScrollArea, QSizePolicy, QSlider
)


class ToolOptionsPanel(QWidget):
    options_changed = Signal(dict)

    def __init__(self, plugin=None, parent=None):
        super().__init__(parent)
        self._plugin = plugin
        self._widgets: Dict[str, Any] = {}
        self._output_dir = ""
        self._files = []

        self._setup_ui()
        if plugin:
            self.load_plugin_options(plugin)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # 待处理文件分组：最小高度保证文字不被压扁
        self._file_section = QGroupBox("待处理文件")
        self._file_section.setMinimumHeight(110)
        self._file_section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        file_layout = QVBoxLayout(self._file_section)
        file_layout.setSpacing(4)
        self._file_list_label = QLabel("尚未选择文件")
        self._file_list_label.setWordWrap(True)
        self._file_list_label.setMinimumHeight(54)
        file_font = QFont("Microsoft YaHei UI", 12)
        self._file_list_label.setFont(file_font)
        file_layout.addWidget(self._file_list_label)
        layout.addWidget(self._file_section)

        # 参数设置分组：最小高度+可扩展，绝不被挤压
        self._options_section = QGroupBox("参数设置")
        self._options_section.setMinimumHeight(140)
        self._options_section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        self._options_layout = QFormLayout(self._options_section)
        self._options_layout.setSpacing(14)
        self._options_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self._options_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._options_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        # 给参数Label也设字体，避免默认小字号
        layout.addWidget(self._options_section)

        # 输出设置分组
        self._output_section = QGroupBox("输出设置")
        self._output_section.setMinimumHeight(110)
        self._output_section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        output_layout = QFormLayout(self._output_section)
        output_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        output_layout.setSpacing(12)
        self._output_dir_edit = QLineEdit()
        self._output_dir_edit.setPlaceholderText("默认: 与源文件同目录")
        self._output_dir_edit.setMinimumHeight(40)
        out_font = QFont("Microsoft YaHei UI", 12)
        self._output_dir_edit.setFont(out_font)
        self._output_dir_edit.textChanged.connect(self._on_options_changed)
        output_label = QLabel("输出目录:")
        output_label.setFont(QFont("Microsoft YaHei UI", 12))
        output_layout.addRow(output_label, self._output_dir_edit)
        layout.addWidget(self._output_section)

        layout.addStretch()

    def load_plugin_options(self, plugin):
        self._plugin = plugin
        self._clear_options()

        schema = plugin.options_schema
        if not schema:
            self._options_section.setVisible(False)
            return

        self._options_section.setVisible(True)
        label_font = QFont("Microsoft YaHei UI", 12)
        for key, config in schema.items():
            widget = self._create_option_widget(key, config)
            if widget:
                self._widgets[key] = widget
                label_text = config.get("label", key)
                # 手动创建Label并设置12号字体，确保不被挤压
                label_widget = QLabel(f"{label_text}:")
                label_widget.setFont(label_font)
                label_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                label_widget.setMinimumWidth(90)
                self._options_layout.addRow(label_widget, widget)

    def _clear_options(self):
        self._widgets.clear()
        while self._options_layout.rowCount():
            self._options_layout.removeRow(0)

    def _create_option_widget(self, key: str, config: Dict[str, Any]):
        """创建选项控件 - 大字号、大控件自适应"""
        opt_type = config.get("type", "string")
        default = config.get("default", "")
        label_font = QFont("Microsoft YaHei UI", 12)
        value_font = QFont("Microsoft YaHei UI", 12)

        if opt_type == "string" or opt_type == "text":
            widget = QLineEdit(str(default))
            widget.setMinimumHeight(40)
            widget.setFont(value_font)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            widget.textChanged.connect(self._on_options_changed)
            return widget
        elif opt_type == "integer":
            widget = QSpinBox()
            widget.setRange(config.get("min", 1), config.get("max", 99999))
            widget.setValue(int(default))
            widget.setMinimumHeight(40)
            widget.setMinimumWidth(140)
            widget.setFont(value_font)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            widget.valueChanged.connect(self._on_options_changed)
            return widget
        elif opt_type == "float":
            widget = QDoubleSpinBox()
            widget.setRange(config.get("min", 0.0), config.get("max", 100.0))
            widget.setValue(float(default))
            widget.setSingleStep(config.get("step", 0.1))
            widget.setMinimumHeight(40)
            widget.setMinimumWidth(140)
            widget.setFont(value_font)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            widget.valueChanged.connect(self._on_options_changed)
            return widget
        elif opt_type == "boolean":
            widget = QCheckBox()
            widget.setChecked(bool(default))
            widget.setMinimumHeight(40)
            widget.setFont(label_font)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            widget.stateChanged.connect(self._on_options_changed)
            return widget
        elif opt_type == "select":
            widget = QComboBox()
            widget.setMinimumHeight(40)
            widget.setMinimumWidth(140)
            widget.setFont(value_font)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            for opt in config.get("options", []):
                if isinstance(opt, dict):
                    widget.addItem(opt.get("label", opt.get("value", "")), opt.get("value"))
                else:
                    widget.addItem(str(opt), opt)
            idx = widget.findData(default)
            if idx >= 0:
                widget.setCurrentIndex(idx)
            widget.currentIndexChanged.connect(self._on_options_changed)
            return widget
        elif opt_type == "slider":
            # 滑块控件 - 大滑轨 + 大数值标签
            container = QWidget()
            container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            h_layout = QHBoxLayout(container)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(12)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(config.get("min", 0), config.get("max", 100))
            slider.setValue(int(default))
            slider.setMinimumHeight(44)
            slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            value_label = QLabel(str(default))
            value_label.setMinimumWidth(56)
            value_label.setAlignment(Qt.AlignCenter)
            value_font_large = QFont("Microsoft YaHei UI", 13)
            value_font_large.setBold(True)
            value_label.setFont(value_font_large)
            slider.valueChanged.connect(lambda v: value_label.setText(str(v)))
            slider.valueChanged.connect(self._on_options_changed)
            h_layout.addWidget(slider, 1)
            h_layout.addWidget(value_label)
            return container
        return None

    def set_need_files(self, need: bool):
        """
        切换是否需要输入文件

        时间戳转换、颜色转换、二维码生成等无文件工具调用 need=False，
        隐藏「待处理文件」分组，避免无意义的空白区域占位。
        """
        self._file_section.setVisible(need)
        if not need:
            self._file_list_label.setText("此工具无需输入文件，直接设置下方参数后即可运行")

    def set_files(self, files: list):
        self._files = files
        if not files:
            self._file_list_label.setText("尚未选择文件")
        elif len(files) <= 3:
            names = [f.split('/')[-1].split('\\')[-1] for f in files]
            self._file_list_label.setText(f"已选择 {len(files)} 个文件:\n" + "\n".join(names))
        else:
            self._file_list_label.setText(f"已选择 {len(files)} 个文件: " + ", ".join(
                f.split('/')[-1].split('\\')[-1] for f in files[:3]
            ) + f" 等")

    def get_options(self) -> Dict[str, Any]:
        options = {}
        for key, widget in self._widgets.items():
            if isinstance(widget, QLineEdit):
                options[key] = widget.text()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                options[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                options[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                options[key] = widget.currentData()
            elif isinstance(widget, QWidget):
                # slider 容器 - 找到内部的 QSlider
                slider = widget.findChild(QSlider)
                if slider:
                    options[key] = slider.value()
        if self._output_dir_edit.text():
            options["output_dir"] = self._output_dir_edit.text()
        return options

    def _on_options_changed(self):
        self.options_changed.emit(self.get_options())
