import sys
import os
import winreg
import speedtest
import socket
import psutil
import GPUtil
import cpuinfo
import subprocess
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
    QFileDialog,
    QComboBox,
    QProgressBar,
    QColorDialog,
    QInputDialog,
    QTextEdit
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath, QPen, QBrush, QTextOption
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint, QThread, pyqtSignal, QTimer, pyqtSlot, QRect
from PyQt6.QtGui import QScreen
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image
from googletrans import Translator, LANGUAGES
import asyncio
import pyautogui
import cv2
import numpy as np
from flask import Flask, Response
import threading
import mss
import time
from werkzeug.serving import make_server
from vendor.components.iconmanager import IconManager
from vendor.components.qrcodewindow import QRCodeWindow

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
        self.pixmap_theme_light = QPixmap("pic/themes.png")
        self.pixmap_theme_dark = QPixmap("pic/themes.png")
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
        pixmap_close = QPixmap("pic/close.png")
        icon_close = QIcon(pixmap_close)
        close_button.setIcon(icon_close)
        close_button.setIconSize(QSize(15, 15))
        close_button.clicked.connect(self.close)
        title_layout.addWidget(close_button)

        main_layout.addLayout(title_layout)

        #Логотип сверху
        top_image_label = QLabel()
        top_image_pixmap = QPixmap("pic/logo.png")

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
        button1 = self.create_button("pic/scan.png")
        button1.clicked.connect(self.open_window1)
        grid_layout.addWidget(button1, 0, 0)

        #Кнопка 2
        button2 = self.create_button("pic/speed.png")
        button2.clicked.connect(self.open_window2)
        grid_layout.addWidget(button2, 0, 1)

        #Кнопка 3
        button3 = self.create_button("pic/mic.png")
        button3.clicked.connect(self.open_window3)
        grid_layout.addWidget(button3, 0, 2)

        #Кнопка 4
        button4 = self.create_button("pic/audio.png")
        button4.clicked.connect(self.open_window4)
        grid_layout.addWidget(button4, 1, 0)

        #Кнопка 5
        button5 = self.create_button("pic/paint.png")
        button5.clicked.connect(self.open_window5)
        grid_layout.addWidget(button5, 1, 1)

        #Кнопка 6
        button6 = self.create_button("pic/info.png")
        button6.clicked.connect(self.open_window6)
        grid_layout.addWidget(button6, 1, 2)

        #Кнопка 7
        button7 = self.create_button("pic/globe.png")
        button7.clicked.connect(self.open_window7)
        grid_layout.addWidget(button7, 2, 0)

        #Кнопка 8
        button8 = self.create_button("pic/folder.png")
        button8.clicked.connect(self.open_window8)
        grid_layout.addWidget(button8, 2, 1)

        #Кнопка 9
        button9 = self.create_button("pic/chat.png")
        button9.clicked.connect(self.open_window9)
        grid_layout.addWidget(button9, 2, 2)

        #Кнопка 10
        button10 = self.create_button("pic/video.png")
        button10.clicked.connect(self.open_window10)
        grid_layout.addWidget(button10, 3, 0)

        #Кнопка 11
        button11 = self.create_button("pic/computer.png")
        button11.clicked.connect(self.open_window11)
        grid_layout.addWidget(button11, 3, 1)

        #Кнопка 12
        button12 = self.create_button("pic/journal.png")
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
                QProgressBar {
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                    background-color: #f0f0f0;
                    font-family: 'Segoe UI';
                    font-size: 12pt;
                }
                QProgressBar::chunk {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                                                       stop:0 rgba(66, 76, 230, 255),  /* Синий */
                                                       stop:0.5 rgba(174, 0, 238, 255), /* Фиолетовый */
                                                       stop:1 rgba(255, 72, 145, 255)); /* Розовый */
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
                QProgressBar {
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                    background-color: #f0f0f0;
                    font-family: 'Segoe UI';
                    font-size: 12pt;
                }
                QProgressBar::chunk {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                                                       stop:0 rgba(66, 76, 230, 255),  /* Синий */
                                                       stop:0.5 rgba(174, 0, 238, 255), /* Фиолетовый */
                                                       stop:1 rgba(255, 72, 145, 255)); /* Розовый */
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
        subprocess.Popen([sys.executable, 'vendor/components/browser.py'])

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


class SpeedTestWorker(QThread):
    result = pyqtSignal(float, float)
    progress = pyqtSignal(int)

    def run(self):
        st = speedtest.Speedtest()
        try:
            st.get_servers()
            self.progress.emit(33)
            st.download()
            self.progress.emit(66)
            st.upload()
            self.progress.emit(100)
            results = st.results.dict()
            download_speed = results["download"] / 1_000_000
            upload_speed = results["upload"] / 1_000_000
            self.result.emit(download_speed, upload_speed)
        except speedtest.SpeedtestHTTPError as e:
            print(f"HTTP Error: {e}")
        except speedtest.SpeedtestCLIError as e:
            print(f"CLI Error: {e}")
        except Exception as e:
            print(f"Unexpected Error: {e}")

class SpeedTestWindow(QWidget):
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
        self.setWindowTitle(self.translations["speed_test_window_title"])
        self.setWindowIcon(IconManager.get_icon("speed_test"))
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

        #Макет для спидометра
        speedometer_layout = QVBoxLayout()

        #Спидометр
        self.speedometer = QLabel(self)
        self.speedometer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speedometer.setStyleSheet("font-size: 24px; font-family: 'Segoe UI';")
        speedometer_layout.addWidget(self.speedometer)

        #IP-адрес
        self.ip_label = QLabel(self)
        self.ip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ip_label.setStyleSheet("font-size: 16px; font-family: 'Segoe UI';")
        speedometer_layout.addWidget(self.ip_label)

        #Прогресс-бар
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        #Стиль для прогресс-бара
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                background-color: #f0f0f0;
                font-family: 'Segoe UI';
                font-size: 12pt;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                                                   stop:0 rgba(66, 76, 230, 255),  /* Синий */
                                                   stop:0.5 rgba(174, 0, 238, 255), /* Фиолетовый */
                                                   stop:1 rgba(255, 72, 145, 255)); /* Розовый */
                border-radius: 5px;
            }
        """)

        speedometer_layout.addWidget(self.progress_bar)

        main_layout.addLayout(speedometer_layout)

        self.setLayout(main_layout)
        self.center_window(self)

        #Запуск измерения скорости
        self.worker = SpeedTestWorker()
        self.worker.result.connect(self.display_results)
        self.worker.progress.connect(self.update_progress)
        self.worker.start()

        #Получение IP-адреса
        self.ip_address = self.get_ip_address()
        self.ip_label.setText(f"{self.translations['ip_address']}: {self.ip_address}")

    def get_ip_address(self):
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception as e:
            print(f"Error reading IP address: {e}")
            return "Не удалось получить IP-адрес"

    def display_results(self, download_speed, upload_speed):
        self.speedometer.setText(f"{self.translations['download_speed']}: {download_speed:.2f} Mbps\n{self.translations['upload_speed']}: {upload_speed:.2f} Mbps")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

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

class PaintWindow(QWidget):
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
        self.setWindowTitle(self.translations["paint_window_title"])
        self.setWindowIcon(IconManager.get_icon("paint"))
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

        #Макет для инструментов рисования
        tools_layout = QHBoxLayout()

        #Кнопка выбора цвета
        self.color_button = QPushButton(self.translations["choose_color_button"], self)
        self.color_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.color_button.clicked.connect(self.choose_color)
        tools_layout.addWidget(self.color_button)

        #Кнопка выбора инструмента
        self.tool_combo = QComboBox(self)
        self.tool_combo.addItems(self.translations["tool_combo"])
        self.tool_combo.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.tool_combo.currentIndexChanged.connect(self.change_tool)
        tools_layout.addWidget(self.tool_combo)

        #Кнопка выбора размера холста
        self.size_button = QPushButton(self.translations["canvas_size_button"], self)
        self.size_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.size_button.clicked.connect(self.set_canvas_size)
        tools_layout.addWidget(self.size_button)

        #Кнопка сохранения изображения
        self.save_button = QPushButton(self.translations["save_button"], self)
        self.save_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.save_button.clicked.connect(self.save_image)
        tools_layout.addWidget(self.save_button)

        main_layout.addLayout(tools_layout)

        #Холст для рисования
        self.canvas = QLabel(self)
        self.canvas.setStyleSheet("background-color: white; border: 1px solid black;")
        self.canvas.setFixedSize(800, 600)
        self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.canvas)

        self.setLayout(main_layout)
        self.center_window(self)

        #Инициализация переменных для рисования
        self.drawing = False
        self.last_point = QPoint()
        self.pen = QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.SolidLine)
        self.brush = QBrush(Qt.GlobalColor.white, Qt.BrushStyle.SolidPattern)
        self.image = QPixmap(self.canvas.size())
        self.image.fill(Qt.GlobalColor.white)

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.pen.setColor(color)

    def change_tool(self, index):
        tool = self.tool_combo.itemText(index)
        if tool == self.translations["tool_combo"][0]:
            self.pen.setWidth(2)
        elif tool == self.translations["tool_combo"][1]:
            self.pen.setWidth(10)
        elif tool == self.translations["tool_combo"][2]:
            self.pen.setColor(Qt.GlobalColor.white)
            self.pen.setWidth(20)

    def set_canvas_size(self):
        width, ok1 = QInputDialog.getInt(self, self.translations["canvas_size_dialog_title"], self.translations["canvas_width_label"], 800, 1, 10000, 1)
        height, ok2 = QInputDialog.getInt(self, self.translations["canvas_size_dialog_title"], self.translations["canvas_height_label"], 600, 1, 10000, 1)
        if ok1 and ok2:
            self.canvas.setFixedSize(width, height)
            self.image = QPixmap(width, height)
            self.image.fill(Qt.GlobalColor.white)
            self.update()

    def save_image(self):
        file_path, _ = QFileDialog.getSaveFileName(self, self.translations["save_image_dialog_title"], "", self.translations["save_image_filter"])
        if file_path:
            if file_path.endswith(".pdf"):
                c = canvas.Canvas(file_path, pagesize=letter)
                self.image.save("temp_image.png")
                c.drawImage("temp_image.png", 0, 0, width=letter[0], height=letter[1])
                c.save()
                os.remove("temp_image.png")
            else:
                self.image.save(file_path)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.fillPath(path, QColor(self.palette().color(self.backgroundRole())))
        painter.setClipPath(path)
        super().paintEvent(event)

        # Рисуем изображение на холсте
        canvas_painter = QPainter(self.canvas)
        canvas_painter.drawPixmap(self.canvas.rect(), self.image)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = event.pos()
            self._old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self.drawing:
            painter = QPainter(self.image)
            painter.setPen(self.pen)
            painter.drawLine(self.last_point, event.pos())
            self.last_point = event.pos()
            self.update()
        elif self._old_pos is not None:
            delta = QPoint(event.globalPosition().toPoint() - self._old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            self._old_pos = None

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

class TranslatorWindow(QWidget):
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
        self.setWindowTitle(self.translations["translator_window_title"])
        self.setWindowIcon(IconManager.get_icon("translator"))
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

        #Поле для ввода текста
        self.input_text = QTextEdit(self)
        self.input_text.setPlaceholderText(self.translations["input_text_placeholder"])
        self.input_text.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        main_layout.addWidget(self.input_text)

        #Выбор языка для перевода
        self.target_language_combo = QComboBox(self)
        self.target_language_combo.addItems(LANGUAGES.values())
        self.target_language_combo.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        main_layout.addWidget(self.target_language_combo)

        #Кнопка перевода
        translate_button = QPushButton(self.translations["translate_button"], self)
        translate_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        translate_button.clicked.connect(self.translate_text)
        main_layout.addWidget(translate_button)

        #Поле для отображения переведенного текста
        self.output_text = QTextEdit(self)
        self.output_text.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.output_text.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        main_layout.addWidget(self.output_text)

        #Поле для отображения языка введенного текста
        self.detected_language_label = QLabel(self)
        self.detected_language_label.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.detected_language_label.setWordWrap(True)
        main_layout.addWidget(self.detected_language_label)

        self.setLayout(main_layout)
        self.center_window(self)

    def translate_text(self):
        input_text = self.input_text.toPlainText()
        target_language = list(LANGUAGES.keys())[self.target_language_combo.currentIndex()]

        async def translate():
            translator = Translator()
            detected = await translator.detect(input_text)
            translation = await translator.translate(input_text, dest=target_language)
            return detected, translation

        detected, translation = asyncio.run(translate())

        self.detected_language_label.setText(f"{LANGUAGES[detected.lang]}")
        self.output_text.setText(f"{translation.text}")

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

class ScreenRecorderWindow(QWidget):
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
        self.setWindowTitle(self.translations["screen_recorder_window_title"])
        self.setWindowIcon(IconManager.get_icon("screen_recorder"))
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

        #Кнопка начала записи
        self.start_button = QPushButton(self.translations["start_button"], self)
        self.start_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.start_button.clicked.connect(self.start_recording)
        main_layout.addWidget(self.start_button)

        #Кнопка остановки записи
        self.stop_button = QPushButton(self.translations["stop_button"], self)
        self.stop_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_recording)
        main_layout.addWidget(self.stop_button)

        #Метка для отображения времени записи
        self.time_label = QLabel("00:00:00", self)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("font-size: 16px; font-family: 'Segoe UI';")
        main_layout.addWidget(self.time_label)

        self.setLayout(main_layout)
        self.center_window(self)

        #Инициализация переменных для записи
        self.recording = False
        self.frames = []
        self.elapsed_time = 0

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

class ScreenShareWindow(QWidget):
    stop_signal = pyqtSignal()

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
        self.setWindowTitle(self.translations["screen_share_window_title"])
        self.setWindowIcon(IconManager.get_icon("screen_share"))
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

        #Кнопка начала трансляции
        self.start_button = QPushButton(self.translations["start_button"], self)
        self.start_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.start_button.clicked.connect(self.start_streaming)
        main_layout.addWidget(self.start_button)

        #Кнопка остановки трансляции
        self.stop_button = QPushButton(self.translations["stop_button"], self)
        self.stop_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_streaming)
        main_layout.addWidget(self.stop_button)

        #Метка для отображения ссылки
        self.url_label = QLabel("", self)
        self.url_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.url_label.setStyleSheet("font-size: 12px; font-family: 'Segoe UI';")
        main_layout.addWidget(self.url_label)

        #Кнопка для копирования ссылки
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
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_url)
        main_layout.addWidget(self.copy_button)

        #Уведомление о копировании
        self.notification_label = QLabel(self.translations["notification_label"], self)
        self.notification_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notification_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 12pt; color: green;")
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

class ScreenshotWindow(QWidget):
    def __init__(self, language):
        super().__init__()
        self._old_pos = None
        self.language = language
        self.translations = self.load_translations(language)
        self.initUI()

    def load_translations(self, language):
        with open(f"{language}.json", "r", encoding="utf-8") as file:
            return json.load(file)

    def initUI(self):
        self.setWindowTitle(self.translations["screenshot_window_title"])
        self.setWindowIcon(IconManager.get_icon("screenshot"))
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

        #Кнопка для скриншота всего экрана
        self.fullscreen_button = QPushButton(self.translations["fullscreen_button"], self)
        self.fullscreen_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.fullscreen_button.clicked.connect(self.take_fullscreen_screenshot)
        main_layout.addWidget(self.fullscreen_button)

        #Кнопка для скриншота области
        self.area_button = QPushButton(self.translations["area_button"], self)
        self.area_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.area_button.clicked.connect(self.take_area_screenshot)
        main_layout.addWidget(self.area_button)

        #Выбор формата сохранения
        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["PNG", "JPG", "PDF", "BMP", "GIF", "TIFF"])
        self.format_combo.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        main_layout.addWidget(self.format_combo)

        #Выбор экрана
        self.screen_combo = QComboBox(self)
        self.screen_combo.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.screen_combo.addItems([f"Screen {i}" for i in range(1, len(self.get_screens()) + 1)])
        main_layout.addWidget(self.screen_combo)

        self.setLayout(main_layout)
        self.center_window(self)

    def get_screens(self):
        with mss.mss() as sct:
            return sct.monitors[1:]

    def take_fullscreen_screenshot(self):
        screen_index = self.screen_combo.currentIndex()
        screens = self.get_screens()
        if screen_index < len(screens):
            screen = screens[screen_index]
            with mss.mss() as sct:
                screenshot = sct.grab(screen)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                self.save_screenshot(img)

    def take_area_screenshot(self):
        self.hide()
        self.area_selection = AreaSelection(self.language)
        self.area_selection.screenshot_taken.connect(self.save_screenshot)
        self.area_selection.show()

    def save_screenshot(self, img):
        file_format = self.format_combo.currentText().lower()
        file_path, _ = QFileDialog.getSaveFileName(self, self.translations["save_screenshot_dialog_title"], "", f"{file_format.upper()} Files (*.{file_format})")

        if file_path:
            if file_format == "pdf":
                #PDF-документ
                temp_image_path = "temp_image.png"
                img.save(temp_image_path)
                c = canvas.Canvas(file_path, pagesize=letter)
                width, height = letter
                c.drawImage(temp_image_path, (width - img.size[0]) / 2, (height - img.size[1]) / 2, width=img.size[0], height=img.size[1])
                c.save()
                os.remove(temp_image_path)
            else:
                img.save(file_path)

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

class AreaSelection(QWidget):
    screenshot_taken = pyqtSignal(Image.Image)

    def __init__(self, language, parent=None):
        super().__init__(parent)
        self.language = language
        self.translations = self.load_translations(language)
        self.initUI()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.show()

    def load_translations(self, language):
        with open(f"{language}.json", "r", encoding="utf-8") as file:
            return json.load(file)

    def initUI(self):
        self.setWindowTitle(self.translations["area_selection_title"])
        self.setWindowIcon(IconManager.get_icon("area_selection"))
        self.start_pos = None
        self.end_pos = None
        self.drawing = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.fillPath(path, QColor(0, 0, 0, 128))
        painter.setClipPath(path)

        if self.start_pos and self.end_pos:
            rect = QRect(self.start_pos, self.end_pos).normalized()
            painter.setPen(QPen(Qt.GlobalColor.white, 2, Qt.PenStyle.DashLine))
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.drawing = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.end_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            self.drawing = False
            self.update()
            self.take_screenshot()

    def take_screenshot(self):
        if self.start_pos and self.end_pos:
            rect = QRect(self.start_pos, self.end_pos).normalized()
            monitor = {
                "top": rect.top(),
                "left": rect.left(),
                "width": rect.width(),
                "height": rect.height()
            }
            with mss.mss() as sct:
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                self.screenshot_taken.emit(img)
                self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
