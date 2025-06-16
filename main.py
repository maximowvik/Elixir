from PyQt6.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QGridLayout,
                             QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy, QComboBox)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath, QScreen
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint
from PyQt6.QtGui import QRegion
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
from vendor.components.mic import AudioRecorder
from vendor.components.mixerwindow import VolumeMixer
from thememanager import ThemeManager

import sys
import os
import json

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
        self._open_windows = {}  # Словарь для хранения открытых окон
        self._window_states = {}  # Словарь для хранения состояний окон

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
        if (self.theme_manager.get_current_platform() == "windows"):
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        title_bar = QHBoxLayout()

        self.language_combo = QComboBox()
        self.language_combo.addItem(QIcon("pic/ru.png"), "Русский")
        self.language_combo.addItem(QIcon("pic/en.png"), "English")
        self.language_combo.setFixedWidth(120)
        self.language_combo.currentIndexChanged.connect(self.change_language)
        title_bar.addWidget(self.language_combo)

        title_bar.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding))
        if (self.theme_manager.get_current_platform() == "windows"):
            for icon, handler in [("change_theme", self.toggle_theme), ("roll_up_button", self.showMinimized), ("button_close", self.close)]:
                btn = self.theme_manager.create_title_button(IconManager.get_images(icon), handler)
                self._title_bar_buttons.append(btn)
                title_bar.addWidget(btn)
        else:
            btn = self.theme_manager.create_title_button(IconManager.get_images("change_theme") if 'pic' not in "change_theme" else "change_theme", self.toggle_theme)
            self._title_bar_buttons.append(btn)
            title_bar.addWidget(btn)

        return title_bar

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
        if self._old_pos:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.move(self.pos() + delta)
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        p.fillPath(path, QColor(self.palette().color(self.backgroundRole())))
        p.setClipPath(path)
        super().paintEvent(event)

    def _cleanup_window(self, window_id):
        """Очистка ресурсов окна при его закрытии"""
        if window_id in self._open_windows:
            window = self._open_windows[window_id]
            if hasattr(window, 'cleanup'):
                window.cleanup()
            del self._open_windows[window_id]
            if window_id in self._window_states:
                del self._window_states[window_id]

    def _window_closed(self, window_id):
        """Обработчик закрытия окна"""
        self._cleanup_window(window_id)

    def _create_window(self, window_id, window_class, *args, **kwargs):
        """Создание нового окна с обработкой закрытия"""
        if window_id not in self._open_windows:
            window = window_class(*args, **kwargs)
            window.closeEvent = lambda event: self._handle_window_close(event, window_id)
            self._open_windows[window_id] = window
            self._window_states[window_id] = True
            window.show()
            return window
        return self._open_windows[window_id]

    def _handle_window_close(self, event, window_id):
        """Обработчик события закрытия окна"""
        self._window_states[window_id] = False
        self._cleanup_window(window_id)
        event.accept()

    def closeEvent(self, event):
        # Останавливаем все открытые окна
        for window_id in list(self._open_windows.keys()):
            self._cleanup_window(window_id)

        # Останавливаем таймер темы
        self.theme_manager.timer.stop()

        # Останавливаем менеджер загрузок
        if hasattr(self.download_manager, 'stop_all'):
            self.download_manager.stop_all()

        # Принимаем событие закрытия
        event.accept()

        # Завершаем приложение
        QApplication.quit()

    # Модифицируем методы открытия окон
    def open_qr_window(self):
        self._create_window('qr', QRCodeWindow, self.theme_manager, self.translations)

    def open_speedtest(self):
        self._create_window('speedtest', SpeedTestWindow, self.theme_manager, self.translations)

    def open_paint(self):
        self._create_window('paint', PaintWindow, self.theme_manager, self.translations)

    def open_pc_info(self):
        self._create_window('pcinfo', PCInfoWindow, self.theme_manager, self.translations)

    def open_browser(self):
        self._create_window('browser', Browser, self.theme_manager, self.translations)

    def open_screenshot(self):
        self._create_window('screenshot', ScreenshotWindow, self.theme_manager, self.translations)

    def open_recorder(self):
        self._create_window('recorder', ScreenRecorderWindow, self.theme_manager, self.translations)

    def open_screenshare(self):
        self._create_window('screenshare', ScreenShareWindow, self.theme_manager, self.translations)

    def open_translator(self):
        self._create_window('translator', TranslatorWindow, self.theme_manager, self.translations)

    def open_chat_window(self):
        self._create_window('chat', AIChatWindow,
            translations=self.translations,
            theme_manager=self.theme_manager,
            download_manager=self.download_manager,
            current_directory=self.current_directory
        )

    def open_mic_window(self): 
        self._create_window("audio_record", AudioRecorder, self.theme_manager, self.translations)
    def open_audio_window(self): 
        self._create_window("mixer_value_audio", VolumeMixer, self.theme_manager, self.translations)

    def create_simple_window(self, title_key, label_key):
        window_id = f"simple_{title_key}"
        if window_id not in self._open_windows:
            window = QWidget()
            window.setWindowTitle(self.translations[title_key])
            QLabel(self.translations[label_key], window).setAlignment(Qt.AlignmentFlag.AlignCenter)
            window.setGeometry(200, 200, 300, 150)
            window.closeEvent = lambda event: self._handle_window_close(event, window_id)
            self._open_windows[window_id] = window
            self._window_states[window_id] = True
            window.show()

if __name__ == "__main__":
    os.environ["QTWEBENGINE_DISABLE_GPU"] = "1"
    root_path = os.path.abspath(os.curdir)
    app = QApplication(sys.argv)
    window = MainWindow("ru", theme_manager, root_path)
    window.show()
    sys.exit(app.exec())
