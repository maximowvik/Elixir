import os
import json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QSpacerItem, QSizePolicy, QFileDialog, QComboBox, QLabel
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint
from PyQt6.QtGui import QScreen
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image
from mss import mss
from .aeraselection import AreaSelection
from .iconmanager import IconManager

class ScreenshotWindow(QWidget):
    def __init__(self, theme_manager, translations: dict[str, str]):
        super().__init__()
        self._old_pos = None
        self.theme_manager = theme_manager
        self.translations = translations

        # Подписка на сигнал изменения темы
        self.theme_manager.theme_changed.connect(self.update_theme)

        self.initUI()

        # Обновляем тему после создания всех элементов
        self.update_theme(self.theme_manager.current_theme())

    def update_theme(self, theme):
        palette = self.theme_manager.theme_palette[theme]
        main_style = f"""
            QWidget {{
                background-color: {palette['bg']};
                color: {palette['fg']};
                border-radius: 8px;
                font-family: 'Segoe UI';
                font-size: 12pt;
            }}

            QWidget#canvas{{
                background-color: {palette['bg']};
                color: {palette['fg']};
                border: 1px solid {palette['border']};
            }}

            QPushButton {{
                height: 30px;
                background-color: {palette['bg']};
                color: {palette['fg']};
                border: 1px solid {palette['border']};
                border-radius: 8px;
                padding: 8px 15px;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background-color: {palette['hover']};
            }}
            QPushButton:pressed {{
                background-color: {palette['pressed']};
            }}
            QLabel {{
                font-size: 10pt;
                margin-bottom: 5px;
            }}
            QSlider {{
                min-height: 25px;
            }}
            QSlider::groove:horizontal {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {palette['bg_info']}, stop:1 {palette['border']}
                );
                height: 10px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {palette['fg']};
                width: 20px;
                height: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {palette['bg_info']}, stop:1 {palette['bg_info']}
                );
                border-radius: 3px;
            }}
            QComboBox {{height:25px; background: {palette['hover']}; border: 1px solid {palette['border']}; color: {palette['fg']}; padding: 10px; border-radius: 8px;}}
            QComboBox:hover {{ background: {palette['bg']}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{ background: {palette['bg']}; color: {palette['fg']}; selection-background-color: #ff4891; }}
        """
        self.setStyleSheet(main_style)

    def initUI(self):
        self.setWindowTitle(self.translations["screenshot_window_title"])
        self.setWindowIcon(IconManager.get_icon("screenshot"))

        self.main_layout = QVBoxLayout()
        self.setup_title_bar()

        # Кнопка для скриншота всего экрана
        self.fullscreen_button = QPushButton(self.translations["fullscreen_button"], self)
        self.fullscreen_button.clicked.connect(self.take_fullscreen_screenshot)
        self.main_layout.addWidget(self.fullscreen_button)

        # Кнопка для скриншота области
        self.area_button = QPushButton(self.translations["area_button"], self)
        self.area_button.clicked.connect(self.take_area_screenshot)
        self.main_layout.addWidget(self.area_button)

        # Выбор формата сохранения
        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["PNG", "JPG", "PDF", "BMP", "GIF", "TIFF"])
        self.main_layout.addWidget(self.format_combo)

        # Выбор экрана
        self.screen_combo = QComboBox(self)
        self.screen_combo.addItems([f"Screen {i}" for i in range(1, len(self.get_screens()) + 1)])
        self.main_layout.addWidget(self.screen_combo)

        self.setLayout(self.main_layout)
        self.center_window(self)

    def setup_title_bar(self):
        if self.theme_manager.get_current_platform() == "windows":
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        title_layout = QHBoxLayout()
        self.title_label = QLabel(self.translations["screenshot_window_title"])
        title_layout.addWidget(self.title_label)
        title_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        if self.theme_manager.get_current_platform() == "windows":
            for icon, handler in [("roll_up_button", self.showMinimized), ("button_close", self.close)]:
                btn = self.theme_manager.create_title_button(IconManager.get_images(icon), handler)
                title_layout.addWidget(btn)

        self.main_layout.addLayout(title_layout)

    def get_screens(self):
        with mss() as sct:
            return sct.monitors[1:]

    def take_fullscreen_screenshot(self):
        screen_index = self.screen_combo.currentIndex()
        screens = self.get_screens()
        if screen_index < len(screens):
            screen = screens[screen_index]
            with mss() as sct:
                screenshot = sct.grab(screen)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                self.save_screenshot(img)

    def take_area_screenshot(self):
        self.hide()
        self.area_selection = AreaSelection(self.translations)
        self.area_selection.screenshot_taken.connect(self.handle_screenshot_taken)
        self.area_selection.show()

    def handle_screenshot_taken(self, img):
        """Обработчик сигнала после создания скриншота области"""
        self.area_selection.close()  # Закрываем окно выбора области
        self.show()
        self.raise_()
        self.activateWindow()
        self.save_screenshot(img)

    def save_screenshot(self, img):
        file_format = self.format_combo.currentText().lower()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.translations["save_screenshot_dialog_title"],
            "",
            f"{file_format.upper()} Files (*.{file_format})"
        )

        if file_path:
            if file_format == "pdf":
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

    def _is_in_title_bar(self, pos):
        title_height = 40
        return pos.y() <= title_height

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_in_title_bar(event.position().toPoint()):
                self._old_pos = event.globalPosition().toPoint()
            else:
                self._old_pos = None

    def mouseMoveEvent(self, event):
        if self._old_pos is not None:
            delta = QPoint(event.globalPosition().toPoint() - self._old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = None
