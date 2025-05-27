import socket
import psutil
import GPUtil
import cpuinfo
import json
import platform
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QSpacerItem, QSizePolicy
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath
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
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.main_layout = QVBoxLayout()

        self.setup_title_bar()
        self.setup_info_section()
        self.setup_copy_button()
        self.setup_notification_label()

        self.setLayout(self.main_layout)

    def setup_title_bar(self):
        title = QHBoxLayout()
        title.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        for icon, slot in [(IconManager.get_images("roll_up_button"), self.showMinimized),
                           (IconManager.get_images("button_close"), self.close)]:
            btn = self.create_title_button(icon, slot)
            title.addWidget(btn)
        self.main_layout.addLayout(title)

    def setup_info_section(self):
        pc_info = self.get_pc_info()
        self.info_label = QLabel(pc_info, self)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.info_label.setWordWrap(True)
        self.main_layout.addWidget(self.info_label)

    def setup_copy_button(self):
        self.copy_button = QPushButton(self.translations["copy_button"], self)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.main_layout.addWidget(self.copy_button)

    def setup_notification_label(self):
        self.notification_label = QLabel(self.translations["notification_label"], self)
        self.notification_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notification_label.hide()
        self.main_layout.addWidget(self.notification_label)

    def apply_theme(self):
        palette = self.theme_manager.theme_palette[self.theme_manager.current_theme()]

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {palette['bg']};
                color: {palette['fg']};
                font-family: 'Segoe UI';
                font-size: 12pt;
            }}
            QPushButton {{
                background-color: {palette['bg']};
                color: {palette['fg']};
                border: 1px solid {palette['border']};
                border-radius: 5px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {palette['hover']};
            }}
            QPushButton:pressed {{
                background-color: {palette['pressed']};
            }}
        """)

    def create_title_button(self, icon_name, slot):
        btn = QPushButton()
        btn.setIcon(QIcon(QPixmap(f"{icon_name}")))
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

    def get_pc_info(self):
        info_lines = [
            f"{self.translations['pc_name']}: {socket.gethostname()}",
            f"{self.translations['windows_version']}: {self.get_os_data()}",
            f"{self.translations['cpu_info']}: {self.get_cpu_info()}",
            f"{self.translations['gpu_info']}: {self.get_gpu_info()}",
            self.get_ram_info(),
            f"{self.translations['storage_info']}: {self.get_storage_info()}",
            f"{self.translations['ip_address']}: {self.get_ip_address()}"
        ]
        return "\n".join(info_lines)

    def get_os_data(self):
        try:
            return f"{platform.system()} (Build {platform.version()}) {platform.release()}"
        except Exception as e:
            print(f"Error reading os data: {e}")
            return "Не удалось получить данные об операционной системе"



    def decode_product_key(self, digital_product_id):
        key_offset = 52
        digits = "BCDFGHJKMPQRTVWXY2346789"
        decoded_chars = []

        for i in range(24):
            current = 0
            for j in range(14, -1, -1):
                current = (current * 256) ^ digital_product_id[j + key_offset]
                digital_product_id[j + key_offset] = current // 24
                current %= 24
            decoded_chars.append(digits[current])

        return "".join(decoded_chars[::-1])

    def get_cpu_info(self):
        try:
            return cpuinfo.get_cpu_info()['brand_raw']
        except Exception as e:
            print(f"Error reading CPU info: {e}")
            return "Не удалось получить информацию о процессоре"

    def get_gpu_info(self):
        try:
            gpus = GPUtil.getGPUs()
            return gpus[0].name if gpus else "Не удалось получить информацию о видеокарте"
        except Exception as e:
            print(f"Error reading GPU info: {e}")
            return "Не удалось получить информацию о видеокарте"

    def get_ram_info(self):
        try:
            mem = psutil.virtual_memory()
            total = mem.total // (1024 ** 3)
            avail = mem.available // (1024 ** 3)
            return f"{self.translations['total_memory']}: {total} GB\n{self.translations['available_memory']}: {avail} GB"
        except Exception as e:
            print(f"Error reading RAM info: {e}")
            return "Не удалось получить информацию об оперативной памяти"

    def get_storage_info(self):
        try:
            storage_info = []
            for part in psutil.disk_partitions():
                usage = psutil.disk_usage(part.mountpoint)
                storage_info.append(f"{part.device} {usage.total // (1024 ** 3)} GB")
            return ", ".join(storage_info)
        except Exception as e:
            print(f"Error reading storage info: {e}")
            return "Не удалось получить информацию о хранилище"

    def get_ip_address(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            print(f"Error reading IP address: {e}")
            return "Не удалось получить IP-адрес"

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.info_label.text())
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
