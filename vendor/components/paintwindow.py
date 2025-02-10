import os
import json
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QFileDialog,
    QComboBox,
    QColorDialog,
    QInputDialog
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath, QPen, QBrush
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint
from PyQt6.QtGui import QScreen
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from .iconmanager import IconManager

class PaintWindow(QWidget):
    def __init__(self, language):
        super().__init__()
        self._old_pos = None
        self.language = language
        self.translations = self.load_translations(self.language)
        self.initUI()

    def load_translations(self, language):
        with open(f"{language}.json", "r", encoding="utf-8") as file:
            return json.load(file)

    def initUI(self):
        self.setWindowTitle(self.translations["paint_window_title"])
        self.setWindowIcon(IconManager.get_icon("paint"))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout()

        title_layout = QHBoxLayout()

        title_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        #Кнопка свернуть
        minimize_button = QPushButton()
        minimize_button.setStyleSheet("background-color: transparent; border: none;")
        pixmap_minimize = QPixmap("pic/minus.png")
        icon_minimize = QIcon(pixmap_minimize)
        minimize_button.setIcon(icon_minimize)
        minimize_button.setIconSize(QSize(30, 30))
        minimize_button.clicked.connect(self.showMinimized)
        title_layout.addWidget(minimize_button)

        #Кнопка закрытия
        close_button = QPushButton()
        close_button.setStyleSheet("background-color: transparent; border: none;")
        pixmap_close = QPixmap("pic/close.png")
        icon_close = QIcon(pixmap_close)
        close_button.setIcon(icon_close)
        close_button.setIconSize(QSize(30, 30))
        close_button.clicked.connect(self.close)
        title_layout.addWidget(close_button)

        main_layout.addLayout(title_layout)

        #Макет для инструментов рисования
        tools_layout = QHBoxLayout()

        #Кнопка выбора цвета
        self.color_button = QPushButton(self.translations["choose_color_button"], self)
        self.color_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.color_button.clicked.connect(self.choose_color)
        tools_layout.addWidget(self.color_button)

        #Кнопка выбора инструмента
        self.tool_combo = QComboBox(self)
        self.tool_combo.addItems(self.translations["tool_combo"])
        self.tool_combo.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.tool_combo.currentIndexChanged.connect(self.change_tool)
        tools_layout.addWidget(self.tool_combo)

        #Кнопка выбора размера холста
        self.size_button = QPushButton(self.translations["canvas_size_button"], self)
        self.size_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.size_button.clicked.connect(self.set_canvas_size)
        tools_layout.addWidget(self.size_button)

        #Кнопка сохранения изображения
        self.save_button = QPushButton(self.translations["save_button"], self)
        self.save_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.save_button.clicked.connect(self.save_image)
        tools_layout.addWidget(self.save_button)

        main_layout.addLayout(tools_layout)

        #Холст для рисования
        self.canvas = QLabel(self)
        self.canvas.setStyleSheet("background-color: white; border: 1px solid black;")
        self.canvas.setFixedSize(800, 600)
        self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.canvas)

        self.setLayout(main_layout)
        self.center_window(self)

        #Инициализация переменных для рисования
        self.drawing = False
        self.last_point = QPoint()
        self.pen = QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.SolidLine)
        self.brush = QBrush(Qt.GlobalColor.white, Qt.BrushStyle.SolidPattern)
        self.image = QPixmap(self.canvas.size())
        self.image.fill(Qt.GlobalColor.white)

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.pen.setColor(color)

    def change_tool(self, index):
        tool = self.tool_combo.itemText(index)
        if tool == self.translations["tool_combo"][0]:
            self.pen.setWidth(2)
        elif tool == self.translations["tool_combo"][1]:
            self.pen.setWidth(10)
        elif tool == self.translations["tool_combo"][2]:
            self.pen.setColor(Qt.GlobalColor.white)
            self.pen.setWidth(20)

    def set_canvas_size(self):
        width, ok1 = QInputDialog.getInt(self, self.translations["canvas_size_dialog_title"], self.translations["canvas_width_label"], 800, 1, 10000, 1)
        height, ok2 = QInputDialog.getInt(self, self.translations["canvas_size_dialog_title"], self.translations["canvas_height_label"], 600, 1, 10000, 1)
        if ok1 and ok2:
            self.canvas.setFixedSize(width, height)
            self.image = QPixmap(width, height)
            self.image.fill(Qt.GlobalColor.white)
            self.update()

    def save_image(self):
        file_path, _ = QFileDialog.getSaveFileName(self, self.translations["save_image_dialog_title"], "", self.translations["save_image_filter"])
        if file_path:
            if file_path.endswith(".pdf"):
                c = canvas.Canvas(file_path, pagesize=letter)
                self.image.save("temp_image.png")
                c.drawImage("temp_image.png", 0, 0, width=letter[0], height=letter[1])
                c.save()
                os.remove("temp_image.png")
            else:
                self.image.save(file_path)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.fillPath(path, QColor(self.palette().color(self.backgroundRole())))
        painter.setClipPath(path)
        super().paintEvent(event)

        # Рисуем изображение на холсте
        canvas_painter = QPainter(self.canvas)
        canvas_painter.drawPixmap(self.canvas.rect(), self.image)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = event.pos()
            self._old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self.drawing:
            painter = QPainter(self.image)
            painter.setPen(self.pen)
            painter.drawLine(self.last_point, event.pos())
            self.last_point = event.pos()
            self.update()
        elif self._old_pos is not None:
            delta = QPoint(event.globalPosition().toPoint() - self._old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            self._old_pos = None

    def center_window(self, window):
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        qr = window.frameGeometry()
        cp = screen.center()
        qr.moveCenter(cp)
        window.move(qr.topLeft())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.fillPath(path, QColor(self.palette().color(self.backgroundRole())))
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
