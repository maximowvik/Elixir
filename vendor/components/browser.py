import urllib.parse
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QTabBar, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QLineEdit, QLabel, QMessageBox, QMenu, QFileDialog, QPushButton,
    QSpacerItem, QSizePolicy, QStyle, QStyleOptionTab, QStylePainter, QToolButton
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEngineDownloadRequest
from PyQt6.QtGui import QIcon, QPixmap, QKeySequence, QPainter, QPainterPath, QColor, QShortcut, QTransform, QScreen
from PyQt6.QtCore import QUrl, Qt, QSize, QPoint, QRectF, QSettings, QRect
from .iconmanager import IconManager

class CustomTabBar(QTabBar):
    def __init__(self, browser, parent=None):
        super().__init__(parent)
        self.browser = browser
        self.setExpanding(False)
        self.setUsesScrollButtons(True)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setIconSize(QSize(20, 20))
        self.close_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton)
        self.hovered_close_button = -1  # Индекс вкладки с наведённой кнопкой закрытия

    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        size.setWidth(size.width() + 30)
        return size

    def paintEvent(self, event):
        painter = QStylePainter(self)
        
        for index in range(self.count()):
            option = QStyleOptionTab()
            self.initStyleOption(option, index)
            
            # Рисуем фон вкладки
            painter.drawControl(QStyle.ControlElement.CE_TabBarTabShape, option)
            
            # Получаем прямоугольник вкладки
            tab_rect = self.tabRect(index)
            
            # Рисуем иконку сайта
            icon = self.tabIcon(index)
            if not icon.isNull():
                icon_rect = QRect(
                    tab_rect.left() + 8,
                    tab_rect.center().y() - 10,
                    20, 20
                )
                icon.paint(painter, icon_rect)
            
            # Рисуем текст
            text_rect = QRect(
                tab_rect.left() + (35 if not icon.isNull() else 8),
                tab_rect.top(),
                tab_rect.width() - 40,
                tab_rect.height()
            )
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self.tabText(index)
            )
            
            # Рисуем кнопку закрытия с hover-эффектом
            close_button_rect = QRect(
                tab_rect.right() - 30,
                tab_rect.center().y() - 10,
                20, 20
            )
            
            # Если кнопка hovered - рисуем красный фон
            if index == self.hovered_close_button:
                painter.save()
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 0, 0, 50))  # Полупрозрачный красный
                painter.drawRoundedRect(close_button_rect, 4, 4)
                painter.restore()
            
            self.close_icon.paint(painter, close_button_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            tab_index = self.tabAt(event.position().toPoint())
            if tab_index >= 0:
                self.browser.close_current_tab(tab_index)
        elif event.button() == Qt.MouseButton.LeftButton:
            tab_index = self.tabAt(event.position().toPoint())
            if tab_index >= 0:
                tab_rect = self.tabRect(tab_index)
                close_button_rect = QRect(
                    tab_rect.right() - 30,
                    tab_rect.center().y() - 10,
                    20, 20
                )
                if close_button_rect.contains(event.position().toPoint()):
                    self.browser.close_current_tab(tab_index)
                    return
            
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # Определяем, над какой кнопкой закрытия находится курсор
        new_hovered = -1
        for index in range(self.count()):
            tab_rect = self.tabRect(index)
            close_button_rect = QRect(
                tab_rect.right() - 30,
                tab_rect.center().y() - 10,
                20, 20
            )
            if close_button_rect.contains(event.position().toPoint()):
                new_hovered = index
                break
        
        # Обновляем только если состояние изменилось
        if new_hovered != self.hovered_close_button:
            self.hovered_close_button = new_hovered
            self.update()  # Перерисовываем
        
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        # При выходе курсора с tabbar сбрасываем hover
        if self.hovered_close_button != -1:
            self.hovered_close_button = -1
            self.update()
        super().leaveEvent(event)
                
class Browser(QWidget):
    def __init__(self, theme_manager, translations: dict[str, str]):
        super().__init__()
        self.theme_manager = theme_manager
        self.is_maximized = False
        self._moving = False
        self._move_start = QPoint()
        self.title_buttons = []
        self.downloads = []
        self.closed_urls = []
        self.translations = translations

        self.init_browser_profile()
        self.init_ui()
        self.init_connections()
        self.load_settings()
        self.center_window()
        self.add_new_tab(QUrl("https://google.com"), "Home")
        self.update_theme(self.theme_manager.current_theme())

    def init_browser_profile(self):
        profile = QWebEngineProfile.defaultProfile()
        settings = profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript, False)
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        profile.setHttpCacheMaximumSize(100 * 1024 * 1024)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)

    def init_ui(self):
        # Create a central widget and set a layout
        central_widget = QWidget(objectName="CentralWidget")
        self.setWindowTitle("Elixir Browser")
        self.setWindowIcon(QIcon(IconManager.get_images("browser")))
        self.setMinimumSize(800, 600)

        # Use a layout to manage the central widget's contents
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        self.setup_title_bar(main_layout)
        self.setup_tab_widget(main_layout)
        self.setup_toolbar(main_layout)
        self.setup_shortcuts()

        # Set the central widget with the layout
        self.setLayout(main_layout)

    def setup_title_bar(self, layout):
        if self.theme_manager.get_current_platform() == "windows":
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        title_bar = QWidget(objectName="TitleBar")
        title_bar.setFixedHeight(50)
        title_bar.mouseDoubleClickEvent = self.toggle_maximize

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)
        title_layout.setSpacing(10)

        logo = QLabel()
        pixmap = QPixmap(IconManager.get_images("main_logo"))
        logo.setPixmap(pixmap.scaledToWidth(100, Qt.TransformationMode.SmoothTransformation))
        title_layout.addWidget(logo)
        title_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        if self.theme_manager.get_current_platform() == "windows":
            for icon, handler in [("expanded", self.toggle_maximize), ("roll_up_button", self.showMinimized), ("button_close", self.close)]:
                button = self.theme_manager.create_title_button(IconManager.get_images(icon), handler)
                title_layout.addWidget(button)

        layout.addWidget(title_bar)
        title_bar.mousePressEvent = self.title_mouse_press
        title_bar.mouseMoveEvent = self.title_mouse_move
        title_bar.mouseReleaseEvent = self.title_mouse_release

    def setup_tab_widget(self, layout):
        self.tab_widget = QTabWidget(documentMode=True)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setTabBar(CustomTabBar(self, self.tab_widget))
        self.tab_widget.tabCloseRequested.connect(self.close_current_tab)
        self.tab_widget.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.tab_widget.currentChanged.connect(self.update_current_tab)
        self.tab_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self.show_tab_context_menu)
        self.tab_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.tab_widget, 1)

    def setup_toolbar(self, layout):
        toolbar = QToolBar(movable=False)
        toolbar.setIconSize(QSize(24, 24))

        # Создаем контейнер для кнопок навигации
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(5)

        # Кнопки навигации
        button_data = [
            ("back", "Back", lambda: self.navigate("back"), "Ctrl+["),
            ("forward", "Forward", lambda: self.navigate("forward"), "Ctrl+]"),
            ("reload", "Refresh", lambda: self.navigate("reload"), "F5"),
            ("home", "Home", self.nav_home, "Ctrl+H")
        ]

        for icon, tip, callback, shortcut in button_data:
            button = QPushButton(QIcon(IconManager.get_images(icon)), "")
            button.setToolTip(tip)
            button.clicked.connect(callback)
            button.setShortcut(QKeySequence(shortcut))
            button.setObjectName("tool")
            button.setIconSize(QSize(20, 20))
            buttons_layout.addWidget(button)

        toolbar.addWidget(buttons_widget)

        # Кастомный QLineEdit с иконкой статуса и стилизованной кнопкой очистки
        self.url_line = QLineEdit()
        self.url_line.setPlaceholderText("Search or enter URL")
        self.url_line.setFixedHeight(40)
        self.url_line.returnPressed.connect(self.nav_to_url)
        
        # Создаем виджет-контейнер для QLineEdit
        url_container = QWidget()
        url_layout = QHBoxLayout(url_container)
        url_layout.setContentsMargins(5, 0, 5, 0)
        
        # Иконка статуса безопасности (внутри QLineEdit слева)
        self.sec_icon = QLabel()
        self.sec_icon.setPixmap(QPixmap(IconManager.get_images("unlock")).scaled(15, 15, 
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.sec_icon.setToolTip("Not secure")
        self.sec_icon.setObjectName("icon_secure")
        self.sec_icon.setFixedSize(QSize(50, 40))
        url_layout.addWidget(self.sec_icon)
        url_layout.addWidget(self.url_line)
        
        # Кастомная кнопка очистки (внутри QLineEdit справа)
        clear_button = QToolButton(self.url_line)
        clear_button.setIcon(QIcon(IconManager.get_images("button_close")))
        clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_button.setToolTip("Clear")
        clear_button.setObjectName("clear")
        clear_button.setFixedSize(QSize(30, 30))
        clear_button.setIconSize(QSize(28, 28))
        clear_button.clicked.connect(self.url_line.clear)
        clear_button.move(self.url_line.width() - 25, (self.url_line.height() - 20) // 2)
        
        # Обновляем позицию кнопки при изменении размера
        self.url_line.resizeEvent = lambda e: clear_button.move(
            self.url_line.width() - 45, (self.url_line.height() - 30) // 2)
        
        toolbar.addWidget(url_container)

        # Кнопки новых вкладок и загрузок
        new_tab_button = QPushButton(QIcon(IconManager.get_images("plus")), "")
        new_tab_button.setToolTip("New Tab")
        new_tab_button.clicked.connect(lambda: self.add_new_tab(QUrl("https://google.com"), "Home"))
        new_tab_button.setShortcut(QKeySequence("Ctrl+T"))
        new_tab_button.setObjectName("tool")
        new_tab_button.setIconSize(QSize(20, 20))
        toolbar.addWidget(new_tab_button)

        downloads_button = QPushButton(self.rotate_icon(QIcon(IconManager.get_images("send_link")), 90), "")
        downloads_button.setToolTip("Downloads")
        downloads_button.clicked.connect(self.show_downloads)
        downloads_button.setObjectName("tool")
        downloads_button.setIconSize(QSize(20, 20))
        toolbar.addWidget(downloads_button)

        layout.addWidget(toolbar)

    def rotate_icon(self, icon: QIcon, degrees: float) -> QIcon:
        if icon.isNull():
            return QIcon()

        available_sizes = icon.availableSizes()
        if not available_sizes:
            return QIcon()

        size = available_sizes[0]
        pixmap = icon.pixmap(size)
        if pixmap.isNull():
            return QIcon()

        transform = QTransform().rotate(degrees)
        rotated_pixmap = pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        return QIcon(rotated_pixmap)

    def setup_shortcuts(self):
        shortcut_mapping = {
            "Ctrl+W": lambda: self.close_current_tab(self.tab_widget.currentIndex()),
            "Ctrl+L": lambda: self.url_line.setFocus(),
            "Ctrl+Shift+T": self.restore_closed_tab,
            "Ctrl+Tab": lambda: self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() + 1) % self.tab_widget.count()),
            "Ctrl+Shift+Tab": lambda: self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() - 1) % self.tab_widget.count()),
        }
        for sequence, callback in shortcut_mapping.items():
            QShortcut(QKeySequence(sequence), self).activated.connect(callback)

    def init_connections(self):
        self.theme_manager.theme_changed.connect(self.update_theme)
        self.update_theme(self.theme_manager.current_theme())

    def update_current_tab(self, index: int):
        if index < 0:
            return
        widget = self.tab_widget.widget(index)
        if isinstance(widget, QWebEngineView):
            self.update_urlbar(widget.url(), widget)

    def add_new_tab(self, qurl: QUrl = None, label="New Tab"):
        if qurl is None:
            text = self.app.clipboard().text().strip()
            qurl = QUrl.fromUserInput(text) if "." in text else QUrl("https://google.com")

        browser = QWebEngineView()
        settings = browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        browser.setZoomFactor(1.0)
        browser.urlChanged.connect(lambda u, b=browser: self.update_urlbar(u, b))
        browser.loadFinished.connect(self.on_load_finished)
        browser.page().titleChanged.connect(lambda t, b=browser: self.update_tab_title(b, t))
        browser.page().iconChanged.connect(lambda i, b=browser: self.update_tab_icon(b, i))
        browser.page().certificateError.connect(self.handle_ssl_error)
        browser.page().profile().downloadRequested.connect(self.handle_download_request)
        browser.setUrl(qurl)

        idx = self.tab_widget.addTab(browser, label)
        self.tab_widget.setCurrentIndex(idx)
        return browser

    def update_tab_title(self, browser, title):
        idx = self.tab_widget.indexOf(browser)
        if idx != -1:
            self.tab_widget.setTabText(idx, title[:20] + ("…" if len(title) > 20 else ""))

    def update_tab_icon(self, browser, icon):
        idx = self.tab_widget.indexOf(browser)
        if idx != -1:
            self.tab_widget.setTabIcon(idx, icon)

    def on_load_finished(self, ok):
        browser = self.sender()
        idx = self.tab_widget.indexOf(browser)
        if idx != -1 and not ok:
            self.tab_widget.setTabText(idx, "Error")

    def update_urlbar(self, qurl, browser=None):
        if browser != self.tab_widget.currentWidget():
            return
        self.url_line.setText(qurl.toString())
        self.url_line.setCursorPosition(0)
        if qurl.scheme() == "https":
            self.sec_icon.setPixmap(QPixmap(IconManager.get_images("lock")))
            self.sec_icon.setToolTip("HTTPS")
        else:
            self.sec_icon.setPixmap(QPixmap(IconManager.get_images("unlock")))
            self.sec_icon.setToolTip("HTTP")

    def nav_to_url(self):
        text = self.url_line.text().strip()
        if not text:
            return
        if " " in text or "." not in text:
            url = QUrl(f"https://www.google.com/search?q={urllib.parse.quote(text)}")
        elif os.path.exists(text):
            url = QUrl.fromLocalFile(text)
        else:
            if not text.startswith(("http://", "https://")):
                text = "https://" + text
            url = QUrl(text)
        self.tab_widget.currentWidget().setUrl(url)

    def navigate(self, action):
        widget = self.tab_widget.currentWidget()
        getattr(widget, action)()

    def nav_home(self):
        self.tab_widget.currentWidget().setUrl(QUrl("https://google.com"))

    def close_current_tab(self, idx):
        widget = self.tab_widget.widget(idx)
        url = widget.url() if isinstance(widget, QWebEngineView) else None
        if url:
            self.closed_urls.append(url)
        self.tab_widget.removeTab(idx)

        if self.tab_widget.count() == 0:
            self.add_new_tab(QUrl("https://google.com"), "Home")
        else:
            if idx < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(idx)
            else:
                self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1)

    def tab_open_doubleclick(self, idx):
        if idx == -1:
            self.add_new_tab()

    def show_tab_context_menu(self, position):
        menu = QMenu()
        idx = self.tab_widget.tabBar().tabAt(position)
        if idx >= 0:
            menu.addAction("Reload", lambda: self.tab_widget.widget(idx).reload())
            menu.addAction("Duplicate", lambda: self.add_new_tab(self.tab_widget.widget(idx).url()))
            menu.addAction("Close", lambda: self.close_current_tab(idx))
            menu.addSeparator()
        menu.addAction("New Tab", self.add_new_tab)
        menu.exec(self.tab_widget.mapToGlobal(position))

    def restore_closed_tab(self):
        if self.closed_urls:
            self.add_new_tab(self.closed_urls.pop())

    def handle_ssl_error(self, error):
        QMessageBox.warning(self, "Security Warning", "Website security certificate is not trusted")
        error.ignore()

    def handle_download_request(self, download_request: QWebEngineDownloadRequest):
        path, _ = QFileDialog.getSaveFileName(self, "Save As", os.path.expanduser(f"~/Downloads/{download_request.downloadFileName()}"))
        if not path:
            return
        download_request.setDownloadDirectory(os.path.dirname(path))
        download_request.setDownloadFileName(os.path.basename(path))
        download_request.accept()
        info = {"path": path, "rec": 0, "tot": download_request.totalBytes(), "done": False}
        self.downloads.append(info)
        download_request.downloadProgress.connect(lambda received, total, p=path: self.update_download_progress(p, received, total))
        download_request.finished.connect(lambda p=path: self.download_finished(p))

    def update_download_progress(self, path, received, total):
        for download in self.downloads:
            if download["path"] == path:
                download["rec"], download["tot"] = received, total

    def download_finished(self, path):
        for download in self.downloads:
            if download["path"] == path:
                download["done"] = True
        QMessageBox.information(self, "Download Complete", f"Saved to:\n{path}")

    def show_downloads(self):
        if not self.downloads:
            QMessageBox.information(self, "Downloads", "No downloads yet")
            return
        message = "\n".join(f"{os.path.basename(d['path'])} - " + ("✓" if d["done"] else f"{d['rec']/1024:.1f}/{d['tot']/1024:.1f} KB") for d in self.downloads)
        QMessageBox.information(self, "Downloads", message)

    def toggle_maximize(self, *args):
        if self.is_maximized:
            self.showNormal()
        else:
            self.showMaximized()
        self.is_maximized = not self.is_maximized

    def title_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.is_maximized:
            self._moving = True
            self._move_start = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def title_mouse_move(self, event):
        if self._moving and event.buttons() & Qt.MouseButton.LeftButton and not self.is_maximized:
            self.move(event.globalPosition().toPoint() - self._move_start)
            event.accept()

    def title_mouse_release(self, event):
        self._moving = False
        event.accept()


    def update_theme(self, theme: str):
        palette = self.theme_manager.theme_palette[theme]
        stylesheet = f"""
            #CentralWidget {{
                background-color: {palette['bg']};
                border-radius: 15px;
            }}
            QTabWidget::pane {{
                border: 1px solid {palette['border']};
                border-radius: 5px;
                margin-top: 5px;
            }}
            QPushButton#tool {{
                background-color: {palette['bg']};
                color: {palette['fg']};
                padding: 10px;
                border: 1px solid {palette['border']};
                border-radius: 5px;
                margin: 2px;
            }}
            QPushButton:hover#tool {{
                background-color: {palette['hover']};
            }}
            QPushButton#clear {{
                background: {palette['bg']};
                color: {palette['fg']};
            }}
            QTabBar::tab {{
                padding: 8px;
                border-radius: 5px;
                border: 1px solid {palette['border']};
                background: {palette['bg']};
                color: {palette['fg']};
                margin-right: 5px;
            }}
            QTabBar::tab:selected {{
                background: {palette['hover']};
                border: 1px solid {palette['border']};
                color: {palette['fg']};
            }}
            QLineEdit {{
                background: {palette['hover']};
                border: 1px solid {palette['border']};
                color: {palette['fg']};
                border-width: 1px 1px 1px 0;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
                padding: 10px;
                margin-right: 10px;
                margin-left: -5px;
            }}
            QLabel#icon_secure {{
                background: {palette['hover']};
                padding: 0px;
                border: 1px solid {palette['border']};
                border-width: 1px 0px 1px 1px;
                border-top-left-radius: 5px;
                border-bottom-left-radius: 5px;
                margin-right: -5px;
                margin-left: 5px;
                padding-left: 5px;
            }}
        """
        self.setStyleSheet(stylesheet)

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

    def load_settings(self):
        settings = QSettings("ElixirBrowser", "Settings")
        if geometry := settings.value("geometry"):
            self.restoreGeometry(geometry)

    def save_settings(self):
        settings = QSettings("ElixirBrowser", "Settings")
        settings.setValue("geometry", self.saveGeometry())

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)