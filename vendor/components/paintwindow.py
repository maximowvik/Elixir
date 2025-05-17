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
        bg_color = QColor(self.theme_manager.theme_palette[self.theme_manager.current_theme()]['bg'])
        self.image = QImage(800, 600, QImage.Format.Format_RGB32)
        self.image.fill(bg_color)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(400, 300)
        self.setStyleSheet(f"background-color: {bg_color.name()}; border: 1px solid #ccc;")

        self.drawing = False
        self.last_point = QPoint()
        self.pen_color = QColor(Qt.GlobalColor.black)
        self.pen_width = 3
        self.current_tool = "pencil"
        self._last_color = QColor(Qt.GlobalColor.black)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.image)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = event.position().toPoint()
            self._draw_to_image(self.last_point, self.last_point)

    def mouseMoveEvent(self, event):
        if self.drawing and event.buttons() & Qt.MouseButton.LeftButton:
            current_point = event.position().toPoint()
            self._draw_to_image(self.last_point, current_point)
            self.last_point = current_point

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False

    def _draw_to_image(self, start, end):
        painter = QPainter(self.image)
        if self.current_tool == "eraser":
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
        else:
            pen = QPen(self.pen_color, self.pen_width, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
        painter.drawLine(start, end)
        self.update()

    def clear(self):
        bg_color = QColor(self.theme_manager.theme_palette[self.theme_manager.current_theme()]['bg'])
        self.image.fill(bg_color)
        self.update()

    def resize_canvas(self, width, height):
        new_image = QImage(width, height, QImage.Format.Format_RGB32)
        bg_color = QColor(self.theme_manager.theme_palette[self.theme_manager.current_theme()]['bg'])
        new_image.fill(bg_color)

        painter = QPainter(new_image)
        painter.drawImage(0, 0, self.image)

        self.image = new_image
        self.setFixedSize(width, height)
        self.update()

class PaintWindow(QMainWindow):
    def __init__(self, language, theme_manager):
        super().__init__()
        self.language = language
        self.theme_manager = theme_manager
        self.translations = self._load_translations()
        self._old_pos = None

        self._init_window_properties()
        self._create_ui()

    def _load_translations(self):
        with open(f"./vendor/core/language/{self.language}.json", "r", encoding="utf-8") as file:
            return json.load(file)

    def _init_window_properties(self):
        self.setMinimumSize(800, 600)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle(self.translations["paint_window_title"])
        self.setWindowIcon(IconManager.get_icon("paint"))

    def create_title_button(self, icon_name, slot):
        btn = QPushButton()
        btn.setIcon(QIcon(QPixmap(f"{icon_name}")))
        btn.setIconSize(QSize(20, 20))
        btn.setFixedSize(30, 30)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 6px;
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

    def _create_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # Верхняя панель
        title = QHBoxLayout()

        # Поле рисования (создаётся до кнопок)
        self.paint_widget = PaintWidget(self.theme_manager)

        # Кнопки Сохранить / Очистить
        save_button = QPushButton(self.translations["save_button"])
        save_button.clicked.connect(self.save_image)
        clear_button = QPushButton(self.translations["canvas_clear_label"])
        clear_button.clicked.connect(self.paint_widget.clear)

        for btn in (save_button, clear_button):
            btn.setFixedSize(100, 30)
            btn.setStyleSheet(f"""
                background: {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['bg']};
                color: {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['fg']};
                border: 1px solid {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['border']};
                border-radius: 10px;
                padding: 6px 12px;
                font-family: 'Segoe UI';
                font-size: 12pt;
            """)
            title.addWidget(btn)

        title.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Кнопки управления окном
        for icon, slot in [(IconManager.get_images("roll_up_button"), self.showMinimized),
                           (IconManager.get_images("button_close"), self.close)]:
            btn = self.create_title_button(icon, slot)
            title.addWidget(btn)

        self.main_layout.addLayout(title)
        self.main_layout.addWidget(self.paint_widget)
        self._create_toolbar(self.main_layout)
        
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

    def _create_toolbar(self, layout):
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.width_slider = QSlider(Qt.Orientation.Horizontal)
        self.width_slider.setRange(1, 50)
        self.width_slider.setValue(3)
        self.width_slider.setFixedHeight(30)
        self.width_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 14px;
                background: {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['bg']};
                border: 1px solid {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['border']};
                border-radius: 7px;
            }}
            QSlider::handle:horizontal {{
                background: {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['fg']};
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }}
        """)
        self.width_slider.valueChanged.connect(self.set_pen_width)

        toolbar.addWidget(QLabel(self.translations["cursor_thickness"]))
        toolbar.addWidget(self.width_slider)

        self.tool_combo = QComboBox()
        self.tool_combo.addItems(self.translations["tool_combo"])
        self.tool_combo.currentIndexChanged.connect(self._handle_tool_change)

        choose_color = QPushButton(self.translations["choose_color_button"])
        choose_color.clicked.connect(self.choose_color)

        button_style = f"""
            QPushButton {{
                background: {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['bg']};
                color: {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['fg']};
                border: 1px solid {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['border']};
                border-radius: 10px;
                padding: 8px;
                font-family: 'Segoe UI';
                font-size: 12pt;
            }}
            QPushButton:hover {{ background: {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['hover']}; }}
            QPushButton:pressed {{ background: {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['pressed']}; }}
        """

        combo_style = f"""
            QComboBox {{
                background: {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['bg']};
                color: {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['fg']};
                border: 1px solid {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['border']};
                border-radius: 10px;
                padding: 6px;
                font-family: 'Segoe UI';
                font-size: 12pt;
            }}
            QComboBox QAbstractItemView {{
                background: {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['bg']};
                color: {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['fg']};
                selection-background-color: {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['hover']};
                selection-color: {self.theme_manager.theme_palette[self.theme_manager.current_theme()]['fg']};
            }}
        """

        choose_color.setStyleSheet(button_style)
        self.tool_combo.setStyleSheet(combo_style)

        toolbar.addWidget(choose_color)
        toolbar.addWidget(self.tool_combo)

        layout.addLayout(toolbar)

    def set_pen_width(self, value):
        self.paint_widget.pen_width = value

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

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.paint_widget.pen_color = color

    def _handle_tool_change(self, index):
        tool_map = {
            "Карандаш": "pencil",
            "Кисть": "brush",
            "Ластик": "eraser"
        }
        self.paint_widget.current_tool = tool_map[self.tool_combo.currentText()]
        if self.paint_widget.current_tool != "eraser":
            self.paint_widget.pen_color = self.paint_widget._last_color

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        painter.fillPath(path, QColor(240, 240, 240))
        painter.setClipPath(path)
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
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = None
