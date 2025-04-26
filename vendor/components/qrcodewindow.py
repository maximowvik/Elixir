import qrcode
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QSpacerItem,
    QSizePolicy, QLineEdit, QFileDialog, QComboBox
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath, QFont
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint
from PyQt6.QtGui import QScreen
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from .iconmanager import IconManager


class QRCodeWindow(QWidget):
    def __init__(self, language, theme_manager):
        super().__init__()
        self._old_pos = None
        self.language = language
        self.theme_manager = theme_manager
        self.theme = self.theme_manager.current_theme()
        self.translations = self.load_translations(self.language)

        self.theme_manager.theme_changed.connect(self.on_theme_changed)
        self.initUI()

    def load_translations(self, language):
        with open(f"./vendor/core/language/{language}.json", "r", encoding="utf-8") as file:
            return json.load(file)

    def initUI(self):
        self.setWindowTitle(self.translations["qr_code_window_title"])
        self.setWindowIcon(IconManager.get_icon("qr_code"))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        title = QHBoxLayout()
        title.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        for icon, slot in [(IconManager.get_images("roll_up_button"), self.showMinimized), (IconManager.get_images("button_close"), self.close)]:
            btn = self.create_title_button(icon, slot)
            title.addWidget(btn)
        self.main_layout.addLayout(title)

        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText(self.translations["url_input_placeholder"])
        self.main_layout.addWidget(self.url_input)

        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["PNG", "JPG", "PDF"])
        self.main_layout.addWidget(self.format_combo)

        self.save_button = QPushButton(self.translations["save_button"], self)
        self.save_button.clicked.connect(self.save_qr_code)
        self.main_layout.addWidget(self.save_button)

        self.update_styles()
        self.center_window()

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

    def update_styles(self):
        palette = self.theme_manager.theme_palette[self.theme]
        fg = palette["fg"]
        bg = palette["bg"]
        border = palette["border"]
        hover = palette["hover"]
        pressed = palette["pressed"]

        font = "Segoe UI"

        self.setStyleSheet(f"background-color: transparent;")
        self.url_input.setStyleSheet(f"""
            background-color: {bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 10px;
            font-size: 13pt;
            font-family: '{font}';
        """)
        self.format_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 10px;
                font-size: 13pt;
                font-family: '{font}';
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)
        self.save_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border-radius: 6px;
                padding: 10px;
                font-size: 13pt;
                font-family: '{font}';
                border: 1px solid {border};
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {pressed};
            }}
        """)

    def on_theme_changed(self, new_theme):
        self.theme = new_theme
        self.update_styles()
        self.update()

    def save_qr_code(self):
        url = self.url_input.text()
        if not url:
            return

        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')

        file_format = self.format_combo.currentText().lower()
        file_path, _ = QFileDialog.getSaveFileName(
            self, self.translations["save_qr_code_dialog_title"], "",
            f"{file_format.upper()} Files (*.{file_format})"
        )
        if file_path:
            temp_qr_path = "temp_qr.png"
            img.save(temp_qr_path)

            if file_format == "pdf":
                c = canvas.Canvas(file_path, pagesize=letter)
                width, height = letter
                c.drawImage(temp_qr_path, (width - img.size[0]) / 2, (height - img.size[1]) / 2,
                            width=img.size[0], height=img.size[1])
                c.save()
            else:
                img.save(file_path)

            os.remove(temp_qr_path)

    def center_window(self):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        qr = self.frameGeometry()
        cp = screen.center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.fillPath(path, QColor(self.theme_manager.theme_palette[self.theme]["bg"]))
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
