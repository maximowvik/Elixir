import socket
import psutil
import GPUtil
import cpuinfo
import json
import requests
import platform
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QSpacerItem, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath, QFont
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint, QTimer
from PyQt6.QtGui import QScreen

from .iconmanager import IconManager

class PCInfoWindow(QWidget):
    def __init__(self, language, theme_manager):
        super().__init__()
        self._old_pos = None
        self.language = language
        self.theme_manager = theme_manager
        self.translations = self.load_translations(self.language)

        self.init_ui()
        self.center_window()

        # Подписка на сигнал изменения темы
        self.theme_manager.theme_changed.connect(self.apply_theme)
        self.apply_theme()

    def load_translations(self, language):
        with open(f"./vendor/core/language/{language}.json", "r", encoding="utf-8") as file:
            return json.load(file)

    def init_ui(self):
        self.setWindowTitle(self.translations["pc_info_window_title"])
        self.setWindowIcon(IconManager.get_icon("pc_info"))
        self.setMinimumSize(600, 500)

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(5)  # Reduce spacing between elements

        self.setup_title_bar()
        self.setup_system_info()
        self.setup_disk_table()
        self.setup_copy_button()
        self.setup_notification_label()

        self.setLayout(self.main_layout)

    def setup_title_bar(self):
        if self.theme_manager.get_current_platform() == "windows":
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        title_layout = QHBoxLayout()
        self.title_label = QLabel(self.translations["pc_info_window_title"])
        title_layout.addWidget(self.title_label)
        title_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        if self.theme_manager.get_current_platform() == "windows":
            for icon, handler in [("roll_up_button", self.showMinimized), ("button_close", self.close)]:
                btn = self.theme_manager.create_title_button(IconManager.get_images(icon), handler)
                title_layout.addWidget(btn)
            
        self.main_layout.addLayout(title_layout)

    def setup_system_info(self):
        system_info = self.get_system_info()
        self.system_info_label = QLabel(system_info, self)
        self.system_info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.system_info_label.setWordWrap(True)
        self.system_info_label.setFont(QFont("Segoe UI", 10))
        self.main_layout.addWidget(self.system_info_label)

    def setup_disk_table(self):
        self.disk_table = QTableWidget()
        self.disk_table.setColumnCount(5)
        self.disk_table.setHorizontalHeaderLabels([
            self.translations["disk"],
            self.translations["total"],
            self.translations["used"],
            self.translations["free"],
            self.translations["fs_type"]
        ])

        # Настройка таблицы
        self.disk_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.disk_table.verticalHeader().setVisible(False)
        self.disk_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.disk_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Set size policy to expanding to fill available space
        self.disk_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Заполнение данными
        disk_data = self.get_disk_info()
        self.disk_table.setRowCount(len(disk_data))

        for row, disk in enumerate(disk_data):
            for col, value in enumerate(disk):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.disk_table.setItem(row, col, item)

        # Resize rows to contents
        self.disk_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        disk_label = QLabel(f"{self.translations['storage_info']}:")
        disk_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.main_layout.addWidget(disk_label)
        self.main_layout.addWidget(self.disk_table)

    def setup_copy_button(self):
        self.button_layout = QHBoxLayout()

        # Add the copy button to the layout first
        self.copy_button = QPushButton(self.translations["copy_button"], self)
        self.copy_button.setFixedWidth(150)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.button_layout.addWidget(self.copy_button)

        # Add a spacer item to the right of the button to push it to the left
        self.button_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.main_layout.addLayout(self.button_layout)

    def setup_notification_label(self):
        self.notification_label = QLabel(self.translations["notification_label"], self)
        self.notification_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notification_label.hide()
        self.button_layout.addWidget(self.notification_label)

    def apply_theme(self):
        palette = self.theme_manager.theme_palette[self.theme_manager.current_theme()]

        # Основные стили
        main_style = f"""
            QWidget {{
                background-color: {palette['bg']};
                color: {palette['fg']};
                font-family: 'Segoe UI';
            }}
            QPushButton {{
                background-color: {palette['bg']};
                color: {palette['fg']};
                border: 1px solid {palette['border']};
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background-color: {palette['hover']};
            }}
            QPushButton:pressed {{
                background-color: {palette['pressed']};
            }}
            QLabel {{
                font-size: 10pt;
                margin-bottom: 5px;
            }}
        """

        # Стили для таблицы
        table_style = f"""
            QTableWidget {{
                border-radius: 10px;
                background-color: {palette['bg']};
                color: {palette['fg']};
                border: 1px solid {palette['border']};
                gridline-color: {palette['border']};
                font-size: 9.5pt;
                padding: 10px;
            }}
            QHeaderView::section {{
                background-color: {palette['hover']};
                color: {palette['fg']};
                border: 1px solid {palette['border']};
                padding: 5px;
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: 3px;
            }}
        """

        self.setStyleSheet(main_style + table_style)

    def get_system_info(self):
        info_lines = [
            f"<b>{self.translations['pc_name']}:</b> {socket.gethostname()}",
            f"<b>{self.translations['os_version']}:</b> {self.get_os_data()}",
            f"<b>{self.translations['cpu_info']}:</b> {self.get_cpu_info()}",
            f"<b>{self.translations['gpu_info']}:</b> {self.get_gpu_info()}",
            f"<b>{self.translations['total_memory']}:</b> {self.get_ram_info()}",
            f"<b>{self.translations['local_ip']}:</b> {self.get_local_ip()}",
            f"<b>{self.translations['public_ip']}:</b> {self.get_public_ip()}"
        ]
        return "<br>".join(info_lines)
    
    def get_local_ip(self):
        try: 
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return self.translations['ip_error']
        
    def get_public_ip(self):
        try: 
            return requests.get('https://api.ipify.org').text
        except Exception:
            return self.translations['ip_error']

    def get_disk_info(self):
        disk_info = []
        try:
            for part in psutil.disk_partitions():
                try:
                    if not part.fstype:
                        continue
                        
                    usage = psutil.disk_usage(part.mountpoint)
                    disk_info.append([
                        part.device,
                        f"{usage.total // (1024**3)} GB",
                        f"{usage.used // (1024**3)} GB ({usage.percent}%)",
                        f"{usage.free // (1024**3)} GB",
                        part.fstype
                    ])
                except Exception as e:
                    print(f"Error reading partition {part.device}: {e}")
        except Exception as e:
            print(f"Error reading storage info: {e}")
        
        return disk_info or [[self.translations["no_disk_info"], "", "", "", ""]]

    def get_os_data(self):
        try:
            return f"{platform.system()} {platform.release()} (Build {platform.version()})"
        except Exception as e:
            print(f"Error reading os data: {e}")
            return self.translations["unknown"]

    def get_cpu_info(self):
        try:
            return cpuinfo.get_cpu_info()['brand_raw']
        except Exception as e:
            print(f"Error reading CPU info: {e}")
            return self.translations["unknown"]

    def get_gpu_info(self):
        try:
            gpus = GPUtil.getGPUs()
            return gpus[0].name if gpus else self.translations["unknown"]
        except Exception as e:
            print(f"Error reading GPU info: {e}")
            return self.translations["unknown"]

    def get_ram_info(self):
        try:
            mem = psutil.virtual_memory()
            total = mem.total // (1024**3)
            used = mem.used // (1024**3)
            return f"{total} GB ({used} GB {self.translations['used']})"
        except Exception as e:
            print(f"Error reading RAM info: {e}")
            return self.translations["unknown"]

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        
        # Собираем текст для копирования
        system_text = self.system_info_label.text().replace("<br>", "\n").replace("<b>", "").replace("</b>", "")
        disk_text = "\n".join(["\t".join([self.disk_table.item(row, col).text() 
                                        for col in range(self.disk_table.columnCount())])
                             for row in range(self.disk_table.rowCount())])
        
        clipboard.setText(f"{system_text}\n\n{self.translations['storage_info']}:\n{disk_text}")
        
        # Показываем уведомление
        self.notification_label.show()
        QTimer.singleShot(2000, self.notification_label.hide)

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        qr = self.frameGeometry()
        qr.moveCenter(screen.center())
        self.move(qr.topLeft())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        palette = self.theme_manager.theme_palette[self.theme_manager.current_theme()]
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