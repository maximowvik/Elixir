import json
import sys
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QFileDialog,
)
from PyQt6.QtGui import QPainter, QColor, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QPoint, QTimer, QDateTime
from PyQt6.QtGui import QScreen
import cv2
import numpy as np
import sounddevice as sd
from vendor.components.iconmanager import IconManager
import mss
import os

class ScreenRecorderWindow(QWidget):
    def __init__(self, theme_manager, translations: dict[str, str]):
        super().__init__()
        self._old_pos = None
        self.theme_manager = theme_manager
        self.translations = translations
        self.theme_manager.theme_changed.connect(self.update_theme)
        self.initUI()
        self.update_theme(self.theme_manager.current_theme())
        self.video_writer = None
        self.file_path = None
        self.audio_recording = False
        self.microphone_active = False

    def initUI(self):
        self.setWindowTitle(self.translations["screen_recorder_window_title"])
        self.setWindowIcon(IconManager.get_icon("screen_recorder"))
        if self.theme_manager.get_current_platform() == "windows":
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout()
        title_layout = QHBoxLayout()

        self.title_label = QLabel(self.translations["screen_recorder_window_title"])
        title_layout.addWidget(self.title_label)
        title_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        if self.theme_manager.get_current_platform() == "windows":
            for icon, handler in [("roll_up_button", self.showMinimized), ("button_close", self.close)]:
                btn = self.theme_manager.create_title_button(IconManager.get_images(icon), handler)
                title_layout.addWidget(btn)

        main_layout.addLayout(title_layout)

        self.start_button = QPushButton(self.translations["start_button"], self)
        self.start_button.clicked.connect(self.start_recording)
        main_layout.addWidget(self.start_button)

        self.stop_button = QPushButton(self.translations["stop_button"], self)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_recording)
        main_layout.addWidget(self.stop_button)

        self.microphone_button = QPushButton(self.translations["microphone_button"], self)
        self.microphone_button.setCheckable(True)
        self.microphone_button.clicked.connect(self.toggle_microphone)
        main_layout.addWidget(self.microphone_button)

        self.time_label = QLabel("00:00:00", self)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.time_label)

        self.setLayout(main_layout)
        self.center_window(self)

        self.recording = False
        self.elapsed_time = 0

    def start_recording(self):
        self.recording = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        directory = QFileDialog.getExistingDirectory(self, self.translations["select_directory_dialog_title"])
        if not directory:
            self.recording = False
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            return

        current_date_time = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss")
        self.file_path = os.path.join(directory, f"Elixir_record_video_{current_date_time}.mp4")

        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                height, width, _ = frame.shape
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                self.video_writer = cv2.VideoWriter(self.file_path, fourcc, 30.0, (width, height))
        except Exception as e:
            print(f"Ошибка инициализации записи видео: {e}")
            self.recording = False
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            return

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.record_frame)
        self.timer.start(33)

        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)

    def stop_recording(self):
        self.recording = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        self.timer.stop()
        self.time_timer.stop()

        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None

    def toggle_microphone(self, checked):
        self.microphone_active = checked
        if checked:
            self.start_microphone_recording()
        else:
            self.stop_microphone_recording()

    def start_microphone_recording(self):
        self.audio_recording = True
        self.audio_frames = []
        self.stream = sd.InputStream(callback=self.audio_callback)
        self.stream.start()

    def stop_microphone_recording(self):
        self.audio_recording = False
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()

    def audio_callback(self, indata, frames, time, status):
        if self.audio_recording:
            self.audio_frames.append(indata.copy())

    def record_frame(self):
        if not self.recording or self.video_writer is None:
            return

        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                self.video_writer.write(frame)
        except Exception as e:
            print(f"Ошибка захвата экрана: {e}")
            self.stop_recording()

    def update_time(self):
        self.elapsed_time += 1
        hours, remainder = divmod(self.elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{hours:02}:{minutes:02}:{seconds:02}"
        self.time_label.setText(time_str)

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
        title_height = 40
        return pos.y() <= title_height

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_in_title_bar(event.position().toPoint()):
            self._old_pos = event.globalPosition().toPoint()

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
            QTextEdit {{
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
                border: 1px solid {theme_vals['border']};
                border-radius: 10px;
                padding: 10px;
            }}
            QLabel {{
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
                border: 1px solid {theme_vals['border']};
                border-radius: 10px;
                padding: 10px;
                text-align:left
            }}
        """)

        self.time_label.setStyleSheet(f"""
            font-size: 16px;
            font-family: 'Segoe UI';
            color: {theme_vals['fg']};
        """)

        self.title_label.setStyleSheet(f"border:none")

    def closeEvent(self, event):
        self.stop_recording()
        event.accept()
