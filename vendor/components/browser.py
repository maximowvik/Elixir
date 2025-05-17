import os
import urllib.parse
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEngineDownloadRequest
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QToolBar, QLineEdit, QLabel,
    QMessageBox, QTabWidget, QPushButton, QHBoxLayout, QSpacerItem, QSizePolicy,
    QGraphicsDropShadowEffect, QMenu, QFileDialog
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QKeySequence, QAction, QShortcut, QPainter, QPainterPath, 
    QColor, QPalette
)
from PyQt6.QtCore import QUrl, Qt, QSize, QPoint, QTimer, QRectF, QSettings, QTimer
from .iconmanager import IconManager


class CEFBrowser(QWidget):
    def __init__(self, url="https://www.google.com", parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.browser = None
        self.create_browser(url)

        # Запускаем CEF цикл сообщений через таймер PyQt
        self.timer = QTimer(self)
        self.timer.timeout.connect(cef.MessageLoopWork)
        self.timer.start(10)

    def create_browser(self, url):
        window_info = cef.WindowInfo()
        window_info.SetAsChild(int(self.winId()), [0, 0, self.width(), self.height()])
        self.browser = cef.CreateBrowserSync(window_info, url=url)

    def navigate(self, url):
        if self.browser:
            self.browser.LoadUrl(url)

    def resizeEvent(self, event):
        if self.browser:
            cef.WindowUtils.OnSize(int(self.winId()), 0, 0, 0)
        super().resizeEvent(event)

    def closeEvent(self, event):
        if self.browser:
            self.browser.CloseBrowser(True)
        super().closeEvent(event)

class Browser(QMainWindow):
    def __init__(self, app, theme_manager):
        super().__init__()
        
        # Инициализация основных свойств
        self.app = app
        self.theme_manager = theme_manager
        self.title_buttons = []
        self.downloads = []
        self.closed_tabs = []  # Для восстановления закрытых вкладок
        self._moving = False
        self._move_start_pos = None
        self.normal_geometry = None

        # Настройка WebEngine профиля и параметров
        profile = QWebEngineProfile.defaultProfile()
        settings = profile.settings()
        
        # Включение аппаратного ускорения и важных функций
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
        # Оптимизация производительности
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        
        # Настройка окна браузера
        self.setWindowTitle("My Browser")
        self.setWindowIcon(QIcon(IconManager.get_images("logo_new")))
        self.setMinimumSize(800, 600)
        
        # Прозрачность и отсутствие стандартного заголовка окна
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # Инициализация UI
        self.init_ui()
        
        # Подключение сигналов
        self.theme_manager.theme_changed.connect(self.update_theme)
        
        # Загрузка настроек и начальное состояние
        self.load_settings()
        self.update_theme(self.theme_manager.current_theme())
        self.center_window()
        
        # Создаем начальную вкладку
        self.add_new_tab(QUrl("https://www.google.com"), "Home")

    def init_ui(self):
        # Main widget setup
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Window shadow effect
        self.shadow = QGraphicsDropShadowEffect(central_widget)
        self.shadow.setBlurRadius(20)
        self.shadow.setOffset(0, 0)
        central_widget.setGraphicsEffect(self.shadow)

        self.setup_title_bar(main_layout)
        self.setup_tab_widget(main_layout)
        self.setup_toolbar(main_layout)
        self.setup_shortcuts()
        
        # Add initial tab
        home_url = QUrl.fromUserInput("https://www.google.com")
        self.add_new_tab(home_url, "New Tab")

    def setup_title_bar(self, parent_layout):
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(50)
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.mouseDoubleClickEvent = self.toggle_maximized

        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)
        title_layout.setSpacing(10)


        # Logo and title
        logo = QLabel()
        logo.setPixmap(QPixmap(IconManager.get_images("logo_new")).scaledToWidth(100, Qt.TransformationMode.SmoothTransformation))
        title_layout.addWidget(logo)
        
        # Spacer
        title_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        
        for icon, slot in [(IconManager.get_images("expanded"), self.toggle_maximized),
                        (IconManager.get_images("roll_up_button"), self.showMinimized),
                        (IconManager.get_images("button_close"), self.close)]:
            btn = self.create_title_button(icon, slot)
            title_layout.addWidget(btn)


        parent_layout.addWidget(self.title_bar)

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

    def setup_tab_widget(self, parent_layout):
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        
        # Tab bar events
        self.tab_widget.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.tab_widget.tabCloseRequested.connect(self.close_current_tab)
        self.tab_widget.currentChanged.connect(self.update_current_tab)
        
        # Context menu
        self.tab_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self.show_tab_context_menu)
        
        parent_layout.addWidget(self.tab_widget, 1)

    def setup_toolbar(self, parent_layout):
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setMovable(False)

        # Navigation buttons
        nav_actions = [
            ("back", "Back", lambda: self.navigate_current_tab("back"), "Ctrl+["),
            ("forward", "Forward", lambda: self.navigate_current_tab("forward"), "Ctrl+]"),
            ("refresh", "Refresh", lambda: self.navigate_current_tab("reload"), "F5"),
            ("home", "Home", self.nav_home, "Ctrl+H"),
        ]

        for icon, text, callback, shortcut in nav_actions:
            action = QAction(QIcon(f"icons/{icon}.png"), text, self)
            action.triggered.connect(callback)
            action.setShortcut(QKeySequence(shortcut))
            self.toolbar.addAction(action)

        self.toolbar.addSeparator()

        # Security indicator
        self.security_icon = QLabel()
        self.security_icon.setPixmap(QPixmap("icons/insecure.png"))
        self.security_icon.setToolTip("Connection not secure")
        self.toolbar.addWidget(self.security_icon)

        # URL bar
        self.url_line = QLineEdit()
        self.url_line.setClearButtonEnabled(True)
        self.url_line.setPlaceholderText("Search or enter website address")
        self.url_line.returnPressed.connect(self.nav_to_url)
        self.toolbar.addWidget(self.url_line)

        # New tab button
        new_tab_action = QAction(QIcon("icons/new-tab.png"), "New Tab", self)
        new_tab_action.setShortcut(QKeySequence("Ctrl+T"))
        new_tab_action.triggered.connect(lambda: self.add_new_tab())
        self.toolbar.addAction(new_tab_action)

        # Downloads button
        downloads_action = QAction(QIcon("icons/downloads.png"), "Downloads", self)
        downloads_action.triggered.connect(self.show_downloads)
        self.toolbar.addAction(downloads_action)

        parent_layout.addWidget(self.toolbar)

    def setup_shortcuts(self):
        shortcuts = {
            "Ctrl+W": lambda: self.close_current_tab(self.tab_widget.currentIndex()),
            "Ctrl+L": lambda: self.url_line.setFocus(),
            "Ctrl+N": lambda: Browser(self.app, self.theme_manager).show(),
            "Ctrl+Shift+T": self.restore_closed_tab,
            "Ctrl+Tab": lambda: self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() + 1) % self.tab_widget.count()),
            "Ctrl+Shift+Tab": lambda: self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() - 1) % self.tab_widget.count()),
        }

        for key, callback in shortcuts.items():
            QShortcut(QKeySequence(key), self).activated.connect(callback)

    def add_new_tab(self, qurl=None, label="New Tab", background=False):
        if qurl is None:
            qurl = QUrl.fromUserInput(self.app.clipboard().text().strip()[:200])
            if not qurl.isValid():
                qurl = QUrl("https://www.google.com")

        browser = QWebEngineView()
        settings = browser.settings()
        
        # Security settings
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        
        browser.setUrl(qurl)
        browser.setZoomFactor(1.0)
        
        # Connect signals
        browser.urlChanged.connect(lambda qurl, b=browser: self.update_urlbar(qurl, b))
        browser.loadStarted.connect(lambda: self.tab_widget.setTabIcon(self.tab_widget.indexOf(browser), QIcon("icons/loading.png")))
        browser.loadFinished.connect(self.on_load_finished)
        browser.page().titleChanged.connect(lambda title, b=browser: self.update_tab_title(b, title))
        browser.page().iconChanged.connect(lambda icon, b=browser: self.update_tab_icon(b, icon))
        browser.page().certificateError.connect(self.handle_ssl_error)
        
        # Handle downloads
        profile = browser.page().profile()
        profile.downloadRequested.connect(self.handle_download_request)
        
        tab_index = self.tab_widget.addTab(browser, label)
        if not background:
            self.tab_widget.setCurrentIndex(tab_index)
        
        return browser

    def update_tab_title(self, browser, title):
        index = self.tab_widget.indexOf(browser)
        if index != -1:
            self.tab_widget.setTabText(index, title[:20] + "..." if len(title) > 20 else title)

    def update_tab_icon(self, browser, icon):
        index = self.tab_widget.indexOf(browser)
        if index != -1:
            self.tab_widget.setTabIcon(index, icon)

    def on_load_finished(self, ok):
        browser = self.sender()
        if isinstance(browser, QWebEngineView):
            index = self.tab_widget.indexOf(browser)
            if index != -1:
                self.tab_widget.setTabIcon(index, QIcon())
                if not ok:
                    self.tab_widget.setTabText(index, "Error loading page")

    def update_urlbar(self, qurl, browser=None):
        if browser != self.tab_widget.currentWidget():
            return
            
        self.url_line.setText(qurl.toString())
        self.url_line.setCursorPosition(0)
        
        # Update security icon
        if qurl.scheme() == "https":
            self.security_icon.setPixmap(QPixmap("icons/secure.png"))
            self.security_icon.setToolTip("Secure connection (HTTPS)")
        else:
            self.security_icon.setPixmap(QPixmap("icons/insecure.png"))
            self.security_icon.setToolTip("Insecure connection (HTTP)")

    def nav_to_url(self):
        url_text = self.url_line.text().strip()
        if not url_text:
            return
            
        # Handle search queries
        if ' ' in url_text or '.' not in url_text:
            url = QUrl(f"https://www.google.com/search?q={urllib.parse.quote(url_text)}")
        else:
            # Handle local files
            if os.path.exists(url_text):
                url = QUrl.fromLocalFile(url_text)
            else:
                if not url_text.startswith(('http://', 'https://')):
                    url_text = 'https://' + url_text
                url = QUrl(url_text)
        
        if url.isValid():
            self.tab_widget.currentWidget().setUrl(url)

    def nav_home(self):
        home_url = QUrl.fromUserInput("https://www.google.com")
        self.tab_widget.currentWidget().setUrl(home_url)

    def close_current_tab(self, index):
        if self.tab_widget.count() <= 1:
            self.close()
        else:
            widget = self.tab_widget.widget(index)
            if widget:
                widget.deleteLater()
            self.tab_widget.removeTab(index)

    def tab_open_doubleclick(self, index):
        if index == -1:  # Double-click on empty tab bar area
            self.add_new_tab()

    def show_tab_context_menu(self, position):
        menu = QMenu()
        index = self.tab_widget.tabBar().tabAt(position)
        
        if index >= 0:  # Clicked on a tab
            menu.addAction("Reload Tab", lambda: self.tab_widget.widget(index).reload())
            menu.addAction("Duplicate Tab", lambda: self.add_new_tab(self.tab_widget.widget(index).url()))
            menu.addAction("Close Tab", lambda: self.close_current_tab(index))
            menu.addSeparator()
        
        menu.addAction("New Tab", lambda: self.add_new_tab())
        menu.exec(self.tab_widget.mapToGlobal(position))

    def navigate_current_tab(self, action):
        browser = self.tab_widget.currentWidget()
        if not browser:
            return
            
        if action == "back":
            browser.back()
        elif action == "forward":
            browser.forward()
        elif action == "reload":
            browser.reload()

    def handle_ssl_error(self, error):
        reply = QMessageBox.question(
            self, "SSL Error",
            f"The site's security certificate is not trusted.\n\n{error.errorDescription()}\n\nDo you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            error.ignore()
        else:
            error.reject()

    def handle_download_request(self, download):
        # Suggest download location
        path, _ = QFileDialog.getSaveFileName(
            self, "Save File", 
            os.path.expanduser(f"~/Downloads/{download.downloadFileName()}"),
            "All Files (*)"
        )
        
        if path:
            download.setDownloadDirectory(os.path.dirname(path))
            download.setDownloadFileName(os.path.basename(path))
            download.accept()
            
            # Track download
            self.downloads.append({
                'path': path,
                'received': 0,
                'total': download.totalBytes(),
                'finished': False
            })
            
            download.downloadProgress.connect(lambda bytesReceived, bytesTotal, path=path: 
                self.update_download_progress(path, bytesReceived, bytesTotal))
            download.finished.connect(lambda path=path: self.download_finished(path))

    def update_download_progress(self, path, received, total):
        # Update download progress (could be shown in status bar)
        for dl in self.downloads:
            if dl['path'] == path:
                dl['received'] = received
                dl['total'] = total
                break

    def download_finished(self, path):
        for dl in self.downloads:
            if dl['path'] == path:
                dl['finished'] = True
                break
        QMessageBox.information(self, "Download Complete", f"File saved to:\n{path}")

    def show_downloads(self):
        # Simple downloads manager
        msg = "Downloads:\n\n"
        for dl in self.downloads:
            status = "✓" if dl['finished'] else f"{dl['received']/1024:.1f}/{dl['total']/1024:.1f} KB"
            msg += f"{os.path.basename(dl['path'])} - {status}\n"
        
        QMessageBox.information(self, "Downloads", msg if self.downloads else "No downloads yet")

    def restore_closed_tab(self):
        # TODO: Implement tab restoration from history
        self.add_new_tab()

    def update_current_tab(self, index):
        if index >= 0:
            browser = self.tab_widget.widget(index)
            self.update_urlbar(browser.url(), browser)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background with rounded corners
        bg_color = QColor(self.theme_manager.theme_palette[self.theme_manager.current_theme()]['bg'])
        bg_color.setAlpha(240)
        
        path = QPainterPath()
        rect = QRectF(self.rect())
        path.addRoundedRect(rect, 15, 15)
        
        painter.fillPath(path, bg_color)
        painter.setClipPath(path)
        super().paintEvent(event)

    def update_theme(self, theme):
        theme_vals = self.theme_manager.theme_palette[theme]
        
        # Update shadow
        shadow_alpha = 120 if theme == "light" else 80
        self.shadow.setColor(QColor(0, 0, 0, shadow_alpha))
        
        # Base stylesheet
        base_style = f"""
            #CentralWidget {{
                background-color: {theme_vals['bg']};
                border-radius: 15px;
            }}
            
            QTabWidget::pane {{
                border: 1px solid {theme_vals['border']};
                border-radius: 5px;
                margin-top: 5px;
            }}
            
            QTabBar::tab {{
                padding: 8px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
            }}
            
            QTabBar::tab:selected {{
                background: {theme_vals['hover']};
            }}
            
            QLineEdit {{
                border: 1px solid {theme_vals['border']};
                border-radius: 15px;
                padding: 5px 10px;
            }}
        """
        self.setStyleSheet(base_style)
        
        # Update title buttons
        hover_color = "rgba(255, 255, 255, 0.1)" if theme == "dark" else "rgba(0, 0, 0, 0.1)"
        pressed_color = "rgba(255, 255, 255, 0.2)" if theme == "dark" else "rgba(0, 0, 0, 0.2)"
        
        for btn in self.title_buttons:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 15px;
                }}
                QPushButton:hover {{
                    background: {hover_color};
                }}
                QPushButton:pressed {{
                    background: {pressed_color};
                }}
            """)

    def toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
            if self.normal_geometry:
                self.setGeometry(self.normal_geometry)
        else:
            self.normal_geometry = self.geometry()
            self.showMaximized()

    def center_window(self):
        screen = self.screen().availableGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )

    def title_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._moving = True
            self._move_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def title_mouse_move(self, event):
        if self._moving and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._move_start_pos)
            event.accept()

    def title_mouse_release(self, event):
        self._moving = False
        event.accept()

    def load_settings(self):
        settings = QSettings("MyBrowser", "Settings")
        geometry = settings.value("window_geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # TODO: Load other settings like home page, zoom level, etc.

    def save_settings(self):
        settings = QSettings("MyBrowser", "Settings")
        settings.setValue("window_geometry", self.saveGeometry())
        
        # TODO: Save other settings

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)