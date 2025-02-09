from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QToolBar, QLineEdit, QLabel,
    QMessageBox, QTabWidget, QPushButton, QHBoxLayout, QSpacerItem, QSizePolicy,
    QFileDialog, QComboBox
)
from PyQt6.QtGui import QIcon, QPixmap, QKeySequence, QAction, QShortcut, QScreen, QPainter, QPainterPath, QColor
from PyQt6.QtCore import QUrl, Qt, QSize, QPoint, QRectF
import os
import sys
import winreg
import qrcode
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

class Browser(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self._old_pos = None
        self.app = app  # Store the app instance
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Browser")
        self.setWindowIcon(QIcon("pic/globe.png"))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.theme = self.get_system_theme()
        self.apply_theme(self.theme)

        self.center_window(self)

        main_layout = QVBoxLayout()

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(10, 5, 10, 5)

        title_label = QLabel()
        title_pixmap = QPixmap("pic/logo.png")
        scaled_pixmap = title_pixmap.scaledToWidth(100, Qt.TransformationMode.SmoothTransformation)
        title_label.setPixmap(scaled_pixmap)
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        title_layout.addWidget(title_label)

        title_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.theme_button = QPushButton()
        self.theme_button.setStyleSheet("background-color: transparent; border: none;")
        self.pixmap_theme_light = QPixmap("pic/themes.png")
        self.pixmap_theme_dark = QPixmap("pic/themes.png")
        self.theme_button.setIcon(QIcon(self.pixmap_theme_light if self.theme == "light" else self.pixmap_theme_dark))
        self.theme_button.setIconSize(QSize(25, 25))
        self.theme_button.clicked.connect(self.toggle_theme)
        title_layout.addWidget(self.theme_button)

        minimize_button = QPushButton()
        minimize_button.setStyleSheet("background-color: transparent; border: none;")
        pixmap_minimize = QPixmap("pic/minus.png")
        icon_minimize = QIcon(pixmap_minimize)
        minimize_button.setIcon(icon_minimize)
        minimize_button.setIconSize(QSize(25, 25))
        minimize_button.clicked.connect(self.showMinimized)
        title_layout.addWidget(minimize_button)

        self.expand_button = QPushButton()
        self.expand_button.setStyleSheet("background-color: transparent; border: none;")
        pixmap_expand = QPixmap("pic/expand.png")
        icon_expand = QIcon(pixmap_expand)
        self.expand_button.setIcon(icon_expand)
        self.expand_button.setIconSize(QSize(25, 25))
        self.expand_button.clicked.connect(self.toggle_maximized)
        title_layout.addWidget(self.expand_button)

        close_button = QPushButton()
        close_button.setStyleSheet("background-color: transparent; border: none;")
        pixmap_close = QPixmap("pic/close.png")
        icon_close = QIcon(pixmap_close)
        close_button.setIcon(icon_close)
        close_button.setIconSize(QSize(25, 25))
        close_button.clicked.connect(self.close)
        title_layout.addWidget(close_button)

        main_layout.addLayout(title_layout)

        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_current_tab)
        main_layout.addWidget(self.tab_widget)

        qtoolbar = QToolBar("Скрыть")
        qtoolbar.setIconSize(QSize(30, 30))
        qtoolbar.setAllowedAreas(Qt.ToolBarArea.TopToolBarArea)
        qtoolbar.setFloatable(False)
        qtoolbar.setMovable(False)
        main_layout.addWidget(qtoolbar)

        qtoolbar.setStyleSheet("""
            QToolButton {
                border: 2px;
                padding: 1px 4px;
                background: transparent;
                border-radius: 4px;
            }
            QToolButton:hover {
                border: 1px;
                background: #c3c3c3;
            }
            QToolButton:selected {
                background: #a8a8a8;
            }
            QToolButton:pressed {
                background: #888888;
            }
        """)

        back_btn = QAction(QIcon("images/back.png"), "Назад", self)
        back_btn.setStatusTip("Вернуться на предыдущую страницу")
        back_btn.triggered.connect(lambda: self.tab_widget.currentWidget().back())
        qtoolbar.addAction(back_btn)

        next_btn = QAction(QIcon("images/forward.png"), "Вперёд", self)
        next_btn.setStatusTip("Перейти на страницу вперёд")
        next_btn.triggered.connect(lambda: self.tab_widget.currentWidget().forward())
        qtoolbar.addAction(next_btn)

        reload_btn = QAction(QIcon("images/reload.png"), "Обновить страницу", self)
        reload_btn.setStatusTip("Перезагрузить страницу")
        reload_btn.triggered.connect(lambda: self.tab_widget.currentWidget().reload())
        qtoolbar.addAction(reload_btn)

        home_btn = QAction(QIcon("images/home.png"), "Домой", self)
        home_btn.setStatusTip("Домой")
        home_btn.triggered.connect(lambda: self.nav_home())
        qtoolbar.addAction(home_btn)

        qtoolbar.addSeparator()

        self.https_icon = QLabel()
        self.https_icon.setPixmap(QPixmap("images/lock.png"))
        qtoolbar.addWidget(self.https_icon)

        self.url_line = QLineEdit()
        self.url_line.returnPressed.connect(self.nav_to_url)
        qtoolbar.addWidget(self.url_line)

        new_tab_btn = QAction(QIcon("images/add-icon.png"), "Новая вкладка", self)
        new_tab_btn.setStatusTip("Открыть новую вкладку")
        new_tab_btn.triggered.connect(lambda: self.add_new_tab())
        qtoolbar.addAction(new_tab_btn)

        info_btn = QAction(QIcon("images/info.png"), "Информация", self)
        info_btn.triggered.connect(self.info)
        qtoolbar.addAction(info_btn)

        self.add_new_tab(QUrl("https://www.google.com"), "Домашняя страница")

        self.shortcut = QShortcut(QKeySequence("F5"), self)
        self.shortcut.activated.connect(lambda: self.tab_widget.currentWidget().reload())

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.show()
        self.setWindowIcon(QIcon("icon/globe.ico"))

    def add_new_tab(self, qurl=QUrl("https://www.google.com"), label="blank"):
        browser = QWebEngineView()
        browser.settings().setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        browser.settings().setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        browser.page().fullScreenRequested.connect(lambda request: request.accept())
        browser.setUrl(qurl)

        tab = self.tab_widget.addTab(browser, label)
        self.tab_widget.setCurrentIndex(tab)

        browser.urlChanged.connect(lambda qurl, browser=browser: self.update_urlbar(qurl, browser))
        browser.loadFinished.connect(lambda _, i=tab, browser=browser:
                                     self.tab_widget.setTabText(tab, browser.page().title()))

    def tab_open_doubleclick(self, i):
        if i == -1:
            self.add_new_tab()

    def current_tab_changed(self, i):
        qurl = self.tab_widget.currentWidget().url()
        self.update_urlbar(qurl, self.tab_widget.currentWidget())
        self.update_title(self.tab_widget.currentWidget())

    def close_current_tab(self, i):
        if self.tab_widget.count() < 2:
            return

        self.tab_widget.removeTab(i)

    def update_title(self, browser):
        if browser != self.tab_widget.currentWidget():
            return
        title = self.tab_widget.currentWidget().page().title()
        self.setWindowTitle(f"{title} - Elixir")

    def info(self):
        QMessageBox.about(self, "Elixir", "Elixir Company 2025")

    def nav_home(self):
        self.tab_widget.currentWidget().setUrl(QUrl("https://www.google.com"))

    def nav_to_url(self):
        qurl = QUrl(self.url_line.text())
        if qurl.scheme() == "":
            qurl.setScheme("http")

        self.tab_widget.currentWidget().setUrl(qurl)

    def update_urlbar(self, url, browser=None):
        if browser != self.tab_widget.currentWidget():
            return

        if url.scheme() == "https":
            self.https_icon.setPixmap(QPixmap("images/lock.png"))
        else:
            self.https_icon.setPixmap(QPixmap("images/unlock.png"))

        self.url_line.setText(url.toString())
        self.url_line.setCursorPosition(0)

    def center_window(self, window):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = window.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        window.move(window_geometry.topLeft())

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

    def toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.isMaximized():
            self.showNormal()
        super().keyPressEvent(event)

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
            self.app.setStyleSheet(
                """
                QWidget {
                    background-color: white;
                    color: black;
                }
                QPushButton {
                    border: none;
                    color: black;
                }
                QLineEdit {
                    background-color: white;
                    color: black;
                    border: 1px solid #ccc;
                    border-radius: 10px;
                    padding: 3px;
                }
                QTabBar {
                    background: #f0f0f0;
                    border-radius: 10px;
                }
                QTabBar::tab {
                    background: #fff;
                    color: #0f0f0f;
                    height: 22px;
                    margin-left: 5px;
                    border-top-left-radius: 10px;
                    border-top-right-radius: 10px;
                }
                QTabBar::tab:selected {
                    background-color: #b3b3b3;
                    color: #000000;
                    padding-left: 5px;
                    padding-right: 5px;
                    border: 1px solid #9e9e9e;
                    border-top-left-radius: 10px;
                    border-top-right-radius: 10px;
                }
                QTabBar::close-button {
                    image: url("images/close.png");
                    subcontrol-position: right;
                }
                """
            )
        else:
            self.app.setStyleSheet(
                """
                QWidget {
                    background-color: black;
                    color: white;
                }
                QPushButton {
                    border: none;
                    color: white;
                }
                QLineEdit {
                    background-color: #333;
                    color: white;
                    border: 1px solid #555;
                    border-radius: 10px;
                    padding: 3px;
                }
                QTabBar {
                    background: #333;
                    border-radius: 10px;
                }
                QTabBar::tab {
                    background: #444;
                    color: #fff;
                    height: 22px;
                    margin-left: 5px;
                    border-top-left-radius: 10px;
                    border-top-right-radius: 10px;
                }
                QTabBar::tab:selected {
                    background-color: #555;
                    color: #fff;
                    padding-left: 5px;
                    padding-right: 5px;
                    border: 1px solid #666;
                    border-top-left-radius: 10px;
                    border-top-right-radius: 10px;
                }
                QTabBar::close-button {
                    image: url("images/close.png");
                    subcontrol-position: right;
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
