# vendor/core/message_widget.py

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

class MessageWidget(QWidget):
    def __init__(self, type_message, text, sender, theme_palette, parent=None):
        super().__init__(parent)
        self.text = text
        self.sender = sender
        self.theme_palette = theme_palette
        self.type_message = type_message

        self.icon_label = QLabel()
        self.text_label = QLabel(self.text)

        self.initUI()

    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        self.text_label.setWordWrap(True)

        if self.sender == "user":
            self.icon_label.setPixmap(QPixmap("./vendor/images/info.png").scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio))
            layout.addStretch()
            layout.addWidget(self.text_label)
            layout.addWidget(self.icon_label)
        elif self.sender == "system":
            layout.addStretch()
            layout.addWidget(self.text_label)
            self.text_label.setFixedWidth(400)
            layout.addStretch()
        else:
            self.icon_label.setPixmap(QPixmap("./vendor/images/computer.png").scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio))
            layout.addWidget(self.icon_label)
            layout.addWidget(self.text_label)
            layout.addStretch()

        self.update_styles()

    def update_theme(self, theme_palette):
        self.theme_palette = theme_palette
        self.update_styles()

    def update_styles(self):
        user_bg = self.theme_palette["hover"]
        bot_bg = self.theme_palette["pressed"]
        fg = self.theme_palette["fg"]
        error_bg = self.theme_palette["bg_error"]
        warning_bg = self.theme_palette["bg_warning"]

        if self.type_message == "error":
            bg_color = error_bg
        elif self.type_message == "warning":
            bg_color = warning_bg
        else:
            bg_color = user_bg if self.sender == "user" else bot_bg

        self.text_label.setStyleSheet(f"""
            background-color: {bg_color};
            color: {fg};
            border-radius: 12px;
            padding: 10px;
            font-size: 12pt;
        """)
