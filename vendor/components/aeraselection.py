import json
from PyQt6.QtWidgets import (
    QWidget
)
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QPen
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QRect
import mss
from PIL import Image
from werkzeug.serving import make_server
from vendor.components.iconmanager import IconManager

class AreaSelection(QWidget):
    screenshot_taken = pyqtSignal(Image.Image)

    def __init__(self, translations: dict[str, str], parent=None):
        super().__init__(parent)
        self.translations = translations
        self.initUI()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.show()

    def initUI(self):
        self.setWindowTitle(self.translations["area_selection_title"])
        self.setWindowIcon(IconManager.get_icon("area_selection"))
        self.start_pos = None
        self.end_pos = None
        self.drawing = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.fillPath(path, QColor(0, 0, 0, 128))
        painter.setClipPath(path)

        if self.start_pos and self.end_pos:
            rect = QRect(self.start_pos, self.end_pos).normalized()
            painter.setPen(QPen(Qt.GlobalColor.white, 2, Qt.PenStyle.DashLine))
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.drawing = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.end_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            self.drawing = False
            self.update()
            self.take_screenshot()

    def take_screenshot(self):
        if self.start_pos and self.end_pos:
            rect = QRect(self.start_pos, self.end_pos).normalized()
            monitor = {
                "top": rect.top(),
                "left": rect.left(),
                "width": rect.width(),
                "height": rect.height()
            }
            with mss.mss() as sct:
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                self.screenshot_taken.emit(img)
                self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
