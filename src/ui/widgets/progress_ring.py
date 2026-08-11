from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget


class ProgressRing(QWidget):
    valueChanged = Signal(int)

    def __init__(self, size: int = 48, parent=None):
        super().__init__(parent)
        self._size = size
        self._value = 0
        self._color = QColor("#89B4FA")
        self._bg_color = QColor("#313244")
        self.setFixedSize(size + 8, size + 8)

    def setValue(self, value: int):
        self._value = max(0, min(100, value))
        self.valueChanged.emit(self._value)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(4, 4, -4, -4)

        pen_width = 6
        painter.setPen(QPen(self._bg_color, pen_width, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, 0, 360 * 16)

        if self._value > 0:
            painter.setPen(QPen(self._color, pen_width, Qt.SolidLine, Qt.RoundCap))
            span = int(-360 * 16 * self._value / 100)
            painter.drawArc(rect, 90 * 16, span)

        painter.setPen(Qt.NoPen)
        font = QFont()
        font.setPointSize(int(self._size / 5))
        font.setBold(True)
        painter.setFont(font)
        text_color = QColor("#E0E0E0")
        painter.setPen(text_color)
        text = f"{self._value}%"
        painter.drawText(rect, Qt.AlignCenter, text)
