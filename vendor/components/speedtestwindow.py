import socket
import json
import threading
import speedtest

from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QSpacerItem, QSizePolicy, QProgressBar, QApplication
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint, pyqtSignal, QObject

from .iconmanager import IconManager

class SpeedTestWorker(QObject):
    result = pyqtSignal(float, float)
    progress = pyqtSignal(int, str)
    error = pyqtSignal(str)

    def run(self):
        try:
            st = speedtest.Speedtest()
            self.progress.emit(20, "Поиск сервера...")
            st.get_best_server()

            self.progress.emit(50, "Скорость загрузки...")
            download = st.download() / 1_000_000

            self.progress.emit(75, "Скорость отдачи...")
            upload = st.upload() / 1_000_000

            self.progress.emit(100, "Готово")
            self.result.emit(download, upload)

        except Exception as e:
            self.error.emit(str(e))

class SpeedTestWindow(QWidget):
    def __init__(self, language, theme_manager):
        super().__init__()
        self.language = language
        self.theme_manager = theme_manager
        self.translations = self.load_translations(language)
        self._last_results = (0, 0)
        self._old_pos = None

        self.theme_manager.theme_changed.connect(self.update_theme)

        self.setup_ui()
        self.update_theme(self.theme_manager.current_theme())

    def load_translations(self, lang):
        with open(f"vendor/core/language/{lang}.json", encoding="utf-8") as f:
            return json.load(f)

    def setup_ui(self):
        self.setWindowTitle(self.translations["speed_test_window_title"])
        self.setWindowIcon(IconManager.get_icon("speed_test"))
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        # Верхняя панель
        if self.theme_manager.get_current_platform() == "windows":
            layout.addLayout(self.create_title_bar())

        # Центральные элементы
        self.speedometer = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.speedometer.setStyleSheet("font-size: 18px; font-family: 'Segoe UI'; text-align: left;")
        layout.addWidget(self.speedometer)

        self.ip_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.ip_label.setStyleSheet("font-size: 16px; font-family: 'Segoe UI'; text-align:left;")
        layout.addWidget(self.ip_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

        # Получение IP
        self.ip_address = self.get_ip_address()
        self.ip_label.setText(f"{self.translations['ip_address']}: {self.ip_address}")

        # Запуск теста
        self.worker = SpeedTestWorker()
        self.worker.result.connect(self.display_results)
        self.worker.progress.connect(self.update_progress)
        self.worker.error.connect(self.display_error)

        self.worker_thread = threading.Thread(target=self.worker.run, daemon=True)
        self.worker_thread.start()

        self.center_window()

    def create_title_bar(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        title_bar = QHBoxLayout()
        title_bar.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        for icon, slot in [(IconManager.get_images("roll_up_button"), self.showMinimized), (IconManager.get_images("button_close"), self.close)]:
            btn = self.create_title_button(icon, slot)
            title_bar.addWidget(btn)

        return title_bar

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

    def update_progress(self, value, text):
        self.progress_bar.setValue(value)
        self.speedometer.setText(text)

    def display_results(self, d, u):
        self._last_results = (d, u)
        self.speedometer.setText(
            f"{self.translations['download_speed']}: {d:.2f} Mbps\n"
            f"{self.translations['upload_speed']}: {u:.2f} Mbps"
        )

    def display_error(self, message):
        self.speedometer.setText(f"{self.translations['error']}: {message}")
        self.progress_bar.setValue(0)

    def get_ip_address(self):
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "N/A"

    def center_window(self):
        screen = QApplication.primaryScreen().availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(screen.center())
        self.move(frame.topLeft())

    def update_language(self, lang):
        self.translations = self.load_translations(lang)
        self.setWindowTitle(self.translations["speed_test_window_title"])
        self.ip_label.setText(f"{self.translations['ip_address']}: {self.ip_address}")
        self.display_results(*self._last_results)

    def update_theme(self, theme):
        theme_vals = self.theme_manager.theme_palette[theme]
        bg = theme_vals["bg"]
        fg = theme_vals["fg"]
        bar = theme_vals["border"]

        self.setStyleSheet(f"""
            QWidget {{ background-color: {bg}; color: {fg}; }}
            QProgressBar {{
                border: 2px solid {bar}; border-radius: 7px;
                background-color: {bg};
                height: 30px;
                border-radius: 10px;
                text-align: center;
                font-family: 'Segoe UI';
                font-size: 10pt;
                color: {fg};
            }}
            QProgressBar::chunk {{
                border-radius: 9px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6a5acd,
                    stop:0.5 #9b59b6,
                    stop:1 #e74c3c
                );
            }}
        """)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        p.fillPath(path, QColor(self.palette().color(self.backgroundRole())))
        p.setClipPath(path)
        super().paintEvent(event)

    def _is_in_title_bar(self, pos):
        # Получаем геометрию заголовка
        title_height = 40  # Высота заголовка
        return pos.y() <= title_height

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            # Проверяем, находится ли курсор в области заголовка
            if self._is_in_title_bar(e.position().toPoint()):
                self._old_pos = e.globalPosition().toPoint()
            else:
                self._old_pos = None

    def mouseMoveEvent(self, e):
        if self._old_pos:
            delta = e.globalPosition().toPoint() - self._old_pos
            self.move(self.pos() + delta)
            self._old_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._old_pos = None

__all__ = ["SpeedTestWindow"]
