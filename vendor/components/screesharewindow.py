import socket
import json
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint, pyqtSignal, QTimer, pyqtSlot
from PyQt6.QtGui import QScreen
import cv2
import numpy as np
from flask import Flask, Response
import threading
import mss
import time
from werkzeug.serving import make_server
from .iconmanager import IconManager

class ScreenShareWindow(QWidget):
    stop_signal = pyqtSignal()

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
        self.setWindowTitle(self.translations["screen_share_window_title"])
        self.setWindowIcon(IconManager.get_icon("screen_share"))
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

        #Кнопка начала трансляции
        self.start_button = QPushButton(self.translations["start_button"], self)
        self.start_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.start_button.clicked.connect(self.start_streaming)
        main_layout.addWidget(self.start_button)

        #Кнопка остановки трансляции
        self.stop_button = QPushButton(self.translations["stop_button"], self)
        self.stop_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_streaming)
        main_layout.addWidget(self.stop_button)

        #Метка для отображения ссылки
        self.url_label = QLabel("", self)
        self.url_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.url_label.setStyleSheet("font-size: 12px; font-family: 'Segoe UI';")
        main_layout.addWidget(self.url_label)

        #Кнопка для копирования ссылки
        self.copy_button = QPushButton(self.translations["copy_button"], self)
        self.copy_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_url)
        main_layout.addWidget(self.copy_button)

        #Уведомление о копировании
        self.notification_label = QLabel(self.translations["notification_label"], self)
        self.notification_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notification_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 12pt; color: green;")
        self.notification_label.hide()
        main_layout.addWidget(self.notification_label)

        self.setLayout(main_layout)
        self.center_window(self)

        #Инициализация переменных для трансляции
        self.streaming = False
        self.server_running = False
        self.app = Flask(__name__)
        self.app.add_url_rule('/video_feed', 'video_feed', self.video_feed)
        self.server = None
        self.stop_event = threading.Event()

        #Подключение сигнала для остановки сервера
        self.stop_signal.connect(self.stop_server)

    def start_streaming(self):
        self.streaming = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        #Запуск веб-сервера в отдельном потоке
        self.server = make_server('0.0.0.0', 5000, self.app)
        self.thread = threading.Thread(target=self.run_server)
        self.thread.start()

        #Генерация ссылки
        self.stream_url = f"http://{socket.gethostbyname(socket.gethostname())}:5000/video_feed"
        self.url_label.setText(f"{self.translations['stream_url']}: {self.stream_url}")
        self.copy_button.setEnabled(True)

    @pyqtSlot()
    def stop_server(self):
        if self.server_running:
            self.stop_event.set()
            self.server.shutdown()
            self.thread.join()

    def stop_streaming(self):
        self.streaming = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        #Остановка веб-сервера
        self.stop_signal.emit()

        #Очистка ссылки
        self.url_label.setText("")
        self.copy_button.setEnabled(False)

    def run_server(self):
        self.server_running = True
        self.server.serve_forever()
        self.server_running = False

    def video_feed(self):
        def generate():
            while not self.stop_event.is_set():
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    screenshot = sct.grab(monitor)
                    frame = np.array(screenshot)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    ret, jpeg = cv2.imencode('.jpg', frame)
                    if not ret:
                        continue
                    frame = jpeg.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
                    time.sleep(1 / 30)  # Ensure 30 FPS

        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

    def copy_url(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.stream_url)
        self.notification_label.show()
        QTimer.singleShot(2000, self.notification_label.hide)

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
