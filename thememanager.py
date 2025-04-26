import winreg
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

class ThemeManager(QObject):
    theme_changed = pyqtSignal(str)  # Сигнал с новой темой: 'light' или 'dark'

    def __init__(self):
        super().__init__()
        self.theme_palette = {
            "light": {"bg": "#ffffff", "fg": "#333", "border": "#ccc", "hover": "#e0e0e0", "pressed": "#d0d0d0"},
            "dark": {"bg": "#222222", "fg": "#fff", "border": "#555", "hover": "#444", "pressed": "#555"}
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
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                return "light" if winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 1 else "dark"
        except:
            return "light"

    def check_system_theme(self):
        new_theme = self.get_system_theme()
        if new_theme != self._theme:
            self.set_theme(new_theme)
