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
    def __init__(self, theme_manager, translations: dict[str, str]):
        super().__init__()
        self._old_pos = None
        self.theme_manager = theme_manager
        self.translations = translations
        
        # Подписка на сигнал изменения темы
        self.theme_manager.theme_changed.connect(self.update_theme)
        
        self.initUI()
        
        # Обновляем тему после создания всех элементов
        self.update_theme(self.theme_manager.current_theme())

    def initUI(self):
        self.setWindowTitle(self.translations["translator_window_title"])
        self.setWindowIcon(IconManager.get_icon("translator"))
        if self.theme_manager.get_current_platform() == "windows":
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout()

        title_layout = QHBoxLayout()
        
        self.title_label = QLabel(self.translations["translator_window_title"])
        title_layout.addWidget(self.title_label)
        title_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        if self.theme_manager.get_current_platform() == "windows":
            for icon, handler in [("roll_up_button", self.showMinimized), ("button_close", self.close)]:
                btn = self.theme_manager.create_title_button(IconManager.get_images(icon), handler)
                title_layout.addWidget(btn)

        main_layout.addLayout(title_layout)

        #Поле для ввода текста
        self.input_text = QTextEdit(self)
        self.input_text.setPlaceholderText(self.translations["input_text_placeholder"])
        main_layout.addWidget(self.input_text)

        #Выбор языка для перевода
        self.target_language_combo = QComboBox(self)
        self.target_language_combo.addItems(LANGUAGES.values())
        main_layout.addWidget(self.target_language_combo)

        #Кнопка перевода
        self.translate_button = QPushButton(self.translations["translate_button"], self)
        self.translate_button.clicked.connect(self.translate_text)
        main_layout.addWidget(self.translate_button)

        #Поле для отображения переведенного текста
        self.output_text = QTextEdit(self)
        self.output_text.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.output_text.setPlaceholderText("Start writing that the translation is displayed here...")
        main_layout.addWidget(self.output_text)

        #Поле для отображения языка введенного текста
        self.detected_language_label = QLabel(self)
        self.detected_language_label.setWordWrap(True)
        self.detected_language_label.setText("Launguage: not detect")
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

        self.detected_language_label.setText(f"Language: {LANGUAGES[detected.lang]}")
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
        if self._old_pos is not None:
            delta = QPoint(event.globalPosition().toPoint() - self._old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = None

    def update_theme(self, theme):
        theme_vals = self.theme_manager.theme_palette[theme]
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
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
                border: 1px solid {theme_vals['border']};
                opacity: 0.5;
            }}
            QTextEdit, QComboBox {{
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
                border: 1px solid {theme_vals['border']};
                border-radius: 10px;
                padding: 10px;
            }}
            QComboBox:hover {{
                background: {theme_vals['hover']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: url(pic/down-arrow.png);
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
                border: 1px solid {theme_vals['border']};
                border-radius: 10px;
                selection-background-color: {theme_vals['hover']};
                selection-color: {theme_vals['fg']};
            }}
            QLabel {{
                background: {theme_vals['bg']};
                color: {theme_vals['fg']};
                border: 1px solid {theme_vals['border']};
                border-radius: 10px;
                padding: 10px;
            }}
            QComboBox {{height:25px; background: {theme_vals['hover']}; border: 1px solid {theme_vals['border']}; color: {theme_vals['fg']}; padding: 10px; border-radius: 8px;}}
            QComboBox:hover {{ background: {theme_vals['bg']}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{ background: {theme_vals['bg']}; color: {theme_vals['fg']}; selection-background-color: #ff4891; }}
        """)
        
        # Обновляем стили отдельных элементов
        self.input_text.setStyleSheet(f"""
            background: {theme_vals['bg']};
            color: {theme_vals['fg']};
            border: 1px solid {theme_vals['border']};
            border-radius: 10px;
            padding: 10px;
            font-family: 'Segoe UI';
            font-size: 12pt;
        """)
        
        self.output_text.setStyleSheet(f"""
            background: {theme_vals['bg']};
            color: {theme_vals['fg']};
            border: 1px solid {theme_vals['border']};
            border-radius: 10px;
            padding: 10px;
            font-family: 'Segoe UI';
            font-size: 12pt;
        """)
        
        self.detected_language_label.setStyleSheet(f"""
            background: {theme_vals['bg']};
            color: {theme_vals['fg']};
            border: 1px solid {theme_vals['border']};
            border-radius: 10px;
            padding: 10px;
            font-family: 'Segoe UI';
            font-size: 12pt;
        """)
        
        self.title_label.setStyleSheet(f"""
            border: none;
        """)
