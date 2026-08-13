# -*- coding: utf-8 -*-
"""
插件接口模块

定义插件的抽象基类和相关数据结构。
所有插件必须继承 BasePlugin 并实现 execute 方法。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


class PluginStatus(Enum):
    """插件执行状态枚举"""
    IDLE = "idle"           # 空闲
    RUNNING = "running"     # 运行中
    SUCCESS = "success"     # 成功
    FAILED = "failed"       # 失败
    CANCELLED = "cancelled" # 已取消


class PluginInput:
    """插件输入数据"""

    def __init__(self, file_paths: List[str] = None, options: Dict[str, Any] = None):
        """
        初始化插件输入

        Args:
            file_paths: 输入文件路径列表
            options: 插件选项配置
        """
        self.file_paths = file_paths or []
        self.options = options or {}


class PluginResult:
    """插件执行结果"""

    def __init__(self, success: bool, output_paths: List[str] = None,
                 message: str = "", error: str = "", metadata: Dict[str, Any] = None):
        """
        初始化插件结果

        Args:
            success: 是否成功
            output_paths: 输出文件路径列表
            message: 成功消息
            error: 错误消息
            metadata: 额外元数据
        """
        self.success = success
        self.output_paths = output_paths or []
        self.message = message
        self.error = error
        self.metadata = metadata or {}


class BasePlugin(ABC):
    """
    插件抽象基类

    所有功能插件都必须继承此类并实现抽象方法。
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """插件唯一标识"""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """插件显示名称"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """插件功能描述"""
        ...

    @property
    def category(self) -> str:
        """插件分类"""
        return "other"

    @property
    def icon(self) -> str:
        """
        插件图标键名

        返回图标键名（如 "pdf", "image", "document" 等），
        由 IconDrawer 绘制对应的简笔画图标。
        """
        return "tools"

    @property
    def version(self) -> str:
        """插件版本号"""
        return "1.0.0"

    @property
    def requires_files(self) -> bool:
        """
        是否需要输入文件

        时间戳转换、颜色转换等纯参数类工具无需文件，
        返回 False 时 UI 不再强制要求拖入文件。
        """
        return True

    @property
    def process_files_together(self) -> bool:
        """
        是否把全部输入文件一次性交给 execute

        合并、批量比对等需要"同时看到所有文件"的工具（如 PDF合并、
        重复文件查找）必须设为 True；否则 TaskWorker 会逐文件调用 execute，
        导致这类工具永远只收到 1 个文件而无法工作。
        """
        return False

    @property
    def supported_input_formats(self) -> List[str]:
        """支持的输入文件格式"""
        return []

    @property
    def supported_output_formats(self) -> List[str]:
        """支持的输出文件格式"""
        return []

    @property
    def options_schema(self) -> Dict[str, Any]:
        """
        选项配置 Schema

        返回选项定义字典，用于自动生成配置界面。
        """
        return {}

    def validate_input(self, input_data: PluginInput) -> Optional[str]:
        """
        验证输入数据

        Args:
            input_data: 插件输入数据

        Returns:
            错误消息字符串，验证通过返回 None
        """
        if not input_data.file_paths:
            return "请至少选择一个文件"
        for path in input_data.file_paths:
            ext = path.rsplit('.', 1)[-1].lower() if '.' in path else ''
            if self.supported_input_formats and ext not in self.supported_input_formats:
                return f"不支持的文件格式: .{ext}"
        return None

    def check_environment(self) -> Optional[str]:
        """
        检查插件运行所需的运行时依赖（外部工具 / 可选库）。

        返回 None 表示环境就绪；返回字符串表示缺失依赖的提示信息。
        UI 在选中插件时调用：依赖缺失时应提示"先安装依赖"而不是允许拖入文件。

        各插件按需覆写，默认视为环境就绪。
        """
        return None

    @abstractmethod
    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        """
        执行插件功能

        Args:
            input_data: 插件输入数据
            progress_callback: 进度回调函数

        Returns:
            插件执行结果
        """
        ...

    def cancel(self):
        """取消正在执行的任务"""
        pass
