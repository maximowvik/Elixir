import sys
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QColorDialog, QSpinBox, QComboBox, QFileDialog,
    QSpacerItem, QSizePolicy, QInputDialog, QSlider
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QImage, QPainterPath, QIcon, QPixmap
)
from PyQt6.QtCore import Qt, QPoint, QSize, QRectF
from .iconmanager import IconManager

class PaintWidget(QWidget):
    def __init__(self, theme_manager):
        super().__init__()
        self.theme_manager = theme_manager

        self.image = QImage(800, 600, QImage.Format.Format_ARGB32)
        self.image.fill(Qt.GlobalColor.transparent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(800, 600)

        self._last_color = QColor("black")
        self.brush_size = 5
        self.brush_color = QColor(0, 0, 0)
        self.eraser_mode = False
        self.current_tool = "pencil"  # Добавлено для управления инструментами

        self.last_point = QPoint()
        self.drawing = False
        self.scale = 1.0
        self.offset = QPoint(0, 0)
        self.drag_start_pos = QPoint()
        self.dragging = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Закруглённый фон
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        painter.fillPath(path, QColor(Qt.GlobalColor.white))
        painter.setClipPath(path)

        # Масштабированное изображение
        scaled_image = self.image.scaled(
            int(self.image.width() * self.scale),
            int(self.image.height() * self.scale),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        painter.drawImage(self.offset, scaled_image)

        # Границы
        pen = QPen(QColor("#dee2e6"), 2)
        painter.setPen(pen)
        painter.drawRoundedRect(QRectF(self.offset.x(), self.offset.y(), scaled_image.width(), scaled_image.height()), 10, 10)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = self._map_to_image(event.position().toPoint())
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.dragging = True
            self.drag_start_pos = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self.drawing and (event.buttons() & Qt.MouseButton.LeftButton):
            current_point = self._map_to_image(event.position().toPoint())
            self._draw_line(self.last_point, current_point)
            self.last_point = current_point
        elif self.dragging and (event.buttons() & Qt.MouseButton.MiddleButton):
            delta = event.position().toPoint() - self.drag_start_pos
            self.offset += delta
            self.drag_start_pos = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.dragging = False

    def wheelEvent(self, event):
        self.scale *= 1.1 if event.angleDelta().y() > 0 else 0.9
        self.update()

    def _map_to_image(self, point: QPoint) -> QPoint:
        """Координаты из виджета -> в координаты изображения"""
        return ((point - self.offset) / self.scale).toPointF()

    def _draw_line(self, start_point: QPoint, end_point: QPoint):
        painter = QPainter(self.image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if self.current_tool == "eraser":
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            pen = QPen(Qt.GlobalColor.transparent, self.brush_size)
        else:
            pen = QPen(self.brush_color, self.brush_size)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        painter.setPen(pen)
        painter.drawLine(start_point, end_point)
        self.update()

    def clear(self):
        self.image.fill(Qt.GlobalColor.transparent)
        self.update()

    def resize_canvas(self, width, height):
        new_image = QImage(width, height, QImage.Format.Format_ARGB32)
        new_image.fill(Qt.GlobalColor.transparent)

        painter = QPainter(new_image)
        painter.drawImage(0, 0, self.image)

        self.image = new_image
        self.setFixedSize(width, height)
        self.update()

    def open_image(self, file_path):
        image = QImage(file_path)
        if not image.isNull():
            self.image = image.convertToFormat(QImage.Format.Format_ARGB32)
            self.scale = 1.0
            self.offset = QPoint(0, 0)
            self.update()

    def set_brush_size(self, size: int):
        self.brush_size = size

    def set_brush_color(self, color: QColor):
        self.brush_color = color
        self._last_color = color
        self.eraser_mode = False
        self.current_tool = "brush"

    def use_eraser(self):
        self.current_tool = "eraser"

    def use_brush(self):
        self.current_tool = "brush"
        
    @property
    def last_color(self):
        return self._last_color

    @last_color.setter
    def last_color(self, color):
        self._last_color = color


class PaintWindow(QMainWindow):
    def __init__(self, theme_manager, translations: dict[str, str]):
        super().__init__()
        self.theme_manager = theme_manager
        self.translations = translations
        self._old_pos = None

        self._init_window_properties()
        self._create_ui()

        # Подписка на сигнал изменения темы
        self.theme_manager.theme_changed.connect(self.apply_theme)
        self.apply_theme()

    def _init_window_properties(self):
        self.setMinimumSize(800,800)
        self.setWindowTitle(self.translations["paint_window_title"])
        self.setWindowIcon(IconManager.get_icon("paint"))
        if self.theme_manager.get_current_platform() == "windows":
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _create_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # Верхняя панель
        title_layout = QHBoxLayout()

        # Поле рисования
        self.paint_widget = PaintWidget(self.theme_manager)
        self.paint_widget.setObjectName("canvas")

        # Кнопки Сохранить / Очистить / Открыть (слева)
        save_button = QPushButton(self.translations["save_button"])
        save_button.clicked.connect(self.save_image)
        clear_button = QPushButton(self.translations["canvas_clear_label"])
        clear_button.clicked.connect(self.paint_widget.clear)
        open_button = QPushButton(self.translations.get("open_image_button", "Open Image"))
        open_button.clicked.connect(self.open_image)
        self.title_label = QLabel(self.translations["paint_window_title"])

        for btn in (save_button, clear_button, open_button):
            btn.setFixedSize(120, 40)
            title_layout.addWidget(btn)
        title_layout.addWidget(self.title_label)

        # Добавляем spacer, чтобы кнопки окна были справа
        title_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Кнопки управления окном (справа)
        if self.theme_manager.get_current_platform() == "windows":
            for icon, handler in [("roll_up_button", self.showMinimized), ("button_close", self.close)]:
                btn = self.theme_manager.create_title_button(IconManager.get_images(icon), handler)
                title_layout.addWidget(btn)

        self.main_layout.addLayout(title_layout)
        self.main_layout.addWidget(self.paint_widget)

        self._create_toolbar(self.main_layout)

    def _create_toolbar(self, layout):
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.width_slider = QSlider(Qt.Orientation.Horizontal)
        self.width_slider.setRange(1, 50)
        self.width_slider.setValue(5)
        self.width_slider.setFixedHeight(30)
        self.width_slider.valueChanged.connect(self.set_brush_width)

        toolbar.addWidget(QLabel(self.translations["cursor_thickness"]))
        toolbar.addWidget(self.width_slider)

        self.tool_combo = QComboBox()
        self.tool_combo.addItems(self.translations["tool_combo"])
        self.tool_combo.currentIndexChanged.connect(self._handle_tool_change)

        choose_color = QPushButton(self.translations["choose_color_button"])
        choose_color.clicked.connect(self.choose_color)

        toolbar.addWidget(choose_color)
        toolbar.addWidget(self.tool_combo)

        layout.addLayout(toolbar)

    def set_brush_width(self, value):
        self.paint_widget.set_brush_size(value)

    def save_image(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.translations["save_image_dialog_title"],
            "",
            self.translations["save_image_filter"]
        )
        if file_path:
            if not file_path.lower().endswith(".png"):
                file_path += ".png"
            self.paint_widget.image.save(file_path)

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translations.get("open_image_dialog_title", "Open Image"),
            "",
            self.translations.get("open_image_filter", "Images (*.png *.xpm *.jpg *.jpeg)")
        )
        if file_path:
            self.paint_widget.open_image(file_path)

    def choose_color(self):
        color = QColorDialog.getColor(self.paint_widget.last_color)
        if color.isValid():
            self.paint_widget.set_brush_color(color)

    def _handle_tool_change(self, index):
        self.tool_map = {0: "pencil", 1: "brush", 2: "eraser"}
        tool = self.tool_map.get(index, "pencil")
        self.paint_widget.current_tool = tool
        if tool == "eraser":
            self.paint_widget.use_eraser()
        else:
            self.paint_widget.use_brush()
            if tool == "pencil":
                self.paint_widget.set_brush_size(3)
                self.width_slider.setValue(3)
            elif tool == "brush":
                self.paint_widget.set_brush_size(5)
                self.width_slider.setValue(5)

    def apply_theme(self):
        palette = self.theme_manager.theme_palette[self.theme_manager.current_theme()]

        main_style = f"""
            QWidget {{
                background-color: {palette['bg']};
                color: {palette['fg']};
                border-radius: 8px;
                font-family: 'Segoe UI';
                font-size: 12pt;
            }}

            QWidget#canvas{{
                background-color: {palette['bg']};
                color: {palette['fg']};
                border: 1px solid {palette['border']};
            }}

            QPushButton {{
                height: 30px;
                background-color: {palette['bg']};
                color: {palette['fg']};
                border: 1px solid {palette['border']};
                border-radius: 8px;
                padding: 8px 15px;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background-color: {palette['hover']};
            }}
            QPushButton:pressed {{
                background-color: {palette['pressed']};
            }}
            QLabel {{
                font-size: 10pt;
                margin-bottom: 5px;
            }}
            QSlider {{
                min-height: 25px;
            }}
            QSlider::groove:horizontal {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {palette['bg_info']}, stop:1 {palette['border']}
                );
                height: 10px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {palette['fg']};
                width: 20px;
                height: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {palette['bg_info']}, stop:1 {palette['bg_info']}
                );
                border-radius: 3px;
            }}
            QComboBox {{height:25px; background: {palette['hover']}; border: 1px solid {palette['border']}; color: {palette['fg']}; padding: 10px; border-radius: 8px;}}
            QComboBox:hover {{ background: {palette['bg']}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{ background: {palette['bg']}; color: {palette['fg']}; selection-background-color: #ff4891; }}
        """

        self.setStyleSheet(main_style)

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