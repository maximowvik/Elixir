import qrcode
import os
import json
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QLineEdit,
    QFileDialog,
    QComboBox,
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint
from PyQt6.QtGui import QScreen
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from .iconmanager import IconManager



class QRCodeWindow(QWidget):
    def __init__(self, language):
        super().__init__()
        self._old_pos = None
        self.language = language
        self.translations = self.load_translations(self.language)
        self.initUI()

    def load_translations(self, language):
        with open(f"./vendor/core/language/{language}.json", "r", encoding="utf-8") as file:
            return json.load(file)
        

    def initUI(self):
        self.setWindowTitle(self.translations["qr_code_window_title"])
        self.setWindowIcon(IconManager.get_icon("qr_code"))
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

        #Поле для ввода ссылки
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText(self.translations["url_input_placeholder"])
        self.url_input.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        main_layout.addWidget(self.url_input)

        #Выбор формата сохранения
        self.format_combo = QComboBox(self)
        self.format_combo.addItems(["PNG", "JPG", "PDF"])
        self.format_combo.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        main_layout.addWidget(self.format_combo)

        #Кнопка сохранить
        save_button = QPushButton(self.translations["save_button"], self)
        save_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        save_button.clicked.connect(self.save_qr_code)
        main_layout.addWidget(save_button)

        self.setLayout(main_layout)
        self.center_window(self)

    def save_qr_code(self):
        url = self.url_input.text()
        if not url:
            return

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill='black', back_color='white')

        file_format = self.format_combo.currentText().lower()
        file_path, _ = QFileDialog.getSaveFileName(self, self.translations["save_qr_code_dialog_title"], "", f"{file_format.upper()} Files (*.{file_format})")

        if file_path:
            temp_qr_path = "temp_qr.png"
            img.save(temp_qr_path)

        if file_format == "pdf":
            #PDF-документ
            c = canvas.Canvas(file_path, pagesize=letter)
            width, height = letter
            #Изображение QR-кода
            c.drawImage(temp_qr_path, (width - img.size[0]) / 2, (height - img.size[1]) / 2, width=img.size[0], height=img.size[1])
            c.save()

            #Удаление временного изображение
            os.remove(temp_qr_path)
        else:
            img.save(file_path)
            os.remove(temp_qr_path)  #Удаление временного изображения, если оно было создано

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
