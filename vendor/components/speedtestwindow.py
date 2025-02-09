import socket
import json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QSpacerItem, QSizePolicy, QProgressBar, QMessageBox
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath, QScreen
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint, QThread, pyqtSignal
import speedtest
from .iconmanager import IconManager


class SpeedTestWorker(QThread):
    result = pyqtSignal(float, float)
    progress = pyqtSignal(int)

    def run(self):
        st = speedtest.Speedtest()
        try:
            st.get_servers()
            self.progress.emit(33)
            st.download()
            self.progress.emit(66)
            st.upload()
            self.progress.emit(100)
            results = st.results.dict()
            download_speed = results["download"] / 1_000_000
            upload_speed = results["upload"] / 1_000_000
            self.result.emit(download_speed, upload_speed)
        except speedtest.SpeedtestHTTPError as e:
            print(f"HTTP Error: {e}")
        except speedtest.SpeedtestCLIError as e:
            print(f"CLI Error: {e}")
        except Exception as e:
            print(f"Unexpected Error: {e}")

class SpeedTestWindow(QWidget):
    def __init__(self, language):
        super().__init__()
        self._old_pos = None
        self.language = language
        self.translations = self.load_translations(self.language)
        self.initUI()

    def load_translations(self, language):
        with open(f"{language}.json", "r", encoding="utf-8") as file:
            return json.load(file)

    def initUI(self):
        self.setWindowTitle(self.translations["speed_test_window_title"])
        self.setWindowIcon(IconManager.get_icon("speed_test"))
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

        #Макет для спидометра
        speedometer_layout = QVBoxLayout()

        #Спидометр
        self.speedometer = QLabel(self)
        self.speedometer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speedometer.setStyleSheet("font-size: 24px; font-family: 'Segoe UI';")
        speedometer_layout.addWidget(self.speedometer)

        #IP-адрес
        self.ip_label = QLabel(self)
        self.ip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ip_label.setStyleSheet("font-size: 16px; font-family: 'Segoe UI';")
        speedometer_layout.addWidget(self.ip_label)

        #Прогресс-бар
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        #Стиль для прогресс-бара
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 7px;
                text-align: center;
                background-color: #f0f0f0;
                font-family: 'Segoe UI';
                font-size: 12pt;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                                                   stop:0 rgba(66, 76, 230, 255),  /* Синий */
                                                   stop:0.5 rgba(174, 0, 238, 255), /* Фиолетовый */
                                                   stop:1 rgba(255, 72, 145, 255)); /* Розовый */
                border-radius: 5px;
            }
        """)

        speedometer_layout.addWidget(self.progress_bar)

        main_layout.addLayout(speedometer_layout)

        self.setLayout(main_layout)
        self.center_window(self)

        #Запуск измерения скорости
        self.worker = SpeedTestWorker()
        self.worker.result.connect(self.display_results)
        self.worker.progress.connect(self.update_progress)
        self.worker.start()

        #Получение IP-адреса
        self.ip_address = self.get_ip_address()
        self.ip_label.setText(f"{self.translations['ip_address']}: {self.ip_address}")

    def get_ip_address(self):
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception as e:
            print(f"Error reading IP address: {e}")
            return "Не удалось получить IP-адрес"

    def display_results(self, download_speed, upload_speed):
        self.speedometer.setText(f"{self.translations['download_speed']}: {download_speed:.2f} Mbps\n{self.translations['upload_speed']}: {upload_speed:.2f} Mbps")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

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