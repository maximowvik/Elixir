import darkdetect
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QSize
import platform

class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)  # Сигнал с новой темой: 'light' или 'dark'

    def __init__(self):
        super().__init__()
        self.theme_palette = {
            "light": {
                "bg": "#f8f9fa",       # Очень светлый серовато-белый
                "fg": "#495057",       # Мягкий темно-серый (не такой резкий, как #333)
                "border": "#dee2e6",   # Светло-серый с легким голубоватым оттенком
                "hover": "#e9ecef",     # Очень мягкий серый (легче, чем исходный)
                "pressed": "#d1d7dc",   # Немного темнее, но не слишком контрастный
                "bg_error": "#ff6b6b",  # Мягкий красный (менее агрессивный, чем #8B0000)
                "bg_warning": "#ffd166" # Теплый, но не кислотно-желтый
            },
            "dark": {
                "bg": "#2b2d42",       # Темно-синевато-серый (мягче, чем чистый #222)
                "fg": "#edf2f4",       # Светло-серый с легким голубым оттенком (не чистый белый)
                "border": "#4a4e69",    # Приглушенный серо-синий
                "hover": "#414563",    # Темный, но не черный
                "pressed": "#4a4e69",   # Чуть светлее, чем hover
                "bg_error": "#ef9a9a",  # Пастельно-красный (мягче, чем #FA8072)
                "bg_warning": "#fff3b0" # Светло-желтый (не такой яркий, как #F0E68C)
            }
        }
        self._theme = self.get_system_theme()
        
        # Таймер для периодической проверки изменения темы
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_system_theme)  # Проверяем каждую секунду
        self.timer.start(1000)  # Интервал в миллисекундах (1000 ms = 1 секунда)

    def set_theme(self, theme: str):
        if theme != self._theme:
            self._theme = theme
            self.theme_changed.emit(theme)

    def current_theme(self) -> str:
        return self._theme
    
    def get_system_theme(self):
        try:
            return str(darkdetect.theme()).lower()
        except:
            return "light"

    def check_system_theme(self):
        new_theme = self.get_system_theme()
        if new_theme != self._theme:
            self.set_theme(new_theme)

    def get_current_platform(self):
        return str(platform.system()).lower()

    def create_title_button(self, icon_name, slot):
        btn = QPushButton()
        btn.setIcon(QIcon(QPixmap(icon_name)))
        btn.setIconSize(QSize(35, 35))
        btn.setFixedSize(40, 40)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 10px;
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

