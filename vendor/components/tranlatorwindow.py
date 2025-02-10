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
    QComboBox,
    QTextEdit
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath, QTextOption
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint
from PyQt6.QtGui import QScreen
from googletrans import Translator, LANGUAGES
import asyncio
from .iconmanager import IconManager

class TranslatorWindow(QWidget):
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
        self.setWindowTitle(self.translations["translator_window_title"])
        self.setWindowIcon(IconManager.get_icon("translator"))
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

        #Поле для ввода текста
        self.input_text = QTextEdit(self)
        self.input_text.setPlaceholderText(self.translations["input_text_placeholder"])
        self.input_text.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        main_layout.addWidget(self.input_text)

        #Выбор языка для перевода
        self.target_language_combo = QComboBox(self)
        self.target_language_combo.addItems(LANGUAGES.values())
        self.target_language_combo.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        main_layout.addWidget(self.target_language_combo)

        #Кнопка перевода
        translate_button = QPushButton(self.translations["translate_button"], self)
        translate_button.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        translate_button.clicked.connect(self.translate_text)
        main_layout.addWidget(translate_button)

        #Поле для отображения переведенного текста
        self.output_text = QTextEdit(self)
        self.output_text.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.output_text.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        main_layout.addWidget(self.output_text)

        #Поле для отображения языка введенного текста
        self.detected_language_label = QLabel(self)
        self.detected_language_label.setStyleSheet("""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                        stop: 0 #6a00ee, stop: 0.5 #b000ff, stop: 1 #ff4891);
            border: none;
            color: white;
            font-family: 'Segoe UI';
            font-size: 12pt;
            padding: 10px;
            border-radius: 5px;
        """)
        self.detected_language_label.setWordWrap(True)
        main_layout.addWidget(self.detected_language_label)

        self.setLayout(main_layout)
        self.center_window(self)

    def translate_text(self):
        input_text = self.input_text.toPlainText()
        target_language = list(LANGUAGES.keys())[self.target_language_combo.currentIndex()]

        async def translate():
            translator = Translator()
            detected = await translator.detect(input_text)
            translation = await translator.translate(input_text, dest=target_language)
            return detected, translation

        detected, translation = asyncio.run(translate())

        self.detected_language_label.setText(f"{LANGUAGES[detected.lang]}")
        self.output_text.setText(f"{translation.text}")

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
