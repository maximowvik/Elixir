import os
import tempfile
import segno
from PIL import Image
from PyQt6.QtCore import Qt, QRectF, QPoint
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QScreen
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLineEdit, QPushButton,
    QSpacerItem, QSizePolicy, QVBoxLayout, QWidget, QComboBox, QColorDialog, QLabel
)
from .iconmanager import IconManager

class QRCodeWindow(QWidget):
    TEMP_SUFFIX = ".png"

    def __init__(self, theme_manager, translations: dict[str, str]) -> None:
        super().__init__()
        self._old_pos: QPoint | None = None
        self.theme_manager = theme_manager
        self._title_bar_buttons = []
        self.theme: str = self.theme_manager.current_theme()
        self.translations = translations

        self.theme_manager.theme_changed.connect(self._on_theme_changed)

        # Default colors for QR code and background
        self.qr_color = QColor(0, 0, 0)  # Black
        self.bg_color = QColor(255, 255, 255)  # White

        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle(self.translations["qr_code_window_title"])
        self.setWindowIcon(IconManager.get_icon("qr_code"))

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        self.title_bar = self.create_title_bar()
        self.main_layout.addLayout(self.title_bar)
        self._init_content()

        self._update_styles()
        self._center_window()

    def create_title_bar(self):
        title_bar = QHBoxLayout()
        self.title_label = QLabel(self.translations["qr_code_window_title"])
        title_bar.addWidget(self.title_label)
        title_bar.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding))

        if self.theme_manager.get_current_platform() == "windows":
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

            for icon, handler in [("roll_up_button", self.showMinimized), ("button_close", self.close)]:
                btn = self.theme_manager.create_title_button(IconManager.get_images(icon), handler)
                self._title_bar_buttons.append(btn)
                title_bar.addWidget(btn)

        return title_bar

    def _init_content(self) -> None:
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText(self.translations["url_input_placeholder"])
        self.main_layout.addWidget(self.url_input)

        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["PNG", "JPG", "PDF"])
        self.main_layout.addWidget(self.format_combo)

        self.qr_color_button = QPushButton(self.translations["qr_color_button"], self)
        self.qr_color_button.clicked.connect(self._choose_qr_color)
        self.main_layout.addWidget(self.qr_color_button)

        self.bg_color_button = QPushButton(self.translations["bg_color_button"], self)
        self.bg_color_button.clicked.connect(self._choose_bg_color)
        self.main_layout.addWidget(self.bg_color_button)

        self.save_button = QPushButton(self.translations["save_button"], self)
        self.save_button.clicked.connect(self._save_qr_code)
        self.main_layout.addWidget(self.save_button)

    def _choose_qr_color(self) -> None:
        color = QColorDialog.getColor(self.qr_color, self, self.translations["choose_qr_color"])
        if color.isValid():
            self.qr_color = color

    def _choose_bg_color(self) -> None:
        color = QColorDialog.getColor(self.bg_color, self, self.translations["choose_bg_color"])
        if color.isValid():
            self.bg_color = color

    def _update_styles(self) -> None:
        theme_vals = self.theme_manager.theme_palette[self.theme]
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {theme_vals['bg']};
                color: {theme_vals['fg']};
                font-family: 'Segoe UI';
                font-size: 12pt;
            }}
            QPushButton {{
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
                border: 1px solid {theme_vals['border']};
                border-radius: 10px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {theme_vals['hover']};
            }}
            QPushButton:pressed {{
                background-color: {theme_vals['pressed']};
            }}
            QPushButton:disabled {{
                background: {theme_vals['hover']};
                color: {theme_vals['fg']};
                border: 1px solid {theme_vals['border']};
                opacity: 0.5;
            }}
            QLineEdit {{
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
                border: 1px solid {theme_vals['border']};
                border-radius: 10px;
                padding: 10px;
            }}
            QLabel {{
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
                border: 1px solid {theme_vals['border']};
                border-radius: 10px;
                padding: 10px;
                text-align: left;
            }}
            QComboBox {{
                height: 25px;
                background: {theme_vals['hover']};
                border: 1px solid {theme_vals['border']};
                color: {theme_vals['fg']};
                padding: 10px;
                border-radius: 8px;
            }}
            QComboBox:hover {{ background: {theme_vals['bg']}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
                selection-background-color: #ff4891;
            }}
        """)

        self.title_label.setStyleSheet("border: none;")

    def _on_theme_changed(self, new_theme: str) -> None:
        self.theme = new_theme
        self._update_styles()
        self.update()

    def _center_window(self) -> None:
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        qr = self.frameGeometry()
        qr.moveCenter(screen.center())
        self.move(qr.topLeft())

    def _save_qr_code(self) -> None:
        data = self.url_input.text().strip()
        if not data:
            return

        file_format = self.format_combo.currentText().lower()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.translations["save_qr_code_dialog_title"],
            "",
            f"{file_format.upper()} Files (*.{file_format})",
        )
        if not file_path:
            return

        qr = segno.make_qr(data, error="H")
        scale = 30
        border = 2
        logo_path = "./vendor/images/logonew.png"

        if file_format == "png":
            self._save_qr_code_as_png(qr, file_path, scale, border, logo_path)
        elif file_format == "jpg":
            self._save_qr_code_as_jpg(qr, file_path, scale, border, logo_path)
        elif file_format == "pdf":
            self._save_qr_code_as_pdf(qr, file_path, scale, border, logo_path)

    def _overlay_logo(self, img_path: str, logo_path: str) -> Image:
        img = Image.open(img_path).convert("RGBA")
        logo_img = Image.open(logo_path).convert("RGBA")

        width, height = img.size
        logo_width, logo_height = 300, 300

        xmin = int((width / 2) - (logo_width / 2))
        ymin = int((height / 2) - (logo_height / 2))
        xmax = int((width / 2) + (logo_width / 2))
        ymax = int((height / 2) + (logo_height / 2))

        logo_img = logo_img.resize((xmax - xmin, ymax - ymin))
        img.paste(logo_img, (xmin, ymin, xmax, ymax), logo_img)

        return img

    def _save_qr_code_as_png(self, qr, file_path: str, scale: int, border: int, logo_path: str) -> None:
        qr.save(file_path, scale=scale, border=border, dark=self.qr_color.name(), light=self.bg_color.name())
        img = self._overlay_logo(file_path, logo_path)
        img.save(file_path)

    def _save_qr_code_as_jpg(self, qr, file_path: str, scale: int, border: int, logo_path: str) -> None:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_name = tmp.name
        qr.save(tmp_name, kind="png", scale=scale, border=border, dark=self.qr_color.name(), light=self.bg_color.name())
        img = self._overlay_logo(tmp_name, logo_path)
        img.convert("RGB").save(file_path, "JPEG", quality=95)
        os.remove(tmp_name)

    def _save_qr_code_as_pdf(self, qr, file_path: str, scale: int, border: int, logo_path: str) -> None:
        image = f"{file_path[:(len(file_path)-3)]}png"
        self._save_qr_code_as_png(qr, image, scale, border, logo_path)
        Image.open(image).convert("RGBA").save(f"{file_path}")
        os.remove(image)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        p.fillPath(path, QColor(self.theme_manager.theme_palette[self.theme]["bg"]))
        p.setClipPath(path)
        super().paintEvent(event)

    def _is_in_title_bar(self, pos):
        title_height = 40
        return pos.y() <= title_height

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_in_title_bar(event.position().toPoint()):
            self._old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._old_pos:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.move(self.pos() + delta)
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = None