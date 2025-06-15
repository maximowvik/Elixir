import urllib.parse
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QTabBar, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QLineEdit, QLabel, QMessageBox, QMenu, QFileDialog,
    QPushButton, QSpacerItem, QSizePolicy
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile, QWebEngineDownloadRequest
from PyQt6.QtGui import QIcon, QPixmap, QKeySequence, QPainter, QPainterPath, QColor, QAction, QShortcut, QTransform
from PyQt6.QtCore import QUrl, Qt, QSize, QPoint, QRectF, QSettings
import os
from .iconmanager import IconManager  # Ваш менеджер ресурсов


class ScrollableTabBar(QTabBar):
    """QTabBar с кнопками прокрутки и колесиком мыши."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setExpanding(False)
        self.setUsesScrollButtons(True)
        self.setElideMode(Qt.TextElideMode.ElideRight)

    def wheelEvent(self, e):
        delta = e.angleDelta().y()
        step = 1
        direction = -step if delta > 0 else step
        self.scrollTabs(direction)          

    def scrollTabs(self, direction: int):
        count = self.count()
        if count == 0:
            return
        current = self.currentIndex()
        nxt = max(0, min(count - 1, current + direction))
        if nxt != current:
            self.parent().setCurrentIndex(nxt)


class Browser(QMainWindow):
    def __init__(self, app: QApplication, theme_manager):
        super().__init__()
        self.app = app
        self.theme_manager = theme_manager

        # внутренние состояния
        self.is_maximized = False
        self._moving = False
        self._move_start = QPoint()
        self.title_buttons = []
        self.downloads = []
        self.closed_urls = []

        # инициализация
        self.init_browser_profile()
        self.init_window_params()
        self.init_ui()
        self.init_connections()
        self.load_settings()
        self.center_window()

        # стартовая вкладка
        self.add_new_tab(QUrl("https://google.com"), "Home")

    # 1) WebEngine профиль
    def init_browser_profile(self):
        p = QWebEngineProfile.defaultProfile()
        s = p.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, False)
        s.setAttribute(QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript, False)
        p.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        p.setHttpCacheMaximumSize(100 * 1024 * 1024)
        p.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)

    # 2) Параметры главного окна
    def init_window_params(self):
        self.setWindowTitle("Elixir Browser")
        self.setWindowIcon(QIcon(IconManager.get_images("browser")))
        self.setMinimumSize(800, 600)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

    # 3) UI: title bar, tabs, toolbar, shortcuts
    def init_ui(self):
        # центральный виджет и layout
        cw = QWidget(objectName="CentralWidget")
        self.setCentralWidget(cw)
        main_l = QVBoxLayout(cw)
        main_l.setContentsMargins(15,15,15,15)
        main_l.setSpacing(10)

        self.setup_title_bar(main_l)
        self.setup_tab_widget(main_l)
        self.setup_toolbar(main_l)
        self.setup_shortcuts()

    def setup_title_bar(self, layout):
        bar = QWidget(objectName="TitleBar")
        bar.setFixedHeight(50)
        bar.mouseDoubleClickEvent = self.toggle_maximize

        h = QHBoxLayout(bar)
        h.setContentsMargins(10,5,10,5)
        h.setSpacing(10)

        # логотип
        logo = QLabel()
        pix = QPixmap(IconManager.get_images("main_logo"))
        logo.setPixmap(pix.scaledToWidth(100, Qt.TransformationMode.SmoothTransformation))
        h.addWidget(logo)
        h.addItem(QSpacerItem(40,20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # кнопки заголовка
        for icon, slot in [
            ("expanded", self.toggle_maximize),
            ("roll_up_button", self.showMinimized),
            ("button_close", self.close)
        ]:
            btn = QPushButton()
            btn.setIcon(QIcon(IconManager.get_images(icon)))
            btn.setIconSize(QSize(30,30))
            btn.setFixedSize(40,40)
            btn.setStyleSheet("""
                QPushButton{background:transparent;border:none;border-radius:8px;}
                QPushButton:hover{background:rgba(0,0,0,30);}
                QPushButton:pressed{background:rgba(0,0,0,50);}
            """)
            btn.clicked.connect(slot)
            self.title_buttons.append(btn)
            h.addWidget(btn)

        layout.addWidget(bar)
        # drag handlers
        bar.mousePressEvent   = self.title_mouse_press
        bar.mouseMoveEvent    = self.title_mouse_move
        bar.mouseReleaseEvent = self.title_mouse_release

    def setup_tab_widget(self, layout):
        self.tab_widget = QTabWidget(documentMode=True)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)

        # заменяем tabBar
        self.tab_widget.setTabBar(ScrollableTabBar())

        # сигналы
        self.tab_widget.tabCloseRequested.connect(self.close_current_tab)
        self.tab_widget.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.tab_widget.currentChanged.connect(self.update_current_tab)
        self.tab_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self.show_tab_context_menu)

        layout.addWidget(self.tab_widget, 1)

    def setup_toolbar(self, layout):
        tb = QToolBar(movable=False)
        tb.setIconSize(QSize(24,24))

        # навигация
        for icon, tip, cb, sc in [
            ("back", "Back", lambda: self.navigate("back"), "Ctrl+["),
            ("forward", "Forward", lambda: self.navigate("forward"), "Ctrl+]"),
            ("reload", "Refresh", lambda: self.navigate("reload"), "F5"),
            ("home", "Home", self.nav_home, "Ctrl+H"),
        ]:
            act = QAction(QIcon(IconManager.get_images(icon)), tip, self)
            act.triggered.connect(cb)
            act.setShortcut(QKeySequence(sc))
            tb.addAction(act)
        tb.addSeparator()

        # индикатор
        self.sec_icon = QLabel()
        self.sec_icon.setPixmap(QPixmap(IconManager.get_images("unlock")))
        self.sec_icon.setToolTip("Not secure")
        tb.addWidget(self.sec_icon)

        # URL
        self.url_line = QLineEdit()
        self.url_line.setPlaceholderText("Search or enter URL")
        self.url_line.setClearButtonEnabled(True)
        self.url_line.returnPressed.connect(self.nav_to_url)
        tb.addWidget(self.url_line)

        # новые вкладки + загрузки
        nt = QAction(QIcon(IconManager.get_images("plus")), "New Tab", self)
        nt.triggered.connect(lambda: self.add_new_tab())
        nt.setShortcut(QKeySequence("Ctrl+T"))
        tb.addAction(nt)

        dl = QAction(self.rotate_icon(QIcon(IconManager.get_images("send_link")), 90), "Downloads", self)
        dl.triggered.connect(self.show_downloads)
        tb.addAction(dl)

        layout.addWidget(tb)

    def rotate_icon(self, icon: QIcon, degrees: float) -> QIcon:
        pixmap = icon.pixmap(icon.availableSizes()[0])  # Получаем QPixmap из QIcon
        transform = QTransform().rotate(degrees)        # Создаем трансформацию поворота
        rotated_pixmap = pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        return QIcon(rotated_pixmap)                    # Создаем новый QIcon из повернутого QPixmap


    def setup_shortcuts(self):
        mapping = {
            "Ctrl+W": lambda: self.close_current_tab(self.tab_widget.currentIndex()),
            "Ctrl+L": lambda: self.url_line.setFocus(),
            "Ctrl+Shift+T": self.restore_closed_tab,
            "Ctrl+Tab": lambda: self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex()+1)%self.tab_widget.count()),
            "Ctrl+Shift+Tab": lambda: self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex()-1)%self.tab_widget.count()),
        }
        for seq, cb in mapping.items():
            QShortcut(QKeySequence(seq), self).activated.connect(cb)

    # 4) ThemeManager
    def init_connections(self):
        self.theme_manager.theme_changed.connect(self.update_theme)
        self.update_theme(self.theme_manager.current_theme())
        
    def update_current_tab(self, index: int):
        if index < 0:
            return
        widget = self.tab_widget.widget(index)
        # Если в вкладке наш QWebEngineView, обновляем URL‑бар
        if isinstance(widget, QWebEngineView):
            self.update_urlbar(widget.url(), widget)
    # 5) Tabs logic
    def add_new_tab(self, qurl: QUrl=None, label="New Tab"):
        if qurl is None:
            text = self.app.clipboard().text().strip()
            qurl = QUrl.fromUserInput(text) if "." in text else QUrl("https://google.com")
        browser = QWebEngineView()
        # security & perf
        s = browser.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
        s.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
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

    def update_tab_title(self, b, title):
        idx = self.tab_widget.indexOf(b)
        if idx != -1:
            self.tab_widget.setTabText(idx, title[:20] + ("…" if len(title)>20 else ""))

    def update_tab_icon(self, b, icon):
        idx = self.tab_widget.indexOf(b)
        if idx != -1:
            self.tab_widget.setTabIcon(idx, icon)

    def on_load_finished(self, ok):
        br = self.sender()
        idx = self.tab_widget.indexOf(br)
        if idx != -1 and not ok:
            self.tab_widget.setTabText(idx, "Error")

    # 6) Navigation
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
        if not text: return
        if " " in text or "." not in text:
            url = QUrl(f"https://www.google.com/search?q={urllib.parse.quote(text)}")
        elif os.path.exists(text):
            url = QUrl.fromLocalFile(text)
        else:
            if not text.startswith(("http://","https://")):
                text = "https://" + text
            url = QUrl(text)
        self.tab_widget.currentWidget().setUrl(url)

    def navigate(self, action):
        w = self.tab_widget.currentWidget()
        getattr(w, action)()

    def nav_home(self):
        self.tab_widget.currentWidget().setUrl(QUrl("https://google.com"))

    # 7) Tabs context & restore
    def close_current_tab(self, idx):
        w = self.tab_widget.widget(idx)
        url = w.url() if isinstance(w, QWebEngineView) else None
        if url:
            self.closed_urls.append(url)
        if self.tab_widget.count() > 1:
            self.tab_widget.removeTab(idx)
        else:
            self.close()

    def tab_open_doubleclick(self, idx):
        if idx == -1:
            self.add_new_tab()

    def show_tab_context_menu(self, pt):
        menu = QMenu()
        idx = self.tab_widget.tabBar().tabAt(pt)
        if idx >= 0:
            menu.addAction("Reload", lambda: self.tab_widget.widget(idx).reload())
            menu.addAction("Duplicate", lambda: self.add_new_tab(self.tab_widget.widget(idx).url()))
            menu.addAction("Close", lambda: self.close_current_tab(idx))
            menu.addSeparator()
        menu.addAction("New Tab", self.add_new_tab)
        menu.exec(self.tab_widget.mapToGlobal(pt))

    def restore_closed_tab(self):
        if self.closed_urls:
            self.add_new_tab(self.closed_urls.pop())

    # 8) SSL & Downloads
    def handle_ssl_error(self, err):
        QMessageBox.warning(self, "Security Warning", "Website security certificate is not trusted")
        err.ignore() 

    def handle_download_request(self, dl: QWebEngineDownloadRequest):
        path, _ = QFileDialog.getSaveFileName(self, "Save As",
                                              os.path.expanduser(f"~/Downloads/{dl.downloadFileName()}"))
        if not path: return
        dl.setDownloadDirectory(os.path.dirname(path))
        dl.setDownloadFileName(os.path.basename(path))
        dl.accept()
        info = {"path": path, "rec": 0, "tot": dl.totalBytes(), "done": False}
        self.downloads.append(info)
        dl.downloadProgress.connect(lambda r, t, p=path: self.update_download_progress(p, r, t))
        dl.finished.connect(lambda p=path: self.download_finished(p))

    def update_download_progress(self, path, rec, tot):
        for i in self.downloads:
            if i["path"] == path:
                i["rec"], i["tot"] = rec, tot

    def download_finished(self, path):
        for i in self.downloads:
            if i["path"] == path:
                i["done"] = True
        QMessageBox.information(self, "Download Complete", f"Saved to:\n{path}")

    def show_downloads(self):
        if not self.downloads:
            QMessageBox.information(self, "Downloads", "No downloads yet")
            return
        msg = "\n".join(
            f"{os.path.basename(d['path'])} - "
            + ( "✓" if d["done"] else f"{d['rec']/1024:.1f}/{d['tot']/1024:.1f} KB" )
            for d in self.downloads
        )
        QMessageBox.information(self, "Downloads", msg)

    # 9) Drag title bar
    def toggle_maximize(self, *args):
        if self.is_maximized:
            self.showNormal()
        else:
            self.showMaximized()
        self.is_maximized = not self.is_maximized

    def title_mouse_press(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton and not self.is_maximized:
            self._moving = True
            self._move_start = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
            ev.accept()

    def title_mouse_move(self, ev):
        if self._moving and ev.buttons() & Qt.MouseButton.LeftButton and not self.is_maximized:
            self.move(ev.globalPosition().toPoint() - self._move_start)
            ev.accept()

    def title_mouse_release(self, ev):
        self._moving = False
        ev.accept()

    # 10) Paint corners, theme
    def paintEvent(self, ev):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.theme_manager.theme_palette[self.theme_manager.current_theme()]
        c = QColor(pal['bg']); c.setAlpha(240)
        path = QPainterPath(); path.addRoundedRect(QRectF(self.rect()), 15, 15)
        painter.fillPath(path, c)
        painter.setClipPath(path)
        super().paintEvent(ev)

    def update_theme(self, theme: str):
        pal = self.theme_manager.theme_palette[theme]
        ss = f"""
            #CentralWidget {{ background-color: {pal['bg']}; border-radius:15px; }}
            QTabWidget::pane {{ border:1px solid {pal['border']}; border-radius:5px; margin-top:5px; }}
            QTabBar::tab {{ padding:8px; border-top-left-radius:5px; border-top-right-radius:5px;
                            background:{pal['bg']}; color:{pal['fg']}; }}
            QTabBar::tab:selected {{ background:{pal['hover']}; }}
            QLineEdit {{ border:1px solid {pal['border']}; border-radius:15px; padding:5px 10px; }}
        """
        self.setStyleSheet(ss)

    # 11) Settings
    def center_window(self):
        geo = self.screen().availableGeometry()
        self.move((geo.width()-self.width())//2, (geo.height()-self.height())//2)

    def load_settings(self):
        s = QSettings("ElixirBrowser", "Settings")
        if g := s.value("geometry"):
            self.restoreGeometry(g)

    def save_settings(self):
        s = QSettings("ElixirBrowser", "Settings")
        s.setValue("geometry", self.saveGeometry())

    def closeEvent(self, ev):
        self.save_settings()
        super().closeEvent(ev)