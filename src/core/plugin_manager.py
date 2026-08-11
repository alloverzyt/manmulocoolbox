import os
import sys
import json
import importlib
from typing import Dict, Type, List, Optional

from .plugin_interface import BasePlugin, PluginInput, PluginResult
from .events import EventBus


def _resolve_plugins_dir() -> str:
    """解析插件目录：
    源码运行 → src/plugins；
    打包运行(frozen) → _MEIPASS/src/plugins（spec 已将插件目录作为数据打包进去）
    """
    default = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "plugins"
    )
    if os.path.isdir(default):
        return default
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        for cand in (
            os.path.join(meipass, "src", "plugins"),
            os.path.join(meipass, "plugins"),
        ):
            if os.path.isdir(cand):
                return cand
    return default


class PluginManager:
    def __init__(self, plugins_dir: str = None):
        self._plugins: Dict[str, Type[BasePlugin]] = {}
        self._instances: Dict[str, BasePlugin] = {}
        self._plugins_dir = plugins_dir or _resolve_plugins_dir()
        self._event_bus = EventBus()
        self._load_all()

    def _load_all(self):
        for category_dir in os.listdir(self._plugins_dir):
            category_path = os.path.join(self._plugins_dir, category_dir)
            if not os.path.isdir(category_path) or category_dir.startswith('_'):
                continue
            for file in os.listdir(category_path):
                if file.endswith('.py') and not file.startswith('_'):
                    module_name = f"src.plugins.{category_dir}.{file[:-3]}"
                    self._load_plugin(module_name)

    def _load_plugin(self, module_name: str):
        try:
            module = importlib.import_module(module_name)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                        and issubclass(attr, BasePlugin)
                        and attr is not BasePlugin):
                    instance = attr()
                    self._plugins[instance.id] = attr
                    self._instances[instance.id] = instance
                    self._event_bus.plugin_added.emit(instance.id)
                    self._event_bus.emit_log(f"加载插件: {instance.name}")
        except Exception as e:
            self._event_bus.emit_log(f"加载插件失败 {module_name}: {str(e)}", "error")

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        return self._instances.get(plugin_id)

    def get_all_plugins(self) -> List[BasePlugin]:
        return list(self._instances.values())

    def get_plugins_by_category(self, category: str) -> List[BasePlugin]:
        return [p for p in self._instances.values() if p.category == category]

    def get_categories(self) -> List[str]:
        categories = set()
        for p in self._instances.values():
            categories.add(p.category)
        return sorted(categories)

    def create_instance(self, plugin_id: str) -> Optional[BasePlugin]:
        plugin_class = self._plugins.get(plugin_id)
        if plugin_class:
            return plugin_class()
        return None

    def execute(self, plugin_id: str, input_data: PluginInput, progress_callback=None) -> PluginResult:
        instance = self.create_instance(plugin_id)
        if not instance:
            return PluginResult(success=False, error=f"插件不存在: {plugin_id}")
        validation_error = instance.validate_input(input_data)
        if validation_error:
            return PluginResult(success=False, error=validation_error)
        return instance.execute(input_data, progress_callback)

    def reload(self):
        self._instances.clear()
        self._plugins.clear()
        self._load_all()

    def discover_plugins(self):
        """发现并加载所有插件（与reload相同，用于兼容）"""
        self.reload()
