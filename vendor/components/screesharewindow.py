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
    QSizePolicy,
    QComboBox
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

        for icon, slot in [(IconManager.get_images("roll_up_button"), self.showMinimized),
                           (IconManager.get_images("button_close"), self.close)]:
            btn = self.create_title_button(icon, slot)
            title_layout.addWidget(btn)

        main_layout.addLayout(title_layout)

        #Кнопка начала трансляции
        self.start_button = QPushButton(self.translations["start_button"], self)
        self.start_button.clicked.connect(self.start_streaming)
        main_layout.addWidget(self.start_button)

        #Кнопка остановки трансляции
        self.stop_button = QPushButton(self.translations["stop_button"], self)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_streaming)
        main_layout.addWidget(self.stop_button)

        #Метка для отображения ссылки
        self.url_label = QLabel("", self)
        self.url_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.url_label)

        #Кнопка для копирования ссылки
        self.copy_button = QPushButton(self.translations["copy_button"], self)
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_url)
        main_layout.addWidget(self.copy_button)

        #Уведомление о копировании
        self.notification_label = QLabel(self.translations["notification_label"], self)
        self.notification_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        self.start_button.setStyleSheet(f"""
            background: {theme_vals['bg']};
            color: {theme_vals['fg']};
            border: 1px solid {theme_vals['border']};
            border-radius: 10px;
            padding: 10px;
            font-family: 'Segoe UI';
            font-size: 12pt;
        """)
        
        self.stop_button.setStyleSheet(f"""
            background: {theme_vals['bg']};
            color: {theme_vals['fg']};
            border: 1px solid {theme_vals['border']};
            border-radius: 10px;
            padding: 10px;
            font-family: 'Segoe UI';
            font-size: 12pt;
        """)
        
        self.url_label.setStyleSheet(f"""
            font-size: 12px;
            font-family: 'Segoe UI';
            color: {theme_vals['fg']};
        """)
        
        self.copy_button.setStyleSheet(f"""
            background: {theme_vals['bg']};
            color: {theme_vals['fg']};
            border: 1px solid {theme_vals['border']};
            border-radius: 10px;
            padding: 10px;
            font-family: 'Segoe UI';
            font-size: 12pt;
        """)
        
        self.notification_label.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: 12pt;
            color: {theme_vals['fg']};
        """)
