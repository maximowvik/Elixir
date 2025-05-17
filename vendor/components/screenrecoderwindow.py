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
    QFileDialog,
    QComboBox
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint, QTimer
from PyQt6.QtGui import QScreen
import pyautogui
import cv2
import numpy as np
from vendor.components.iconmanager import IconManager

class ScreenRecorderWindow(QWidget):
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
        self.setWindowTitle(self.translations["screen_recorder_window_title"])
        self.setWindowIcon(IconManager.get_icon("screen_recorder"))
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

        #Кнопка начала записи
        self.start_button = QPushButton(self.translations["start_button"], self)
        self.start_button.clicked.connect(self.start_recording)
        main_layout.addWidget(self.start_button)

        #Кнопка остановки записи
        self.stop_button = QPushButton(self.translations["stop_button"], self)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_recording)
        main_layout.addWidget(self.stop_button)

        #Метка для отображения времени записи
        self.time_label = QLabel("00:00:00", self)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.time_label)

        self.setLayout(main_layout)
        self.center_window(self)

        #Инициализация переменных для записи
        self.recording = False
        self.frames = []
        self.elapsed_time = 0
        
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

    def start_recording(self):
        self.recording = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        #Запуск таймера для записи кадров
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.record_frame)
        self.timer.start(33)  # 30 FPS

        #Запуск таймера для обновления времени записи
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)  # 1 секунда

    def stop_recording(self):
        self.recording = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        #Остановка таймера
        self.timer.stop()
        self.time_timer.stop()

        #Сохранение видео
        file_path, _ = QFileDialog.getSaveFileName(self, self.translations["save_video_dialog_title"], "", "MP4 Files (*.mp4)")
        if file_path:
            self.save_video(file_path)

    def record_frame(self):
        if self.recording:
            screen = pyautogui.screenshot()
            frame = np.array(screen)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            self.frames.append(frame)

    def save_video(self, file_path):
        if self.frames:
            height, width, _ = self.frames[0].shape
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(file_path, fourcc, 30.0, (width, height))
            for frame in self.frames:
                out.write(frame)
            out.release()
            self.frames = []

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
        
        self.time_label.setStyleSheet(f"""
            font-size: 16px;
            font-family: 'Segoe UI';
            color: {theme_vals['fg']};
        """)