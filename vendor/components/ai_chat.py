import os
import re
import requests
import json
import threading
import time
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QSpacerItem, QSizePolicy, QLineEdit, QScrollArea, QLabel, QComboBox
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath, QFont, QScreen
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint, QTimer, pyqtSignal
from .iconmanager import IconManager
from .ai_model_manager import AI_Bot
from .command_manager import CommandManager
from .message_widget import MessageWidget


# Основное окно чата
class AIChatWindow(QWidget):
    add_message_signal = pyqtSignal(str, str, str)

    def __init__(self, language, theme_manager, download_manager):
        super().__init__()
        self.setObjectName("ChatWindow")

        self.language = language
        self.theme_manager = theme_manager
        self.theme = self.theme_manager.current_theme()
        self.translations = self.load_translations(self.language)
        self.chat_model = ""
        self.message_send_user = ""
        
        self.theme_manager.theme_changed.connect(self.on_theme_changed)
        self.add_message_signal.connect(self.add_message)

        self._old_pos = None
        self.messages = []

        self.bot = AI_Bot()

        self.initUI()

        self.command_manager = CommandManager()
        self.command_manager.register_command("/clear", self.clear_chat)
        self.command_manager.register_command("/help", self.show_help)
        self.command_manager.register_command("/download", self.download_data)
        
        self.download_manager = download_manager

    # --- загружаем переводы
    def load_translations(self, lang):
        with open(f"vendor/core/language/{lang}.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def initUI(self):
        self.setWindowTitle(self.translations.get("ai_chat_window_title", "AI Chat"))
        self.setWindowIcon(IconManager.get_icon("chat"))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(800, 600)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # --- заголовок ---
        self.main_layout.addLayout(self._create_title_bar())

        # --- зона сообщений ---
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.chat_widget = QWidget()
        self.chat_widget.setObjectName("ChatWindow")
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.addStretch(1)
        self.scroll_area.setWidget(self.chat_widget)
        self.main_layout.addWidget(self.scroll_area)

        # --- поле ввода ---
        self.input_layout = QHBoxLayout()
        self.message_input = QLineEdit(self)
        self.message_input.setPlaceholderText(self.translations.get("input_placeholder", "Type a message..."))
        self.send_button = QPushButton(self.translations.get("send_button", "Send"), self)
        self.send_button.clicked.connect(self.send_message)

        self.input_layout.addWidget(self.message_input)
        self.input_layout.addWidget(self.send_button)
        self.main_layout.addLayout(self.input_layout)

        self.update_styles()
        self.center_window()

    def _create_title_bar(self):
        self.title_layout = QHBoxLayout()

        self.model_combo = QComboBox()
        path_model = "vendor/models"
        list_model = []
        
        if os.path.isdir(path_model):
            # Загружаем модели
            for name_model in os.listdir(path_model):
                full_path = os.path.join(path_model, name_model)
                if os.path.isfile(full_path):
                    model_name = name_model.rsplit(".", 1)[0]
                    list_model.append(model_name)
        
        if list_model != []:
            for model_name in list_model:
                self.model_combo.addItem(model_name)
        else:
            self.model_combo.addItem("Not install models")

        self.model_combo.setFixedWidth(220)

        # Если есть модели, устанавливаем первую сразу
        if list_model:
            first_model = list_model[0]
            self.bot.set_model(first_model)

        # Подключаем обработчик смены модели
        self.model_combo.currentTextChanged.connect(self.change_model)

        self.title_layout.addWidget(self.model_combo)
        self.title_layout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding))

        for icon, slot in [(IconManager.get_images("roll_up_button"), self.showMinimized),
                           (IconManager.get_images("button_close"), self.close)]:
            btn = self.create_title_button(icon, slot)
            self.title_layout.addWidget(btn)

        return self.title_layout

    def change_model(self, model_name):
        self.bot.set_model(model_name)
        
        
    def update_model_list(self):
        path_model = "vendor/models"
        list_model = []

        if os.path.isdir(path_model):
            for name_model in os.listdir(path_model):
                full_path = os.path.join(path_model, name_model)
                if os.path.isfile(full_path):
                    model_name = name_model.rsplit(".", 1)[0]
                    list_model.append(model_name)

        self.model_combo.blockSignals(True)  # Отключаем события на время очистки
        self.model_combo.clear()

        if list_model:
            for model_name in list_model:
                self.model_combo.addItem(model_name)

            # Установим первую модель
            first_model = list_model[0]
            self.bot.set_model(first_model)
        else:
            self.model_combo.addItem("Not install models")

        self.model_combo.blockSignals(False)
        
    
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

    def send_message(self):
        text = self.message_input.text().strip()
        if not text:
            return

        self.message_input.clear()

        if text.startswith("/"):
            try:
                self.add_message(f"Команда: {text}", "user")
                self.message_send_user = text
                self.command_manager.execute(text)
            except ValueError as e:
                self.add_message(str(e), "bot", "error")
        else:
            self.add_message(text, "user")
            threading.Thread(target=self.get_ai_response, args=(text,), daemon=True).start()

    def get_ai_response(self, user_message):
        self.add_message_signal.emit("Помощник печатает...", "bot", "")
        time.sleep(1.5)
        self.bot.set_language(self.language)
        self.bot.set_message(user_message)
        result = self.bot.ai_response()
        self.add_message_signal.emit(result[0], "bot", result[1])

    def add_message(self, text, sender="user", type_message = ""):
        message = MessageWidget(type_message, text, sender, self.theme_manager.theme_palette[self.theme])
        self.messages.append(message)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, message)
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def clear_chat(self):
        self.messages.clear()
        self.chat_widget.deleteLater()
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.addStretch(1)
        self.scroll_area.setWidget(self.chat_widget)
        self.add_message("Чат очищен.", "bot")

    def show_help(self):
        help_message = (
            "Команды:\n"
            "/clear - Очистить чат\n"
            "/help - Показать эту помощь\n\n"
            "Версия чата: alpha-0.0.1\nРазработчики: Подсевалов Илья и Максимов Виктор"
        )
        self.add_message(help_message, "bot")
        
    def download_data(self, args=None):
        try:
            url = args.get('url', '')
            folder_name = args.get('type', 'downloads')  # <-- папка по умолчанию "downloads"

            if not url:
                raise ValueError("URL не указан")

            self.add_message(f"Начата загрузка из {url} в папку '{folder_name}'", "bot", "info")
            method = self.update_model_list if folder_name == "models" else None
            
            threading.Thread(target=self.download_manager.download_file, args=(url, folder_name, method), daemon=True).start()
            
        except Exception as e:
            self.add_message(f"Ошибка: {str(e)}", "bot", "error")

    def update_styles(self):
        palette = self.theme_manager.theme_palette[self.theme]
        fg, bg, border, hover, pressed, error, warning = palette["fg"], palette["bg"], palette["border"], palette["hover"], palette["pressed"], palette["bg_error"], palette["bg_warning"]

        self.setStyleSheet(f"""
            QWidget {{ background-color: {bg}; color: {fg}; font-family: 'Segoe UI'; font-size: 12pt;}}
            QComboBox {{ background: {hover}; border: 1px solid {border}; color: {fg}; padding: 5px 10px; border-radius: 8px; }}
            QComboBox:hover {{ background: {bg}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{ background: {bg}; color: {fg}; selection-background-color: #ff4891; }}
            #ChatWindow {{
                border: 1px solid {border};
                border-radius: 10px;
            }}
            
            #ChatWindowMessageError{{
                background-color: {error};
                color:{fg}
            }}
            
            #ChatWindowMessageWarning{{
                background-color: {warning};
                color:{fg}
            }}
        """)
        self.message_input.setStyleSheet(f"""
            background-color: {bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 8px;
            font-size: 12pt;
        """)
        self.send_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 8px;
                font-size: 12pt;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton:pressed {{ background-color: {pressed}; }}
        """)

    def on_theme_changed(self, new_theme):
        self.theme = new_theme
        self.update_styles()
        self.update()

        # Обновляем тему у всех сообщений
        for message in self.messages:
            message.update_theme(self.theme_manager.theme_palette[self.theme])

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
        if self._old_pos:
            delta = QPoint(event.globalPosition().toPoint() - self._old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = None