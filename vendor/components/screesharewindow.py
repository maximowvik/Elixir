import socket
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
from PyQt6.QtGui import QPainter, QColor, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QPoint, pyqtSignal, QTimer, pyqtSlot
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

    def __init__(self, theme_manager, translations: dict[str, str]):
        super().__init__()
        self._old_pos = None
        self.theme_manager = theme_manager
        self.translations = translations
        
        # Подписка на сигнал изменения темы
        self.theme_manager.theme_changed.connect(self.update_theme)
        
        # Инициализация переменных для трансляции
        self.streaming = False
        self.server = None
        self.server_thread = None
        self.active_clients = []
        self.server_lock = threading.Lock()
        self.stop_event = threading.Event()

        self.initUI()
        self.update_theme(self.theme_manager.current_theme())

    def initUI(self):
        self.setWindowTitle(self.translations["screen_share_window_title"])
        self.setWindowIcon(IconManager.get_icon("screen_share"))
        
        if self.theme_manager.get_current_platform() == "windows":
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Title bar
        title_layout = QHBoxLayout()
        self.title_label = QLabel(self.translations["screen_share_window_title"])
        title_layout.addWidget(self.title_label)
        title_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        if self.theme_manager.get_current_platform() == "windows":
            for icon, handler in [("roll_up_button", self.showMinimized), ("button_close", self.close)]:
                btn = self.theme_manager.create_title_button(IconManager.get_images(icon), handler)
                title_layout.addWidget(btn)

        main_layout.addLayout(title_layout)

        # Start button
        self.start_button = QPushButton(self.translations["start_button"], self)
        self.start_button.clicked.connect(self.start_streaming)
        main_layout.addWidget(self.start_button)

        # Stop button
        self.stop_button = QPushButton(self.translations["stop_button"], self)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_streaming)
        main_layout.addWidget(self.stop_button)

        # URL label
        self.url_label = QLabel("", self)
        self.url_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.url_label)

        # Copy button
        self.copy_button = QPushButton(self.translations["copy_button"], self)
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_url)
        main_layout.addWidget(self.copy_button)

        # Notification label
        self.notification_label = QLabel(self.translations["notification_label"], self)
        self.notification_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notification_label.hide()
        main_layout.addWidget(self.notification_label)

        self.setLayout(main_layout)
        self.center_window()

        # Подключение сигнала для остановки сервера
        self.stop_signal.connect(self.stop_server)

    def start_streaming(self):
        self.streaming = True
        self.stop_event.clear()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # Очищаем список клиентов
        with self.server_lock:
            self.active_clients = []
        
        # Инициализация Flask приложения
        self.app = Flask(__name__)
        self.app.add_url_rule('/video_feed', 'video_feed', self.video_feed)
        
        # Создание сервера с настройками
        self.server = make_server('0.0.0.0', 5000, self.app, threaded=True)
        self.server.daemon_threads = True
        
        # Запуск сервера в отдельном потоке
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()
        
        # Генерация URL для трансляции
        self.stream_url = f"http://{socket.gethostbyname(socket.gethostname())}:5000/video_feed"
        self.url_label.setText(f"{self.translations['stream_url']}: {self.stream_url}")
        self.copy_button.setEnabled(True)

    def video_feed(self):
        def generate():
            # Регистрируем нового клиента
            with self.server_lock:
                self.active_clients.append(1)
            
            sct = mss.mss()
            try:
                while self.streaming and not self.stop_event.is_set():
                    monitor = sct.monitors[1]
                    screenshot = sct.grab(monitor)
                    frame = np.array(screenshot)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                    if not ret:
                        continue
                    frame = jpeg.tobytes()
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
                    time.sleep(1/30)
            except (GeneratorExit, ConnectionError):
                # Клиент отключился
                pass
            finally:
                # Удаляем клиента из списка
                with self.server_lock:
                    if self.active_clients:
                        self.active_clients.pop()
                sct.close()

        response = Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
        response.timeout = 5
        return response

    def run_server(self):
        try:
            self.server.serve_forever()
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.server = None

    @pyqtSlot()
    def stop_server(self):
        if self.server:
            # Устанавливаем флаги остановки
            self.streaming = False
            self.stop_event.set()
            
            # Принудительно разрываем соединения
            with self.server_lock:
                self.active_clients = []
            
            # Останавливаем сервер
            try:
                if hasattr(self.server, 'shutdown'):
                    self.server.shutdown()
                else:
                    # Альтернативный способ для Werkzeug
                    self.server._BaseServer__shutdown_request = True
                
                # Закрываем сокет
                if hasattr(self.server, 'socket'):
                    self.server.socket.close()
            except Exception as e:
                print(f"Error stopping server: {e}")
            finally:
                self.server = None
                
            # Ждем завершения потока сервера
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=1)

    def stop_streaming(self):
        self.streaming = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # Остановка сервера через сигнал
        self.stop_signal.emit()
        
        # Очистка URL
        self.url_label.setText("")
        self.copy_button.setEnabled(False)

    def copy_url(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.stream_url)
        self.notification_label.show()
        QTimer.singleShot(2000, self.notification_label.hide)

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        qr = self.frameGeometry()
        cp = screen.center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.fillPath(path, QColor(self.theme_manager.theme_palette[self.theme_manager.current_theme()]['bg']))
        painter.setClipPath(path)
        super().paintEvent(event)

    def _is_in_title_bar(self, pos):
        title_height = 40
        return pos.y() <= title_height

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
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
                background-color: {theme_vals['hover']};
            }}
            QPushButton:pressed {{
                background-color: {theme_vals['pressed']};
            }}
            QPushButton:disabled {{
                background: {theme_vals['hover']};
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
                text-align: left;
            }}
            QComboBox {{
                height: 25px; 
                background: {theme_vals['hover']}; 
                border: 1px solid {theme_vals['border']}; 
                color: {theme_vals['fg']}; 
                padding: 10px; 
                border-radius: 8px;
            }}
            QComboBox:hover {{ background: {theme_vals['bg']}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{ 
                background: {theme_vals['bg']}; 
                color: {theme_vals['fg']}; 
                selection-background-color: #ff4891; 
            }}
        """)
        
        self.url_label.setStyleSheet(f"""
            font-size: 12px;
            font-family: 'Segoe UI';
            color: {theme_vals['fg']};
            border: none;
        """)
        
        self.notification_label.setStyleSheet(f"""
            font-family: 'Segoe UI';
            font-size: 12pt;
            color: {theme_vals['fg']};
            border: none;
        """)
        
        self.title_label.setStyleSheet("border: none;")

    def closeEvent(self, event):
        if self.streaming:
            self.stop_streaming()
        event.accept()