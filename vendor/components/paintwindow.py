import sys
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QColorDialog, QSpinBox, QComboBox, QFileDialog,
    QSpacerItem, QSizePolicy, QInputDialog
)
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QImage, QPainterPath, QIcon
)
from PyQt6.QtCore import Qt, QPoint, QSize, QRectF

# Константы стилей
BUTTON_STYLE = """
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                              stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
    border: none;
    color: white;
    font-family: 'Segoe UI';
    font-size: 12pt;
    padding: 10px;
    border-radius: 5px;
"""


class PaintWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self._init_drawing_properties()

    def _init_ui(self):
        self.image = QImage(800, 600, QImage.Format.Format_RGB32)
        self.image.fill(Qt.GlobalColor.white)
        self.setFixedSize(800, 600)
        self.setStyleSheet("background-color: white; border: 1px solid #ccc;")

    def _init_drawing_properties(self):
        self.drawing = False
        self.last_point = QPoint()
        self.pen_color = QColor(Qt.GlobalColor.black)
        self.pen_width = 3
        self.current_tool = "pencil"

    def paintEvent(self, event):
        with QPainter(self) as painter:
            painter.drawImage(0, 0, self.image)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = event.position().toPoint()
            with QPainter(self.image) as painter:
                self._configure_painter(painter)
                painter.drawPoint(self.last_point)
            self.update()

    def mouseMoveEvent(self, event):
        if self.drawing and event.buttons() & Qt.MouseButton.LeftButton:
            current_point = event.position().toPoint()
            with QPainter(self.image) as painter:
                self._configure_painter(painter)
                painter.drawLine(self.last_point, current_point)
            self.last_point = current_point
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False

    def _configure_painter(self, painter):
        pen = QPen(self.pen_color, self.pen_width, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

    def clear(self):
        self.image.fill(Qt.GlobalColor.white)
        self.update()

    def resize_canvas(self, width, height):
        new_image = QImage(width, height, QImage.Format.Format_RGB32)
        new_image.fill(Qt.GlobalColor.white)
        
        with QPainter(new_image) as painter:
            painter.drawImage(0, 0, self.image)
        
        self.image = new_image
        self.setFixedSize(width, height)
        self.update()


class PaintWindow(QMainWindow):
    def __init__(self, language):
        super().__init__()
        self.language = language
        self.translations = self._load_translations()
        self._init_window_properties()
        self._create_ui()
        self._old_pos = None

    def _init_window_properties(self):
        self.setMinimumSize(800, 600)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle(self.translations["paint_window_title"])

    def _create_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self._create_title_bar(main_layout)
        self._create_paint_widget(main_layout)
        self._create_toolbar(main_layout)

    def _create_title_bar(self, parent_layout):
        title_layout = QHBoxLayout()
        title_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        for button in self._create_window_control_buttons():
            title_layout.addWidget(button)

        parent_layout.addLayout(title_layout)

    def _create_window_control_buttons(self):
        return [
            self._create_button("window-minimize", self.showMinimized),
            self._create_button("window-close", self.close)
        ]

    def _create_button(self, icon_name, handler):
        button = QPushButton()
        button.setStyleSheet("background-color: transparent; border: none;")
        button.setIcon(QIcon.fromTheme(icon_name))
        button.setIconSize(QSize(30, 30))
        button.clicked.connect(handler)
        return button

    def _create_paint_widget(self, parent_layout):
        self.paint_widget = PaintWidget()
        parent_layout.addWidget(self.paint_widget)

    def _create_toolbar(self, parent_layout):
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        controls = [
            self._create_color_button,
            self._create_tool_combo,
            self._create_width_control,
            self._create_size_button,
            self._create_clear_button,
            self._create_save_button
        ]

        for create_control in controls:
            widget = create_control()
            toolbar.addWidget(widget)

        parent_layout.addLayout(toolbar)

    def _create_color_button(self):
        button = QPushButton(self.translations["choose_color_button"])
        button.setStyleSheet(BUTTON_STYLE)
        button.clicked.connect(self.choose_color)
        return button

    def _create_tool_combo(self):
        combo = QComboBox()
        combo.addItems(self.translations["tool_combo"])
        combo.setStyleSheet(BUTTON_STYLE)
        combo.currentIndexChanged.connect(self._handle_tool_change)
        return combo

    def _create_width_control(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 50)
        self.width_spin.setValue(3)
        self.width_spin.setStyleSheet(BUTTON_STYLE)
        self.width_spin.valueChanged.connect(self.set_pen_width)
        
        layout.addWidget(QLabel(self.translations["cursor_thickness"]))
        layout.addWidget(self.width_spin)
        return container

    def _create_size_button(self):
        button = QPushButton(self.translations["canvas_size_button"])
        button.setStyleSheet(BUTTON_STYLE)
        button.clicked.connect(self.set_canvas_size)
        return button

    def _create_clear_button(self):
        button = QPushButton(self.translations["canvas_clear_label"])
        button.setStyleSheet(BUTTON_STYLE)
        button.clicked.connect(self.paint_widget.clear)
        return button

    def _create_save_button(self):
        button = QPushButton(self.translations["save_button"])
        button.setStyleSheet(BUTTON_STYLE)
        button.clicked.connect(self.save_image)
        return button

    def _load_translations(self):
        with open(f"./vendor/core/language/{self.language}.json", "r", encoding="utf-8") as file:
            return json.load(file)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.fillPath(path, QColor(240, 240, 240))
        painter.setClipPath(path)
        super().paintEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._old_pos is not None:
            delta = event.globalPosition().toPoint() - self._old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = None

    def choose_color(self):
        if (color := QColorDialog.getColor()).isValid():
            self.paint_widget.pen_color = color

    def _handle_tool_change(self, index):
        tools = ["pencil", "brush", "eraser"]
        self.paint_widget.current_tool = tools[index]
        if index == 2:  # Eraser
            self.paint_widget.pen_color = QColor(Qt.GlobalColor.white)

    def set_pen_width(self, width):
        self.paint_widget.pen_width = width

    def set_canvas_size(self):
        width, ok1 = QInputDialog.getInt(
            self, self.translations["canvas_size_dialog_title"],
            self.translations["canvas_width_label"], 800, 100, 4000, 1
        )
        height, ok2 = QInputDialog.getInt(
            self, self.translations["canvas_size_dialog_title"],
            self.translations["canvas_height_label"], 600, 100, 4000, 1
        )
        if ok1 and ok2:
            self.paint_widget.resize_canvas(width, height)

    def save_image(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.translations["save_image_dialog_title"],
            "",
            self.translations["save_image_filter"]
        )
        if file_path:
            if not file_path.lower().endswith('.png'):
                file_path += '.png'
            self.paint_widget.image.save(file_path)