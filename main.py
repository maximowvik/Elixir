import sys
import winreg
import json
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QGridLayout,
    QVBoxLayout,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QComboBox
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint
from PyQt6.QtGui import QScreen
from vendor.components.iconmanager import IconManager
from vendor.components.qrcodewindow import QRCodeWindow
from vendor.components.browser import Browser
from vendor.components.speedtestwindow import SpeedTestWindow
from vendor.components.screenrecoderwindow import ScreenRecorderWindow
from vendor.components.screenshotwindow import ScreenshotWindow
from vendor.components.screenshotwindow import ScreenshotWindow
from vendor.components.screesharewindow import ScreenShareWindow
from vendor.components.tranlatorwindow import TranslatorWindow
from vendor.components.pcinfowindow import PCInfoWindow
from vendor.components.paintwindow import PaintWindow

# Настройки DPI для высоких разрешений
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._old_pos = None
        self.language = "ru"
        self.translations = self.load_translations(self.language)
        self.initUI()

    def load_translations(self, language):
        with open(f"vendor/core/language/{language}.json", "r", encoding="utf-8") as file:
            return json.load(file)

    def initUI(self):
        self.setWindowTitle(self.translations["window_title"])
        self.setWindowIcon(IconManager.get_icon("main"))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.theme = self.get_system_theme()
        self.apply_theme(self.theme)

        self.center_window(self)

        main_layout = QVBoxLayout()

        title_layout = QHBoxLayout()

        #Выпадающий список для выбора языка
        self.language_combo = QComboBox(self)
        self.language_combo.addItem(QIcon("pic/ru.png"), "Русский")
        self.language_combo.addItem(QIcon("pic/en.png"), "English")
        self.language_combo.setStyleSheet("""
            QComboBox {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                            stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
                border: none;
                color: white;
                font-family: 'Segoe UI';
                font-size: 12pt;
                padding: 5px;
                border-radius: 5px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(icon/down_arrow.png);
                width: 14px;
                height: 14px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid darkgray;
                selection-background-color: #ff4891;
            }
        """)
        self.language_combo.setFixedWidth(108)  # Увеличиваем ширину
        self.language_combo.currentIndexChanged.connect(self.change_language)
        title_layout.addWidget(self.language_combo)

        title_layout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        #Кнопка смены темы
        self.theme_button = QPushButton()
        self.theme_button.setStyleSheet("background-color: transparent; border: none;")
        self.pixmap_theme_light = QPixmap(IconManager.get_images("change_theme"))
        self.pixmap_theme_dark = QPixmap(IconManager.get_images("change_theme"))
        self.theme_button.setIcon(QIcon(self.pixmap_theme_light if self.theme == "light" else self.pixmap_theme_dark))
        self.theme_button.clicked.connect(self.toggle_theme)
        title_layout.addWidget(self.theme_button)

        #Кнопка свернуть
        minimize_button = QPushButton()
        minimize_button.setStyleSheet("background-color: transparent; border: none;")
        pixmap_minimize = QPixmap("pic/minus.png")
        icon_minimize = QIcon(pixmap_minimize)
        minimize_button.setIcon(icon_minimize)
        minimize_button.setIconSize(QSize(15, 15))
        minimize_button.clicked.connect(self.showMinimized)
        title_layout.addWidget(minimize_button)

        #Кнопка закрытия
        close_button = QPushButton()
        close_button.setStyleSheet("background-color: transparent; border: none;")
        pixmap_close = QPixmap(IconManager.get_images("button_close"))
        icon_close = QIcon(pixmap_close)
        close_button.setIcon(icon_close)
        close_button.setIconSize(QSize(15, 15))
        close_button.clicked.connect(self.close)
        title_layout.addWidget(close_button)

        main_layout.addLayout(title_layout)

        #Логотип сверху
        top_image_label = QLabel()
        top_image_pixmap = QPixmap(IconManager.get_images("main_logo"))

        scaled_pixmap = top_image_pixmap.scaledToWidth(
            self.width() // 2, Qt.TransformationMode.SmoothTransformation
        )

        top_image_label.setPixmap(scaled_pixmap)
        top_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(top_image_label)

        #Макет для кнопок
        grid_layout = QGridLayout()

        grid_layout.setVerticalSpacing(30)

        #Кнопка 1
        button1 = self.create_button(IconManager.get_images("qr_code"))
        button1.clicked.connect(self.open_window1)
        grid_layout.addWidget(button1, 0, 0)

        #Кнопка 2
        button2 = self.create_button(IconManager.get_images("speed_test"))
        button2.clicked.connect(self.open_window2)
        grid_layout.addWidget(button2, 0, 1)

        #Кнопка 3
        button3 = self.create_button(IconManager.get_images("microphone"))
        button3.clicked.connect(self.open_window3)
        grid_layout.addWidget(button3, 0, 2)

        #Кнопка 4
        button4 = self.create_button(IconManager.get_images("audio"))
        button4.clicked.connect(self.open_window4)
        grid_layout.addWidget(button4, 1, 0)

        #Кнопка 5
        button5 = self.create_button(IconManager.get_images("paint"))
        button5.clicked.connect(self.open_window5)
        grid_layout.addWidget(button5, 1, 1)

        #Кнопка 6
        button6 = self.create_button(IconManager.get_images("pc_info"))
        button6.clicked.connect(self.open_window6)
        grid_layout.addWidget(button6, 1, 2)

        #Кнопка 7
        button7 = self.create_button(IconManager.get_images('browser'))
        button7.clicked.connect(self.open_window7)
        grid_layout.addWidget(button7, 2, 0)

        #Кнопка 8
        button8 = self.create_button(IconManager.get_images('screenshot'))
        button8.clicked.connect(self.open_window8)
        grid_layout.addWidget(button8, 2, 1)

        #Кнопка 9
        button9 = self.create_button(IconManager.get_images('chat'))
        button9.clicked.connect(self.open_window9)
        grid_layout.addWidget(button9, 2, 2)

        #Кнопка 10
        button10 = self.create_button(IconManager.get_images('screen_recorder'))
        button10.clicked.connect(self.open_window10)
        grid_layout.addWidget(button10, 3, 0)

        #Кнопка 11
        button11 = self.create_button(IconManager.get_images('screen_share'))
        button11.clicked.connect(self.open_window11)
        grid_layout.addWidget(button11, 3, 1)

        #Кнопка 12
        button12 = self.create_button(IconManager.get_images('translator'))
        button12.clicked.connect(self.open_window12)
        grid_layout.addWidget(button12, 3, 2)

        main_layout.addLayout(grid_layout)

        self.setLayout(main_layout)
        self.center_window(self)

    def create_button(self, icon_path):
        button = QPushButton()
        button.setStyleSheet("background-color: transparent; border: none;")
        pixmap = QPixmap(icon_path)
        icon = QIcon(pixmap)
        button.setIcon(icon)
        button.setIconSize(QSize(self.width() // 6, self.height() // 6))
        return button

    def get_system_theme(self):
        try:
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            winreg.CloseKey(registry)
            return "light" if value == 1 else "dark"
        except Exception as e:
            print(f"Error reading system theme: {e}")
            return "light"

    def apply_theme(self, theme):
        if theme == "light":
            app.setStyleSheet(
                """
                QWidget {
                    background-color: white;
                    color: black;
                    font-family: 'Segoe UI';
                    font-size: 12pt;
                }
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: black;
                    font-family: 'Segoe UI';
                    font-size: 12pt;
                }
                QLineEdit {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
                    border: none;
                    color: white;
                    font-family: 'Segoe UI';
                    font-size: 12pt;
                    padding: 10px;
                    border-radius: 5px;
                }
                QComboBox {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
                    border: none;
                    color: white;
                    font-family: 'Segoe UI';
                    font-size: 12pt;
                    padding: 10px;
                    border-radius: 5px;
                }
                """
            )
        else:
            app.setStyleSheet(
                """
                QWidget {
                    background-color: black;
                    color: white;
                    font-family: 'Segoe UI';
                    font-size: 12pt;
                }
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: white;
                    font-family: 'Segoe UI';
                    font-size: 12pt;
                }
                QLineEdit {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
                    border: none;
                    color: white;
                    font-family: 'Segoe UI';
                    font-size: 12pt;
                    padding: 10px;
                    border-radius: 5px;
                }
                QComboBox {
                    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
                    border: none;
                    color: white;
                    font-family: 'Segoe UI';
                    font-size: 12pt;
                    padding: 10px;
                    border-radius: 5px;
                }
                """
            )

    def toggle_theme(self):
        if self.theme == "light":
            self.theme = "dark"
            self.apply_theme("dark")
            self.theme_button.setIcon(QIcon(self.pixmap_theme_dark))
        else:
            self.theme = "light"
            self.apply_theme("light")
            self.theme_button.setIcon(QIcon(self.pixmap_theme_light))

    def change_language(self, index):
        if index == 0:
            self.language = "ru"
        else:
            self.language = "en"
        self.translations = self.load_translations(self.language)
        self.update_translations()

    def update_translations(self):
        self.setWindowTitle(self.translations["window_title"])
        self.theme_button.setToolTip(self.translations["theme_button"])

    def open_new_window(self):
        self.new_window = QWidget()
        self.new_window.setWindowTitle(self.translations["new_window_title"])
        label = QLabel(self.translations["new_window_label"], self.new_window)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.new_window.setGeometry(200, 200, 300, 150)
        self.center_window(self.new_window)
        self.new_window.show()

    def open_window1(self):
        self.qr_window = QRCodeWindow(self.language)
        self.qr_window.show()

    def open_window2(self):
        self.speed_window = SpeedTestWindow(self.language)
        self.speed_window.show()

    def open_window3(self):
        self.new_window = QWidget()
        self.new_window.setWindowTitle(self.translations["window_3_title"])
        label = QLabel(self.translations["window_3_label"], self.new_window)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.new_window.setGeometry(200, 200, 200, 150)
        self.center_window(self.new_window)
        self.new_window.show()

    def open_window4(self):
        self.new_window = QWidget()
        self.new_window.setWindowTitle(self.translations["window_4_title"])
        label = QLabel(self.translations["window_4_label"], self.new_window)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.new_window.setGeometry(200, 200, 200, 150)
        self.center_window(self.new_window)
        self.new_window.show()

    def open_window5(self):
        self.paint_window = PaintWindow(self.language)
        self.paint_window.show()

    def open_window6(self):
        self.pc_info_window = PCInfoWindow(self.language)
        self.pc_info_window.show()

    def open_window7(self):
        self.browser = Browser(app)
        self.browser.show()

    def open_window8(self):
        self.screenshot_window = ScreenshotWindow(self.language)
        self.screenshot_window.show()

    def open_window9(self):
        self.new_window = QWidget()
        self.new_window.setWindowTitle(self.translations["window_9_title"])
        label = QLabel(self.translations["window_9_label"], self.new_window)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.new_window.setGeometry(200, 200, 200, 150)
        self.center_window(self.new_window)
        self.new_window.show()

    def open_window10(self):
        self.screen_recorder_window = ScreenRecorderWindow(self.language)
        self.screen_recorder_window.show()

    def open_window11(self):
        self.screen_share_window = ScreenShareWindow(self.language)
        self.screen_share_window.show()

    def open_window12(self):
        self.translator_window = TranslatorWindow(self.language)
        self.translator_window.show()

    def center_window(self, window):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        qr = window.frameGeometry()
        cp = screen.center()
        qr.moveCenter(cp)
        window.move(qr.topLeft())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_button_sizes()

    def adjust_button_sizes(self):
        min_size = 50
        for button in self.findChildren(QPushButton):
            size = min(self.width() // 6, self.height() // 6)
            size = max(size, min_size)
            button.setIconSize(QSize(size, size))

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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.fillPath(path, QColor(self.palette().color(self.backgroundRole())))
        painter.setClipPath(path)
        super().paintEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Создаем файл qt.conf для правильной работы DPI
    import os
    if not os.path.exists("qt.conf"):
        with open("qt.conf", "w") as f:
            f.write("[Platforms]\nWindowsArguments = dpiawareness=0,1,2\n")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
