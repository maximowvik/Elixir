import sys
import json
import wave
import pyaudio
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QFileDialog, QVBoxLayout,
    QHBoxLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPoint
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QFont
from .iconmanager import IconManager


class AudioRecorder(QWidget):
    def __init__(self, language, theme_manager):
        super().__init__()
        self.theme_manager = theme_manager
        self.language = language
        self.translations = self.load_translations(language)
        self._last_results = (0, 0)
        self._old_pos = None

        self.theme_manager.theme_changed.connect(self.update_theme)

        self.init_audio()
        self.init_ui()
        self.update_theme(self.theme_manager.current_theme())
        
    def load_translations(self, lang):
        with open(f"vendor/core/language/{lang}.json", encoding="utf-8") as f:
            return json.load(f)

    def init_audio(self):
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1024
        self.frames = []
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.seconds = 0

    def init_ui(self):
        self.setFixedSize(400, 250)
        self.setWindowTitle(self.translations["audio_record"])
        self.setWindowIcon(IconManager.get_icon("audio_recording"))
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        self.init_title_bar()

        self.timer_label = QLabel("00:00", self)
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setFont(QFont("Segoe UI", 16))
        self.main_layout.addWidget(self.timer_label)

        self.status_label = QLabel("", self)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.main_layout.addWidget(self.status_label)

        self.record_btn = QPushButton(self.translations["start_recording"])
        self.record_btn.clicked.connect(self.start_recording)

        self.stop_btn = QPushButton(self.translations["stop_recording"])
        self.stop_btn.clicked.connect(self.stop_recording)
        self.stop_btn.setEnabled(False)

        self.record_btn.setFont(QFont("Segoe UI", 12))
        self.stop_btn.setFont(QFont("Segoe UI", 12))

        self.main_layout.addWidget(self.record_btn)
        self.main_layout.addWidget(self.stop_btn)

    def init_title_bar(self):
        if (self.theme_manager.get_current_platform() == "windows"):
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        title_layout = QHBoxLayout()
        self.title_label = QLabel(self.translations["audio_record"])
        title_layout.addWidget(self.title_label)
        title_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        if (self.theme_manager.get_current_platform() == "windows"):
            for icon, handler in [("roll_up_button", self.showMinimized), ("button_close", self.close)]:
                btn = self.theme_manager.create_title_button(IconManager.get_images(icon), handler)
                title_layout.addWidget(btn)
            
        self.main_layout.addLayout(title_layout)

    def update_theme(self, theme):
        theme_vals = self.theme_manager.theme_palette[theme]
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme_vals['bg']};
                color: {theme_vals['fg']};
            }}
            QPushButton {{
                background-color: {theme_vals['bg']};
                color: {theme_vals['fg']};
                border-radius: 6px;
                border: 1px solid {theme_vals['border']};
                padding: 10px;
            }}
            QPushButton:hover {{ background: {theme_vals['hover']}; }}
            QPushButton:pressed {{ background: {theme_vals['pressed']}; }}
            QPushButton:disabled {{ background: {theme_vals['pressed']}; }}
        """)

    def start_recording(self):
        self.frames = []
        self.stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
            stream_callback=self.callback
        )
        self.stream.start_stream()

        self.is_recording = True
        self.seconds = 0
        self.timer_label.setText("00:00")
        self.timer.start(1000)

        self.status_label.setText("🔴 " + self.translations["recording_started"])
        # QTimer.singleShot(2000, lambda: self.status_label.setText(""))

        self.record_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def callback(self, in_data, frame_count, time_info, status):
        if self.is_recording:
            self.frames.append(in_data)
        return (in_data, pyaudio.paContinue)

    def update_timer(self):
        self.seconds += 1
        minutes = self.seconds // 60
        seconds = self.seconds % 60
        self.timer_label.setText(f"{minutes:02}:{seconds:02}")

    def stop_recording(self):
        self.is_recording = False
        self.timer.stop()
        self.status_label.setText("")

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        self.save_audio_file()

    def save_audio_file(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, 
            self.translations["save_recording"],
            "recording.wav", 
            "Wave Files (*.wav)"
        )
        if file_name:
            if not file_name.endswith(".wav"):
                file_name += ".wav"

            wf = wave.open(file_name, 'wb')
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(b''.join(self.frames))
            wf.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.fillPath(path, QColor(self.theme_manager.theme_palette[self.theme_manager.current_theme()]["bg"]))
        painter.setClipPath(path)
        super().paintEvent(event)

    def _is_in_title_bar(self, pos):
        return pos.y() <= 40  # Высота title bar

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_in_title_bar(event.position().toPoint()):
                self._old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._old_pos:
            delta = QPoint(event.globalPosition().toPoint() - self._old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = None

    def closeEvent(self, event):
        if self.is_recording:
            self.stop_recording()
        self.audio.terminate()
        event.accept()