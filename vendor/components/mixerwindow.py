import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSlider, QSpacerItem, QHBoxLayout,
    QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QPoint, QSize, QRectF, QTimer
from PyQt6.QtGui import (
    QPainter, QColor,  QPainterPath, QIcon, 
)
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
import sys
import psutil
from .iconmanager import IconManager

class VolumeMixer(QWidget):
    def __init__(self, theme_manager, translations: dict[str, str]):
        super().__init__()
        self.theme_manager = theme_manager
        self.translations = translations
        self._current_theme = self.theme_manager.current_theme()
        self._title_bar_buttons = []
        self._old_pos = None
        self.theme_manager.theme_changed.connect(self._on_theme_changed)

        self.setWindowTitle(self.translations["mixer_value"])
        self.setWindowIcon(IconManager.get_icon("audio"))
        self.setFixedWidth(500)

        self.main_container = QFrame()
        self.main_container.setObjectName("mainContainer")

        self.main_layout = QVBoxLayout(self.main_container)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(0)  # Уменьшаем расстояние между элементами

        container_layout = QVBoxLayout(self)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.main_container)

        self.main_layout.addLayout(self.create_title_bar())
        self.active_controls = {}

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_audio_sessions)
        self.update_timer.start(1000)

        self._update_audio_sessions()
        self._apply_theme()

    def create_title_bar(self):
        if self.theme_manager.get_current_platform() == "windows":
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        title_bar = QHBoxLayout()
        self.title_label = QLabel(self.translations["mixer_value"])
        title_bar.addWidget(self.title_label)
        title_bar.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding))
        if self.theme_manager.get_current_platform() == "windows":
            for icon, handler in [("roll_up_button", self.showMinimized), ("button_close", self.close)]:
                btn = self.theme_manager.create_title_button(IconManager.get_images(icon), handler)
                self._title_bar_buttons.append(btn)
                title_bar.addWidget(btn)
        return title_bar

    def _update_audio_sessions(self):
        current_sessions = {}

        for session in AudioUtilities.GetAllSessions():
            process = session.Process
            volume = session._ctl.QueryInterface(ISimpleAudioVolume)

            if not process:
                session_id = "system_sounds"
                process_name = "System Sounds"
                is_active = True
            else:
                session_id = f"proc_{process.pid}"
                process_name = process.name()
                is_active = psutil.pid_exists(process.pid) if process else False

            if not is_active:
                continue

            if session_id not in current_sessions:
                current_sessions[session_id] = {
                    'name': process_name,
                    'volume': volume,
                    'level': volume.GetMasterVolume(),
                    'muted': volume.GetMute(),
                    'process': process
                }

        for session_id in list(self.active_controls.keys()):
            if session_id not in current_sessions:
                self._remove_control(session_id)

        for session_id, session_data in current_sessions.items():
            if session_id in self.active_controls:
                self._update_control(session_id, session_data)
            else:
                self._add_control(session_id, session_data)

    def _add_control(self, session_id, session_data):
        palette = self.theme_manager.theme_palette[self._current_theme]

        row = QHBoxLayout()
        row.setSpacing(0)  # Убираем расстояние между элементами в строке
        row.setContentsMargins(5, 5, 5, 5)  # Убираем отступы

        name_label = QLabel(session_data['name'])
        name_label.setFixedSize(QSize(150, 40))
        name_label.setStyleSheet(f"background-color: {palette['bg']}; padding: 10px;")

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(int(session_data['level'] * 100))
        slider.setEnabled(not session_data['muted'])
        slider.setFixedSize(QSize(210, 40))
        slider.setStyleSheet(f"background-color: {palette['bg']}; padding: 10px;")

        percent_label = QLabel(f"{int(session_data['level'] * 100)}%")
        percent_label.setFixedWidth(60)
        percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        percent_label.setStyleSheet(f"background-color: {palette['bg']}; padding: 10px;")

        mute_btn = QPushButton()
        mute_btn.setCheckable(True)
        mute_btn.setChecked(session_data['muted'])
        mute_btn.setFixedSize(QSize(40, 40))
        mute_btn.setIconSize(QSize(35, 35))
        mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        mute_btn.setIcon(QIcon(IconManager.get_images("mute") if session_data['muted'] else IconManager.get_images("unmute")))
        mute_btn.setStyleSheet(f"background-color: {palette['bg']}; padding: 10px;")

        slider.valueChanged.connect(
            lambda value, vol=session_data['volume'], lbl=percent_label: (
                vol.SetMasterVolume(value / 100.0, None),
                lbl.setText(f"{value}%")
            ))

        mute_btn.toggled.connect(
            lambda muted, vol=session_data['volume'], slider=slider, btn=mute_btn: (
                vol.SetMute(muted, None),
                slider.setEnabled(not muted),
                btn.setIcon(QIcon(IconManager.get_images("mute") if muted else IconManager.get_images("unmute")))
            ))

        row.addWidget(name_label)
        row.addWidget(slider)
        row.addWidget(percent_label)
        row.addWidget(mute_btn)

        self.main_layout.addLayout(row)

        self.active_controls[session_id] = {
            'row': row,
            'label': name_label,
            'slider': slider,
            'percent': percent_label,
            'mute_btn': mute_btn,
            'volume': session_data['volume']
        }
        
        self._apply_theme()

    def _update_control(self, session_id, session_data):
        control = self.active_controls[session_id]

        control['slider'].blockSignals(True)
        control['slider'].setValue(int(session_data['level'] * 100))
        control['slider'].setEnabled(not session_data['muted'])
        control['slider'].blockSignals(False)

        control['percent'].setText(f"{int(session_data['level'] * 100)}%")

        control['mute_btn'].blockSignals(True)
        control['mute_btn'].setChecked(session_data['muted'])
        control['mute_btn'].setIcon(QIcon(IconManager.get_images("mute") if session_data['muted'] else IconManager.get_images("unmute")))
        control['mute_btn'].blockSignals(False)

    def _remove_control(self, session_id):
        control = self.active_controls.pop(session_id)
        while control['row'].count():
            item = control['row'].takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.main_layout.removeItem(control['row'])

    def _on_theme_changed(self, new_theme):
        self._current_theme = new_theme
        self._apply_theme()

    def _apply_theme(self):
        palette = self.theme_manager.theme_palette[self._current_theme]

        self.main_container.setStyleSheet(f"""
            QFrame#mainContainer {{
                background-color: {palette['bg']};
                border: 1px solid {palette['border']};
                border-radius: 10px;
            }}
        """)

        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {palette['fg']};
                font: 16px 'Segoe UI';
            }}
        """)

        for session_id in self.active_controls.keys():
            self._apply_control_style(session_id)

    def _apply_control_style(self, session_id):
        palette = self.theme_manager.theme_palette[self._current_theme]
        control = self.active_controls[session_id]

        control['label'].setStyleSheet(f"""
            QLabel {{
                color: {palette['fg']};
                font: 14px 'Segoe UI';
                padding-left: 5px;
            }}
        """)

        control['percent'].setStyleSheet(f"""
            QLabel {{
                color: {palette['fg']};
                font: 12px 'Segoe UI';
            }}
        """)

        control['slider'].setStyleSheet(f"""
            QSlider {{
                min-height: 25px;
            }}
            QSlider::groove:horizontal {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {palette['bg_info']}, stop:1 {palette['border']}
                );
                height: 10px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {palette['fg']};
                width: 20px;
                height: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {palette['bg_info']}, stop:1 {palette['bg_info']}
                );
                border-radius: 3px;
            }}
        """)

        control['mute_btn'].setStyleSheet(f"""
            QPushButton {{
                height: 30px;
                background-color: {palette['bg']};
                color: {palette['fg']};
                border: none;
                border-radius: 8px;
                padding: 8px 15px;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background: {palette['hover']};
            }}
            QPushButton:pressed {{
                background: {palette['pressed']};
            }}
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        palette = self.theme_manager.theme_palette[self._current_theme]
        painter.fillPath(path, QColor(palette['bg']))
        painter.setClipPath(path)
        super().paintEvent(event)

    def _is_in_title_bar(self, pos):
        return pos.y() <= 40  # Высота title bar

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
