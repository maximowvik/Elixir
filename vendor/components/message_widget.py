from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton, QApplication, QTextEdit, QMenu
from PyQt6.QtGui import QPixmap, QCursor, QIcon, QPainter, QAction
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtSvgWidgets import QSvgWidget
import base64
from io import BytesIO
from .iconmanager import IconManager

class HoverLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._hover_callback = None
        self._leave_callback = None
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        menu.setStyleSheet("""
            QMenu {
                background-color: #2D2D2D;
                border: none;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 6px;
                margin: 2px;
                color: #FFFFFF;
            }
            QMenu::item:selected {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        copy_action = QAction("Копировать выделенное", self)
        copy_action.triggered.connect(self.copy_selected)
        menu.addAction(copy_action)
        menu.exec(self.mapToGlobal(pos))

    def copy_selected(self):
        selected_text = self.selectedText()
        if selected_text:
            QApplication.clipboard().setText(selected_text)

    def enterEvent(self, event):
        if self._hover_callback:
            self._hover_callback()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._leave_callback:
            self._leave_callback()
        super().leaveEvent(event)

    def set_hover_callback(self, callback):
        self._hover_callback = callback

    def set_leave_callback(self, callback):
        self._leave_callback = callback

class HoverButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        self._hover_callback = None
        self._leave_callback = None

    def enterEvent(self, event):
        if self._hover_callback:
            self._hover_callback()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._leave_callback:
            self._leave_callback()
        super().leaveEvent(event)

    def set_hover_callback(self, callback):
        self._hover_callback = callback

    def set_leave_callback(self, callback):
        self._leave_callback = callback

class MessageWidget(QWidget):
    def __init__(self, type_message, text, sender, theme_palette, parent=None):
        super().__init__(parent)
        self.text = text
        self.sender = sender
        self.theme_palette = theme_palette
        self.type_message = type_message
        self._hovered = False
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(100)
        self._hover_timer.timeout.connect(self._hide_copy_button)

        self.icon_label = QSvgWidget()
        self.text_label = HoverLabel(self.text)
        self.copy_button = HoverButton("Copy")
        self.copy_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.copy_button.setFixedSize(90, 40)
        self.copy_button.clicked.connect(self.copy_text)
        self.copy_button.hide()

        self.text_label.set_hover_callback(self._show_copy_button)
        self.text_label.set_leave_callback(self._delayed_hide_copy_button)
        self.copy_button.set_hover_callback(self._show_copy_button)
        self.copy_button.set_leave_callback(self._delayed_hide_copy_button)

        self.initUI()

    def _get_fluent_copy_icon(self, color: str, size: int = 20) -> QIcon:
        # SVG Fluent Copy (outline)
        svg = f'''<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M7 7V5.75C7 4.23122 8.23122 3 9.75 3H16.25C17.7688 3 19 4.23122 19 5.75V12.25C19 13.7688 17.7688 15 16.25 15H15V17.25C15 18.7688 13.7688 20 12.25 20H7.75C6.23122 20 5 18.7688 5 17.25V9.75C5 8.23122 6.23122 7 7.75 7H7Z" stroke="{color}" stroke-width="1.5"/>
<rect x="9" y="9" width="8" height="8" rx="2" fill="none" stroke="{color}" stroke-width="1.5"/>
</svg>'''
        # SVG -> QPixmap
        from PyQt6.QtSvg import QSvgRenderer
        image = QPixmap(size, size)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        renderer = QSvgRenderer(bytearray(svg, encoding='utf-8'))
        renderer.render(painter)
        painter.end()
        return QIcon(image)

    def _show_copy_button(self):
        self.copy_button.show()
        self._hovered = True
        self._hover_timer.stop()

    def _delayed_hide_copy_button(self):
        self._hovered = False
        self._hover_timer.start()

    def _hide_copy_button(self):
        if not self._hovered:
            self.copy_button.hide()

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        self.text_label.setWordWrap(True)

        if self.sender == "user":
            self.icon_label.load(IconManager.get_images("user"))
            self.icon_label.setFixedSize(32, 32)
            layout.addStretch()
            layout.addWidget(self.copy_button)
            layout.addWidget(self.text_label)
            layout.addWidget(self.icon_label)
        elif self.sender == "system":
            layout.addStretch()
            layout.addWidget(self.text_label)
            layout.addWidget(self.copy_button)
            self.text_label.setFixedWidth(400)
            layout.addStretch()
        else:
            self.icon_label.load(IconManager.get_images("bot"))
            self.icon_label.setFixedSize(32, 32)
            layout.addWidget(self.icon_label)
            layout.addWidget(self.text_label)
            layout.addWidget(self.copy_button)
            layout.addStretch()

        self.update_styles()

    def copy_text(self):
        clipboard = QApplication.instance().clipboard()
        clipboard.setText(self.text)

    def update_theme(self, theme_palette):
        self.theme_palette = theme_palette
        self.update_styles()

    def update_styles(self):
        border = self.theme_palette["border"]
        main_bg = self.theme_palette["hover"]
        fg = self.theme_palette["fg"]
        error_bg = self.theme_palette["bg_error"]
        warning_bg = self.theme_palette["bg_warning"]
        hover_color = self.theme_palette["hover"]
        pressed_color = self.theme_palette["pressed"]
        
        # Устанавливаем иконку с нужным цветом
        self.copy_button.setIcon(self._get_fluent_copy_icon(fg))
        self.copy_button.setStyleSheet(f"""
            QPushButton {{
                padding: 8px;
                font-size: 12pt;
                border: 1px solid {border};
                background-color: {main_bg};
                color: {fg};
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 0, 0, 0.1);
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
        """)

        if self.type_message == "error":
            bg_color = error_bg
            fg = self.theme_palette["fg_message"]
        elif self.type_message == "warning":
            bg_color = warning_bg
            fg = self.theme_palette["fg_message"]
        elif self.type_message == "info":
            bg_color = self.theme_palette["bg_info"]
            fg = self.theme_palette["fg_message"]
        else:
            bg_color = main_bg
            fg = self.theme_palette["fg"]

        self.text_label.setStyleSheet(f"""
            background-color: {bg_color};
            color: {fg};
            border-radius: 12px;
            padding: 10px;
            font-size: 12pt;
        """)
        
