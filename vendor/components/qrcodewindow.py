from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import segno
from PIL import Image
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint
from PyQt6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPixmap,
    QScreen,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QColorDialog,
    QLabel
)
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Expecting IconManager and ThemeManager from host application
from .iconmanager import IconManager  # type: ignore

class QRCodeWindow(QWidget):
    """Frameless window for generating and saving QR codes."""

    TEMP_SUFFIX = ".png"

    def __init__(self, language: str, theme_manager) -> None:
        super().__init__()
        self._old_pos: QPoint | None = None
        self.language = language
        self.theme_manager = theme_manager
        self._title_bar_buttons = []
        self.theme: str = self.theme_manager.current_theme()
        self.translations: dict[str, str] = self._load_translations(language)

        self.theme_manager.theme_changed.connect(self._on_theme_changed)

        # Default colors for QR code and background
        self.qr_color = QColor(0, 0, 0)  # Black
        self.bg_color = QColor(255, 255, 255)  # White

        self._init_ui()

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------
    def _load_translations(self, language: str) -> dict[str, str]:
        file = Path("./vendor/core/language") / f"{language}.json"
        with file.open(encoding="utf-8") as f:
            return json.load(f)

    def _init_ui(self) -> None:
        self.setWindowTitle(self.translations["qr_code_window_title"])
        self.setWindowIcon(IconManager.get_icon("qr_code"))

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        self.main_layout.addLayout(self.create_title_bar())
        self._init_content()

        self._update_styles()
        self._center_window()
        
    def create_title_bar(self):
        if (self.theme_manager.get_current_platform() == "windows"):
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        title_bar = QHBoxLayout()
        self.title_label = QLabel(self.translations["qr_code_window_title"])
        title_bar.addWidget(self.title_label)
        title_bar.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding))
        if (self.theme_manager.get_current_platform() == "windows"):
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
        self.format_combo.addItems(["PNG", "JPG", "PDF", "SVG"])
        self.main_layout.addWidget(self.format_combo)

        # Buttons for color selection
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

    # ------------------------------------------------------------------
    # Style helpers
    # ------------------------------------------------------------------
    def _create_title_button(self, icon_path: str, slot) -> QPushButton:
        btn = QPushButton()
        btn.setIcon(QIcon(QPixmap(icon_path)))
        btn.setIconSize(QSize(35, 35))
        btn.setFixedSize(40, 40)
        btn.setStyleSheet(self._title_btn_stylesheet())
        btn.clicked.connect(slot)
        return btn

    def _title_btn_stylesheet(self) -> str:
        palette = self.theme_manager.theme_palette[self.theme]
        return (
            "QPushButton {background: transparent; border: none; border-radius: 10px;}"
            f"QPushButton:hover {{background: {palette['hover']};}}"
            f"QPushButton:pressed {{background: {palette['pressed']};}}"
        )

    def _update_styles(self) -> None:
        palette = self.theme_manager.theme_palette[self.theme]
        fg, bg, border = palette["fg"], palette["bg"], palette["border"]
        hover, pressed = palette["hover"], palette["pressed"]
        font = "Segoe UI"

        self.setStyleSheet(f"background-color: {bg};")
        self.url_input.setStyleSheet(
            (
                f"background-color: {bg}; color: {fg}; border: 1px solid {border};"
                f"border-radius: 6px; padding: 10px; font: 13pt '{font}';"
            )
        )
        self.format_combo.setStyleSheet(
            (
                "QComboBox {background-color: %s; color: %s; border: 1px solid %s;"
                "border-radius: 6px; padding: 10px; font: 13pt '%s';}"
                "QComboBox::drop-down {border: none;}" % (bg, fg, border, font)
            )
        )
        self.qr_color_button.setStyleSheet(
            (
                "QPushButton {background-color: %s; color: %s; border: 1px solid %s;"
                "border-radius: 6px; padding: 10px; font: 13pt '%s';}"
                "QPushButton:hover {background-color: %s;}"
                "QPushButton:pressed {background-color: %s;}" % (bg, fg, border, font, hover, pressed)
            )
        )
        self.bg_color_button.setStyleSheet(
            (
                "QPushButton {background-color: %s; color: %s; border: 1px solid %s;"
                "border-radius: 6px; padding: 10px; font: 13pt '%s';}"
                "QPushButton:hover {background-color: %s;}"
                "QPushButton:pressed {background-color: %s;}" % (bg, fg, border, font, hover, pressed)
            )
        )
        self.save_button.setStyleSheet(
            (
                "QPushButton {background-color: %s; color: %s; border: 1px solid %s;"
                "border-radius: 6px; padding: 10px; font: 13pt '%s';}"
                "QPushButton:hover {background-color: %s;}"
                "QPushButton:pressed {background-color: %s;}" % (bg, fg, border, font, hover, pressed)
            )
        )

        if hasattr(self, 'minimize_btn') and self.minimize_btn:
            self.minimize_btn.setStyleSheet(self._title_btn_stylesheet())
        if hasattr(self, 'close_btn') and self.close_btn:
            self.close_btn.setStyleSheet(self._title_btn_stylesheet())

    # ------------------------------------------------------------------
    # Theme & geometry helpers
    # ------------------------------------------------------------------
    def _on_theme_changed(self, new_theme: str) -> None:
        self.theme = new_theme
        self._update_styles()
        self.update()

    def _center_window(self) -> None:
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        qr = self.frameGeometry()
        qr.moveCenter(screen.center())
        self.move(qr.topLeft())

    # ------------------------------------------------------------------
    # QR‑code generation & saving
    # ------------------------------------------------------------------
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

        qr = segno.make(data, error="L")

        if file_format in ("png", "svg", "pdf"):
            qr.save(file_path, kind=file_format, scale=10, border=4, dark=self.qr_color.name(), light=self.bg_color.name())
            if file_format == "pdf":
                self._embed_png_into_pdf(file_path)
            return

        # JPG or other: via Pillow
        with tempfile.NamedTemporaryFile(suffix=self.TEMP_SUFFIX, delete=False) as tmp:
            tmp_name = tmp.name
        qr.save(tmp_name, kind="png", scale=10, border=4, dark=self.qr_color.name(), light=self.bg_color.name())
        Image.open(tmp_name).convert("RGB").save(file_path, "JPEG")
        os.remove(tmp_name)

    # PDF helper -------------------------------------------------------
    def _embed_png_into_pdf(self, pdf_path: str) -> None:
        png_temp = pdf_path + "_temp.png"
        segno.make(self.url_input.text().strip(), error="L").save(png_temp, kind="png", scale=10, dark=self.qr_color.name(), light=self.bg_color.name())
        width, height = letter
        c = canvas.Canvas(pdf_path, pagesize=letter)
        img = Image.open(png_temp)
        c.drawImage(png_temp, (width - img.width) / 2, (height - img.height) / 2)
        c.save()
        os.remove(png_temp)

    # ------------------------------------------------------------------
    # Painting & window dragging
    # ------------------------------------------------------------------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        p.fillPath(path, QColor(self.theme_manager.theme_palette[self.theme]["bg"]))
        p.setClipPath(path)
        super().paintEvent(event)
        
    def _is_in_title_bar(self, pos):
        # Получаем геометрию заголовка
        title_height = 40  # Высота заголовка
        return pos.y() <= title_height

    def mousePressEvent(self, event):
       if event.button() == Qt.MouseButton.LeftButton:
            # Проверяем, находится ли курсор в области заголовка
            if self._is_in_title_bar(event.position().toPoint()):
                self._old_pos = event.globalPosition().toPoint()
            else:
                self._old_pos = None

    def mouseMoveEvent(self, event):
       if self._old_pos:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.move(self.pos() + delta)
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
       if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = None

__all__ = ["QRCodeWindow"]
