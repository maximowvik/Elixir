import os
import json
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QFileDialog,
    QComboBox
)
import mss
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint
from PyQt6.QtGui import QScreen
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image
from .aeraselection import AreaSelection
from .iconmanager import IconManager


class ScreenshotWindow(QWidget):
    def __init__(self, language):
        super().__init__()
        self._old_pos = None
        self.language = language
        self.translations = self.load_translations(language)
        self.initUI()

    def load_translations(self, language):
        with open(f"{language}.json", "r", encoding="utf-8") as file:
            return json.load(file)

    def initUI(self):
        self.setWindowTitle(self.translations["screenshot_window_title"])
        self.setWindowIcon(IconManager.get_icon("screenshot"))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout()

        title_layout = QHBoxLayout()

        title_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        #Кнопка свернуть
        minimize_button = QPushButton()
        minimize_button.setStyleSheet("background-color: transparent; border: none;")
        pixmap_minimize = QPixmap("pic/minus.png")
        icon_minimize = QIcon(pixmap_minimize)
        minimize_button.setIcon(icon_minimize)
        minimize_button.setIconSize(QSize(30, 30))
        minimize_button.clicked.connect(self.showMinimized)
        title_layout.addWidget(minimize_button)

        #Кнопка закрытия
        close_button = QPushButton()
        close_button.setStyleSheet("background-color: transparent; border: none;")
        pixmap_close = QPixmap("pic/close.png")
        icon_close = QIcon(pixmap_close)
        close_button.setIcon(icon_close)
        close_button.setIconSize(QSize(30, 30))
        close_button.clicked.connect(self.close)
        title_layout.addWidget(close_button)

        main_layout.addLayout(title_layout)

        #Кнопка для скриншота всего экрана
        self.fullscreen_button = QPushButton(self.translations["fullscreen_button"], self)
        self.fullscreen_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.fullscreen_button.clicked.connect(self.take_fullscreen_screenshot)
        main_layout.addWidget(self.fullscreen_button)

        #Кнопка для скриншота области
        self.area_button = QPushButton(self.translations["area_button"], self)
        self.area_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.area_button.clicked.connect(self.take_area_screenshot)
        main_layout.addWidget(self.area_button)

        #Выбор формата сохранения
        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["PNG", "JPG", "PDF", "BMP", "GIF", "TIFF"])
        self.format_combo.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        main_layout.addWidget(self.format_combo)

        #Выбор экрана
        self.screen_combo = QComboBox(self)
        self.screen_combo.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.screen_combo.addItems([f"Screen {i}" for i in range(1, len(self.get_screens()) + 1)])
        main_layout.addWidget(self.screen_combo)

        self.setLayout(main_layout)
        self.center_window(self)

    def get_screens(self):
        with mss.mss() as sct:
            return sct.monitors[1:]

    def take_fullscreen_screenshot(self):
        screen_index = self.screen_combo.currentIndex()
        screens = self.get_screens()
        if screen_index < len(screens):
            screen = screens[screen_index]
            with mss.mss() as sct:
                screenshot = sct.grab(screen)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                self.save_screenshot(img)

    def take_area_screenshot(self):
        self.hide()
        self.area_selection = AreaSelection(self.language)
        self.area_selection.screenshot_taken.connect(self.save_screenshot)
        self.area_selection.show()

    def save_screenshot(self, img):
        file_format = self.format_combo.currentText().lower()
        file_path, _ = QFileDialog.getSaveFileName(self, self.translations["save_screenshot_dialog_title"], "", f"{file_format.upper()} Files (*.{file_format})")

        if file_path:
            if file_format == "pdf":
                #PDF-документ
                temp_image_path = "temp_image.png"
                img.save(temp_image_path)
                c = canvas.Canvas(file_path, pagesize=letter)
                width, height = letter
                c.drawImage(temp_image_path, (width - img.size[0]) / 2, (height - img.size[1]) / 2, width=img.size[0], height=img.size[1])
                c.save()
                os.remove(temp_image_path)
            else:
                img.save(file_path)

    def center_window(self, window):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        qr = window.frameGeometry()
        cp = screen.center()
        qr.moveCenter(cp)
        window.move(qr.topLeft())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.fillPath(path, QColor(self.palette().color(self.backgroundRole())))
        painter.setClipPath(path)
        super().paintEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._old_pos is not None:
            delta = QPoint(event.globalPosition().toPoint() - self._old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = None
