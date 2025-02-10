import winreg
import socket
import psutil
import GPUtil
import cpuinfo
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
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint, QTimer
from PyQt6.QtGui import QScreen
from .iconmanager import IconManager

class PCInfoWindow(QWidget):
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
        self.setWindowTitle(self.translations["pc_info_window_title"])
        self.setWindowIcon(IconManager.get_icon("pc_info"))
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

        #Получение информации о ПК
        pc_info = self.get_pc_info()

        #Отображение информации о ПК
        self.info_label = QLabel(pc_info, self)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 12pt;")
        main_layout.addWidget(self.info_label)

        #Кнопка копирования
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
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        main_layout.addWidget(self.copy_button)

        #Уведомление о копировании
        self.notification_label = QLabel(self.translations["notification_label"], self)
        self.notification_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notification_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 12pt; color: green;")
        self.notification_label.hide()
        main_layout.addWidget(self.notification_label)

        self.setLayout(main_layout)
        self.center_window(self)

    def get_pc_info(self):
        pc_name = socket.gethostname()
        windows_version = self.get_windows_version()
        windows_key = self.get_windows_key()
        cpu_info = self.get_cpu_info()
        gpu_info = self.get_gpu_info()
        ram_info = self.get_ram_info()
        storage_info = self.get_storage_info()
        ip_address = self.get_ip_address()

        return (
            f"{self.translations['pc_name']}: {pc_name}\n"
            f"{self.translations['windows_version']}: {windows_version}\n"
            f"{self.translations['windows_key']}: {windows_key}\n"
            f"{self.translations['cpu_info']}: {cpu_info}\n"
            f"{self.translations['gpu_info']}: {gpu_info}\n"
            f"{ram_info}\n"
            f"{self.translations['storage_info']}: {storage_info}\n"
            f"{self.translations['ip_address']}: {ip_address}\n"
        )

    def get_windows_version(self):
        try:
            registry = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
            key = winreg.OpenKey(registry, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            product_name, _ = winreg.QueryValueEx(key, "ProductName")
            current_build, _ = winreg.QueryValueEx(key, "CurrentBuild")
            ubbr, _ = winreg.QueryValueEx(key, "UBR")
            release_id, _ = winreg.QueryValueEx(key, "ReleaseId")
            winreg.CloseKey(key)
            winreg.CloseKey(registry)
            return f"{product_name} (Build {current_build}.{ubbr}) {release_id}"
        except Exception as e:
            print(f"Error reading Windows version: {e}")
            return "Не удалось получить версию Windows"

    def get_windows_key(self):
        try:
            registry = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
            key = winreg.OpenKey(registry, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            digital_product_id, _ = winreg.QueryValueEx(key, "DigitalProductId")
            winreg.CloseKey(key)
            winreg.CloseKey(registry)
            return self.decode_product_key(digital_product_id)
        except Exception as e:
            print(f"Error reading Windows key: {e}")
            return "Не удалось получить ключ Windows"

    def decode_product_key(self, digital_product_id):
        key_offset = 52
        digits = "BCDFGHJKMPQRTVWXY2346789"
        decoded_chars = []

        
        digital_product_id_list = list(digital_product_id)

        for i in range(24):
            current = 0
            for j in range(14, -1, -1):
                current = (current * 256) ^ digital_product_id_list[j + key_offset]
                digital_product_id_list[j + key_offset] = current // 24
                current = current % 24
            decoded_chars.append(digits[current])

        return "".join(decoded_chars[::-1])

    def get_cpu_info(self):
        try:
            cpu_info = cpuinfo.get_cpu_info()
            return f"{cpu_info['brand_raw']}"
        except Exception as e:
            print(f"Error reading CPU info: {e}")
            return "Не удалось получить информацию о процессоре"

    def get_gpu_info(self):
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                return gpus[0].name
            else:
                return "Не удалось получить информацию о видеокарте"
        except Exception as e:
            print(f"Error reading GPU info: {e}")
            return "Не удалось получить информацию о видеокарте"

    def get_ram_info(self):
        try:
            total_memory = psutil.virtual_memory().total
            available_memory = psutil.virtual_memory().available
            return f"{self.translations['total_memory']}: {total_memory // (1024 ** 3)} GB\n{self.translations['available_memory']}: {available_memory // (1024 ** 3)} GB"
        except Exception as e:
            print(f"Error reading RAM info: {e}")
            return "Не удалось получить информацию о оперативной памяти"

    def get_storage_info(self):
        try:
            partitions = psutil.disk_partitions()
            storage_info = []
            for partition in partitions:
                usage = psutil.disk_usage(partition.mountpoint)
                storage_info.append(f"{partition.device} {usage.total // (1024 ** 3)} GB")
            return ", ".join(storage_info)
        except Exception as e:
            print(f"Error reading storage info: {e}")
            return "Не удалось получить информацию о хранилище"

    def get_ip_address(self):
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception as e:
            print(f"Error reading IP address: {e}")
            return "Не удалось получить IP-адрес"

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.info_label.text())
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
