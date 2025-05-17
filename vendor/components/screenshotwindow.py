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
    def __init__(self, language, theme_manager):
        super().__init__()
        self._old_pos = None
        self.language = language
        self.theme_manager = theme_manager
        self.translations = self.load_translations(self.language)
        
        # Подписка на сигнал изменения темы
        self.theme_manager.theme_changed.connect(self.update_theme)
        
        self.initUI()
        
        # Обновляем тему после создания всех элементов
        self.update_theme(self.theme_manager.current_theme())
        
    def create_title_button(self, icon_path, slot):
        btn = QPushButton()
        btn.setIcon(QIcon(QPixmap(icon_path)))
        btn.setIconSize(QSize(30, 30))
        btn.setFixedSize(40, 40)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 30);
            }
            QPushButton:pressed {
                background: rgba(0, 0, 0, 50);
            }
        """)
        btn.clicked.connect(slot)
        return btn

    def load_translations(self, language):
        with open(f"{language}.json", "r", encoding="utf-8") as file:
            return json.load(file)

    def update_theme(self, theme):
        theme_vals = self.theme_manager.theme_palette[theme]
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme_vals['bg']};
                color: {theme_vals['fg']};
                font-family: 'Segoe UI';
                font-size: 12pt;
            }}
            QPushButton {{
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
                border: 1px solid {theme_vals['border']};
                border-radius: 10px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background: {theme_vals['hover']};
            }}
            QPushButton:pressed {{
                background: {theme_vals['pressed']};
            }}
            QPushButton:disabled {{
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
                border: 1px solid {theme_vals['border']};
                opacity: 0.5;
            }}
            QLabel {{
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
                border: 1px solid {theme_vals['border']};
                border-radius: 10px;
                padding: 10px;
            }}
            QComboBox {{
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
                border: 1px solid {theme_vals['border']};
                border-radius: 10px;
                padding: 10px;
                min-width: 6em;
            }}
            QComboBox:hover {{
                background: {theme_vals['hover']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: url(pic/down-arrow.png);
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
                border: 1px solid {theme_vals['border']};
                border-radius: 10px;
                selection-background-color: {theme_vals['hover']};
                selection-color: {theme_vals['fg']};
            }}
        """)
        
        # Обновляем стили отдельных элементов
        self.fullscreen_button.setStyleSheet(f"""
            background: {theme_vals['bg']};
            color: {theme_vals['fg']};
            border: 1px solid {theme_vals['border']};
            border-radius: 10px;
            padding: 10px;
            font-family: 'Segoe UI';
            font-size: 12pt;
        """)
        
        self.area_button.setStyleSheet(f"""
            background: {theme_vals['bg']};
            color: {theme_vals['fg']};
            border: 1px solid {theme_vals['border']};
            border-radius: 10px;
            padding: 10px;
            font-family: 'Segoe UI';
            font-size: 12pt;
        """)
        
        self.format_combo.setStyleSheet(f"""
            background: {theme_vals['bg']};
            color: {theme_vals['fg']};
            border: 1px solid {theme_vals['border']};
            border-radius: 10px;
            padding: 10px;
            font-family: 'Segoe UI';
            font-size: 12pt;
        """)
        
        self.screen_combo.setStyleSheet(f"""
            background: {theme_vals['bg']};
            color: {theme_vals['fg']};
            border: 1px solid {theme_vals['border']};
            border-radius: 10px;
            padding: 10px;
            font-family: 'Segoe UI';
            font-size: 12pt;
        """)

    def initUI(self):
        self.setWindowTitle(self.translations["screenshot_window_title"])
        self.setWindowIcon(IconManager.get_icon("screenshot"))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout()

        title_layout = QHBoxLayout()

        title_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        for icon, slot in [(IconManager.get_images("roll_up_button"), self.showMinimized),
                           (IconManager.get_images("button_close"), self.close)]:
            btn = self.create_title_button(icon, slot)
            title_layout.addWidget(btn)

        main_layout.addLayout(title_layout)

        #Кнопка для скриншота всего экрана
        self.fullscreen_button = QPushButton(self.translations["fullscreen_button"], self)
        self.fullscreen_button.clicked.connect(self.take_fullscreen_screenshot)
        main_layout.addWidget(self.fullscreen_button)

        #Кнопка для скриншота области
        self.area_button = QPushButton(self.translations["area_button"], self)
        self.area_button.clicked.connect(self.take_area_screenshot)
        main_layout.addWidget(self.area_button)

        #Выбор формата сохранения
        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["PNG", "JPG", "PDF", "BMP", "GIF", "TIFF"])
        main_layout.addWidget(self.format_combo)

        #Выбор экрана
        self.screen_combo = QComboBox(self)
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

    def _is_in_title_bar(self, pos):
        # Получаем геометрию заголовка
        title_height = 40  # Высота заголовка
        return pos.y() <= title_height

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Проверяем, находится ли курсор в области заголовка
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
