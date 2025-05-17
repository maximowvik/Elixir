import os
import json
import threading
import time
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QSpacerItem, QSizePolicy, QLineEdit, QScrollArea, QLabel, QComboBox
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath, QFont, QScreen
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint, QTimer, pyqtSignal, QThread
from PyQt6.QtSvg import QSvgRenderer
from .iconmanager import IconManager
from .ai_model_manager import ModelManager
from .command_manager import CommandManager
from .message_widget import MessageWidget

class ModelWorker(QThread):
    responseReady = pyqtSignal(str, str)
    error = pyqtSignal(str)

    def __init__(self, model_manager, prompt):
        super().__init__()
        self.model_manager = model_manager
        self.prompt = prompt

    def run(self):
        try:
            response = self.model_manager.generate_response(self.prompt)
            self.responseReady.emit(response, "response")
        except Exception as e:
            self.error.emit(str(e))

# Основное окно чата
class AIChatWindow(QWidget):
    add_message_signal = pyqtSignal(str, str, str)

    def __init__(self, language, theme_manager, download_manager, current_directory):
        super().__init__()
        self.setObjectName("ChatWindow")
        self.worker_thread = None
        self.language = language
        self.theme_manager = theme_manager
        self.theme = self.theme_manager.current_theme()
        self.translations = self.load_translations(self.language)
        self.chat_model = ""
        self.message_send_user = ""
        self.current_directory = current_directory
        self.model_manager = None
        
        self.theme_manager.theme_changed.connect(self.on_theme_changed)
        self.add_message_signal.connect(self.add_message)

        self._old_pos = None
        self.messages = []

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
        self.message_input.returnPressed.connect(self.send_message)
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
        self.add_message(f"Смена модели на {model_name}...", "bot", "info")
        model_path = os.path.join(self.current_directory, "vendor", "models", f"{model_name}.gguf")
        
        # Создаем новый экземпляр ModelManager
        self.model_manager = ModelManager(model_path)
        success, message = self.model_manager.load_model()
        
        if success:
            self.add_message(f"Модель {model_name} успешно загружена", "bot", "info")
        else:
            self.add_message(f"Ошибка загрузки модели: {message}", "bot", "error")

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
            self.get_ai_response(text)

    def get_ai_response(self, user_message):
        if not self.model_manager:
            self.add_message("Модель не загружена. Пожалуйста, выберите модель из списка.", "bot", "error")
            return

        # Создаем и запускаем worker в отдельном потоке
        self.worker = ModelWorker(self.model_manager, user_message)
        self.worker.responseReady.connect(self.on_response)
        self.worker.error.connect(lambda msg: self.add_message(msg, "bot", "error"))
        self.worker.start()

    def on_response(self, response, response_type):
        self.add_message_signal.emit(response, "bot", response_type)

    def add_message(self, text, sender="user", type_message = ""):
        message = MessageWidget(type_message, text, sender, self.theme_manager.theme_palette[self.theme])
        self.messages.append(message)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, message)
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def clear_chat(self,  args=None):
        self.messages.clear()
        self.chat_widget.deleteLater()
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_widget.setObjectName("ChatWindow")
        self.chat_layout.addStretch(1)
        self.scroll_area.setWidget(self.chat_widget)
        self.add_message("Чат очищен.", "bot")

    def show_help(self,  args=None):
        help_message = (
            "Команды:\n"
            "/clear - Очистить чат\n"
            "/help - Показать эту помощь\n\n"
            "/download --url=\"<download link>\" --type=\"<download folder or default to the root of the application>\" - позваляет загружать любые файлы (модели ии)"
            "\n\nВерсия чата: alpha-0.0.1\nРазработчики: Подсевалов Илья и Максимов Виктор"
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

    def _get_send_icon(self, color: str, size: int = 20) -> QIcon:
        svg = f'''<svg width="{size}" height="{size}" viewBox="0 0 390.041 390.041" xmlns="http://www.w3.org/2000/svg">
            <path d="m81.578.07c-38.9-1.865-75.532 33.964-67.083 76.208l19.458 97.5c.5-.018 1-.018 1.5 0h109.917c11.736-1.054 22.104 7.606 23.158 19.342s-7.606 22.104-19.342 23.158c-1.269.114-2.546.114-3.816 0h-109.917c-.501-.025-1.002-.068-1.5-.128l-19.458 97.625c-10.398 51.993 47.524 94.25 93.875 68.5l236.208-131.333c42.926-23.846 42.926-87.987 0-111.833l-236.209-131.331c-8.69-4.828-17.814-7.278-26.791-7.708z" fill="{color}"/>
        </svg>'''
        image = QPixmap(size, size)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        renderer = QSvgRenderer(bytearray(svg, encoding='utf-8'))
        renderer.render(painter)
        painter.end()
        return QIcon(image)

    def update_styles(self):
        palette = self.theme_manager.theme_palette[self.theme]
        bg = palette["bg"]
        fg = palette["fg"]
        border = palette["border"]
        hover = palette["hover"]
        pressed = palette["pressed"]

        self.setStyleSheet(f"""
            QWidget#ChatWindow {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QComboBox {{ 
                background: {hover}; 
                border: 1px solid {border}; 
                color: {fg}; 
                padding: 5px 10px; 
                border-radius: 8px; 
                min-width: 120px; 
            }}
            QComboBox:hover {{ 
                background: {bg}; 
            }}
            QComboBox::drop-down {{ 
                border: none; 
                width: 20px; 
            }}
            QComboBox QAbstractItemView {{ 
                background: {bg}; 
                color: {fg}; 
                selection-background-color: #ff4891; 
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

        self.send_button.setIcon(self._get_send_icon(fg))
        self.send_button.setIconSize(QSize(20, 20))
        self.send_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12pt;
                font-family: 'Segoe UI';
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {pressed};
            }}
        """)

        self.send_button.setFixedHeight(40)
        self.send_button.setMinimumWidth(120)

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
            delta = QPoint(event.globalPosition().toPoint() - self._old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = None