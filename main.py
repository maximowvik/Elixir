import os
import sys
import winreg
import json
from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QGridLayout, 
                            QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy, QComboBox)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint
from PyQt6.QtGui import QScreen, QBitmap, QRegion
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

if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._old_pos = None
        self.language = "ru"
        self._title_bar_buttons = []
        self.translations = self.load_translations(self.language)
        self.init_ui()
        self.setFixedSize(QSize(370, 700))

    def load_translations(self, lang):
        with open(f"vendor/core/language/{lang}.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def init_ui(self):
        self.setWindowTitle(self.translations["window_title"])
        self.setWindowIcon(IconManager.get_icon("main"))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        self.theme = self.get_system_theme()
        self.apply_theme(self.theme)
        
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

        change_theme = self.create_title_button(IconManager.get_images("change_theme"), self.toggle_theme)
        minimize_btn = self.create_title_button("pic/minus.png", self.showMinimized)
        close_btn = self.create_title_button(IconManager.get_images("button_close"), self.close)

        self._title_bar_buttons.extend([change_theme, minimize_btn, close_btn])

        title_bar.addWidget(change_theme)
        title_bar.addWidget(minimize_btn)
        title_bar.addWidget(close_btn)

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
        
        for i, (text, icon_name, handler) in enumerate(buttons):
            btn = self.create_button(text, icon_name)
            btn.clicked.connect(handler)
            grid.addWidget(btn, i//3, i%3)
            
        return grid

    def create_button(self, text, icon_name):
        btn = QPushButton()
        btn.setIcon(QIcon(IconManager.get_images(icon_name)))
        btn.setIconSize(QSize(64, 64))
        btn.setFixedSize(QSize(100, 100))
        btn.setStyleSheet("""
            QPushButton {
                background: %button_bg%;
                border-radius: 10px;
                padding: 15px;
                color: %text_color%;
                font-size: 14px;
                border: 0px solid %border_color%;
                text-align: center;
            }
            QPushButton:hover {
                background: %button_hover%;
            }
            QPushButton:pressed {
                background: %button_pressed%;
            }
        """.replace("%button_bg%", "#ffffff" if self.theme == "light" else "#222222") #f0f0f0, 333
          .replace("%text_color%", "#333" if self.theme == "light" else "#fff")
          .replace("%border_color%", "#ccc" if self.theme == "light" else "#555")
          .replace("%button_hover%", "#e0e0e0" if self.theme == "light" else "#444")
          .replace("%button_pressed%", "#d0d0d0" if self.theme == "light" else "#555"))
        return btn
    
    def button_style(self):
        return """
            QPushButton {
                background: %(bg)s;
                border-radius: 10px;
                padding: 15px;
                color: %(fg)s;
                font-size: 14px;
                border: 0px solid %(border)s;
                text-align: center;
            }
            QPushButton:hover {
                background: %(hover)s;
            }
            QPushButton:pressed {
                background: %(pressed)s;
            }
        """ % {
            "bg": "#ffffff" if self.theme == "light" else "#222222",
            "fg": "#333" if self.theme == "light" else "#fff",
            "border": "#ccc" if self.theme == "light" else "#555",
            "hover": "#e0e0e0" if self.theme == "light" else "#444",
            "pressed": "#d0d0d0" if self.theme == "light" else "#555",
        }


    def get_system_theme(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                return "light" if winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 1 else "dark"
        except:
            return "light"

    def apply_theme(self, theme):
        self.theme = theme
        bg_color = "#ffffff" if theme == "light" else "#222222"
        text_color = "#333333" if theme == "light" else "#ffffff"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                color: {text_color};
                font-family: 'Segoe UI';
                font-size: 12pt;
            }}

            QComboBox {{
                background: {"#f0f0f0" if theme == "light" else "#333"};
                border: 1px solid {"#ccc" if theme == "light" else "#555"};
                color: {"#333" if theme == "light" else "#fff"};
                padding: 5px 10px;
                border-radius: 8px;
                min-width: 120px;
            }}
            QComboBox:hover {{
                background: {"#e0e0e0" if theme == "light" else "#444"};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background: {"#ffffff" if theme == "light" else "#222"};
                color: {"#000000" if theme == "light" else "#ffffff"};
                selection-background-color: #ff4891;
            }}
        """)

        # Обновляем стиль всех остальных кнопок, кроме кнопок заголовка
        for btn in self.findChildren(QPushButton):
            if btn not in self._title_bar_buttons:
                btn.setStyleSheet(self.button_style())

    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        self.apply_theme(self.theme)

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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        painter.fillPath(path, QColor("#ffffff" if self.theme == "light" else "#222222"))
        painter.setClipPath(path)
        super().paintEvent(event)

    def resizeEvent(self, event):
        radius = 10
        pixmap = QBitmap(self.size())
        pixmap.clear()

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.GlobalColor.color1)
        painter.setPen(Qt.PenStyle.NoPen)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), radius, radius)
        painter.drawPath(path)
        painter.end()

        self.setMask(QRegion(pixmap))
        super().resizeEvent(event)

    # Window handlers
    def open_qr_window(self): 
        self.qr_window = QRCodeWindow(self.language)
        self.qr_window.show()

    def open_speedtest(self): 
        self.speed_window = SpeedTestWindow(self.language)
        self.speed_window.show()

    def open_paint(self): 
        self.paint_window = PaintWindow(self.language)
        self.paint_window.show()

    def open_pc_info(self): 
        self.pc_info_window = PCInfoWindow(self.language)
        self.pc_info_window.show()

    def open_browser(self): 
        self.browser = Browser(app)
        self.browser.show()

    def open_screenshot(self): 
        self.screenshot_window = ScreenshotWindow(self.language)
        self.screenshot_window.show()

    def open_recorder(self): 
        self.recorder_window = ScreenRecorderWindow(self.language)
        self.recorder_window.show()

    def open_screenshare(self): 
        self.screenshare_window = ScreenShareWindow(self.language)
        self.screenshare_window.show()

    def open_translator(self): 
        self.translator_window = TranslatorWindow(self.language)
        self.translator_window.show()
    
    def open_mic_window(self): 
        self.create_simple_window("window_3_title", "window_3_label")
    
    def open_audio_window(self): 
        self.create_simple_window("window_4_title", "window_4_label")
    
    def open_chat_window(self): 
        self.create_simple_window("window_9_title", "window_9_label")
    
    def create_simple_window(self, title_key, label_key):
        window = QWidget()
        window.setWindowTitle(self.translations[title_key])
        QLabel(self.translations[label_key], window).setAlignment(Qt.AlignmentFlag.AlignCenter)
        window.setGeometry(200, 200, 300, 150)
        window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())