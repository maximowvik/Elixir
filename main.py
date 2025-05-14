import sys
import os
import json
from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QGridLayout, 
                             QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy, QComboBox)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath
from PyQt6.QtCore import Qt, QSize, QRectF
from PyQt6.QtGui import QScreen, QRegion
from vendor.components.iconmanager import IconManager
from vendor.components.qrcodewindow import QRCodeWindow
from vendor.components.browser import Browser
from vendor.components.speedtestwindow import SpeedTestWindow
from vendor.components.screenrecoderwindow import ScreenRecorderWindow
from vendor.components.screenshotwindow import ScreenshotWindow
from vendor.components.screesharewindow import ScreenShareWindow
from vendor.components.tranlatorwindow import TranslatorWindow
from vendor.components.pcinfowindow import PCInfoWindow
from vendor.components.paintwindow import PaintWindow
from vendor.components.ai_chat import AIChatWindow
from vendor.components.manager_download import Download_Manager
from thememanager import ThemeManager

if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

theme_manager = ThemeManager()

class MainWindow(QWidget):
    def __init__(self, language, theme_manager, current_directory):
        super().__init__()
        self._old_pos = None
        self.language = language
        self.theme_manager = theme_manager
        self.download_manager = Download_Manager()
        self._title_bar_buttons = []
        self.translations = self.load_translations(self.language)
        self.current_directory = current_directory
        
        self.theme_manager.theme_changed.connect(self.update_theme)
        self.update_theme(self.theme_manager.current_theme())

        self.init_ui()
        self.setFixedSize(QSize(370, 700))

    def load_translations(self, lang):
        with open(f"vendor/core/language/{lang}.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def init_ui(self):
        self.setWindowTitle(self.translations["window_title"])
        self.setWindowIcon(IconManager.get_icon("main"))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.addLayout(self.create_title_bar())

        logo = QLabel()
        logo_pixmap = QPixmap(IconManager.get_images("main_logo"))
        logo.setPixmap(logo_pixmap.scaledToWidth(300, Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(logo)

        main_layout.addLayout(self.create_button_grid())
        self.setLayout(main_layout)

    def create_title_bar(self):
        title_bar = QHBoxLayout()

        self.language_combo = QComboBox()
        self.language_combo.addItem(QIcon("pic/ru.png"), "Русский")
        self.language_combo.addItem(QIcon("pic/en.png"), "English")
        self.language_combo.setFixedWidth(120)
        self.language_combo.currentIndexChanged.connect(self.change_language)
        title_bar.addWidget(self.language_combo)

        title_bar.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding))

        for icon, handler in [("change_theme", self.toggle_theme), ("pic/minus.png", self.showMinimized), ("button_close", self.close)]:
            btn = self.create_title_button(IconManager.get_images(icon) if 'pic' not in icon else icon, handler)
            self._title_bar_buttons.append(btn)
            title_bar.addWidget(btn)

        return title_bar

    def create_title_button(self, icon_path, handler):
        btn = QPushButton()
        btn.setIcon(QIcon(icon_path))
        btn.setIconSize(QSize(35, 35))
        btn.setFixedSize(40, 40)
        btn.clicked.connect(handler)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                padding: 4px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 30);
            }
            QPushButton:pressed {
                background: rgba(0, 0, 0, 50);
            }
        """)
        return btn

    def create_button_grid(self):
        grid = QGridLayout()
        grid.setVerticalSpacing(20)
        grid.setHorizontalSpacing(20)

        buttons = [
            ("QR Code", "qr_code", self.open_qr_window),
            ("Speed Test", "speed_test", self.open_speedtest),
            ("Microphone", "microphone", self.open_mic_window),
            ("Audio", "audio", self.open_audio_window),
            ("Paint", "paint", self.open_paint),
            ("PC Info", "pc_info", self.open_pc_info),
            ("Browser", "browser", self.open_browser),
            ("Screenshot", "screenshot", self.open_screenshot),
            ("Chat", "chat", self.open_chat_window),
            ("Recorder", "screen_recorder", self.open_recorder),
            ("Screen Share", "screen_share", self.open_screenshare),
            ("Translator", "translator", self.open_translator)
        ]

        for i, (text, icon, handler) in enumerate(buttons):
            btn = self.create_button(text, icon)
            btn.clicked.connect(handler)
            grid.addWidget(btn, i//3, i%3)

        return grid

    def create_button(self, text, icon_name):
        theme = self.theme_manager.theme_palette[self.theme]
        btn = QPushButton()
        btn.setIcon(QIcon(IconManager.get_images(icon_name)))
        btn.setIconSize(QSize(64, 64))
        btn.setFixedSize(QSize(100, 100))
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {theme['bg']};
                border-radius: 10px;
                padding: 15px;
                color: {theme['fg']};
                font-size: 14px;
                border: 0px solid {theme['border']};
                text-align: center;
            }}
            QPushButton:hover {{ background: {theme['hover']}; }}
            QPushButton:pressed {{ background: {theme['pressed']}; }}
        """)
        return btn

    def update_theme(self, theme: str):
        self.theme = theme
        theme_vals = self.theme_manager.theme_palette[self.theme]
        self.setStyleSheet(f"""
            QWidget {{ background-color: {theme_vals['bg']}; color: {theme_vals['fg']}; font-family: 'Segoe UI'; font-size: 12pt; }}
            QComboBox {{ background: {theme_vals['hover']}; border: 1px solid {theme_vals['border']}; color: {theme_vals['fg']}; padding: 5px 10px; border-radius: 8px; min-width: 120px; }}
            QComboBox:hover {{ background: {theme_vals['bg']}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{ background: {theme_vals['bg']}; color: {theme_vals['fg']}; selection-background-color: #ff4891; }}
        """)

        for btn in self.findChildren(QPushButton):
            if btn not in self._title_bar_buttons:
                btn.setStyleSheet(self.create_button("", "").styleSheet())

    def toggle_theme(self):
        new_theme = "dark" if self.theme_manager.current_theme() == "light" else "light"
        self.theme_manager.set_theme(new_theme)

    def change_language(self, index):
        self.language = "ru" if index == 0 else "en"
        self.translations = self.load_translations(self.language)
        self.setWindowTitle(self.translations["window_title"])

    def center_window(self):
        qr = self.frameGeometry()
        cp = QScreen.availableGeometry(QApplication.primaryScreen()).center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def showEvent(self, event):
        self.center_window()
        super().showEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._old_pos:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.move(self.pos() + delta)
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = None

    def paintEvent(self, event):
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillPath(path, QColor(self.theme_manager.theme_palette[self.theme]['bg']))
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))
        super().paintEvent(event)

    # Window handlers
    def open_qr_window(self): self._open = QRCodeWindow(self.language, self.theme_manager); self._open.show()
    def open_speedtest(self): self._open = SpeedTestWindow(self.language, self.theme_manager); self._open.show()
    def open_paint(self): self._open = PaintWindow(self.language, self.theme_manager); self._open.show()
    def open_pc_info(self): self._open = PCInfoWindow(self.language, self.theme_manager); self._open.show()
    def open_browser(self): self._open = Browser(app); self._open.show()
    def open_screenshot(self): self._open = ScreenshotWindow(self.language); self._open.show()
    def open_recorder(self): self._open = ScreenRecorderWindow(self.language); self._open.show()
    def open_screenshare(self): self._open = ScreenShareWindow(self.language); self._open.show()
    def open_translator(self): self._open = TranslatorWindow(self.language); self._open.show()
    def open_mic_window(self): self.create_simple_window("window_3_title", "window_3_label")
    def open_audio_window(self): self.create_simple_window("window_4_title", "window_4_label")
    def open_chat_window(self): self._open = AIChatWindow(language=self.language, theme_manager=self.theme_manager, download_manager=self.download_manager, current_directory=self.current_directory); self._open.show()

    def create_simple_window(self, title_key, label_key):
        window = QWidget()
        window.setWindowTitle(self.translations[title_key])
        QLabel(self.translations[label_key], window).setAlignment(Qt.AlignmentFlag.AlignCenter)
        window.setGeometry(200, 200, 300, 150)
        window.show()

if __name__ == "__main__":
    root_path = os.path.abspath(os.curdir)
    app = QApplication(sys.argv)
    window = MainWindow("ru", theme_manager, root_path)
    window.show()
    sys.exit(app.exec())