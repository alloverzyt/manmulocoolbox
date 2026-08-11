from PySide6.QtCore import QObject, Signal


class EventBus(QObject):
    task_started = Signal(str)
    task_progress = Signal(str, int, str)
    task_completed = Signal(str, bool, str)
    task_failed = Signal(str, str)

    plugin_added = Signal(str)
    plugin_removed = Signal(str)

    file_dropped = Signal(list)

    theme_changed = Signal(str)
    language_changed = Signal(str)

    log_message = Signal(str, str)

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            super().__init__()
            self._initialized = True

    def emit_log(self, message: str, level: str = "info"):
        self.log_message.emit(message, level)
