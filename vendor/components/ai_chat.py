from datetime import datetime
import os
import json
import threading
import uuid
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QSpacerItem, QSizePolicy, QLineEdit, QScrollArea, QLabel, QComboBox
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath, QFont, QScreen, QCursor
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint, pyqtSignal, QObject, QTimer, QThread
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtSvgWidgets import QSvgWidget
from .iconmanager import IconManager
from .command_manager import CommandManager
from .message_widget import MessageWidget
from .ai_model_manager import ModelWorker
from .chat_history import ChatHistory

class AIChatWindow(QWidget):
    add_message_signal = pyqtSignal(str, str, str)
    ui_block_signal = pyqtSignal(bool)

    def __init__(self, language, theme_manager, download_manager, current_directory):
        super().__init__()
        self.setObjectName("ChatWindow")
        self.language = language
        self.theme_manager = theme_manager
        self.current_directory = current_directory
        self.theme = self.theme_manager.current_theme()
        self.translations = self.load_translations()
        self.chat_model = ""
        self.api_key = ""

        self.theme_manager.theme_changed.connect(self.on_theme_changed)
        self.add_message_signal.connect(self.add_message)
        self.ui_block_signal.connect(self.block_ui)

        self._old_pos = None
        self.messages = []
        self.spacer = ""
        self.is_generating = False

        self.chat_history = ChatHistory(current_directory)
        self.init_ui()
        self.load_settings()
        self.load_history()

        self.command_manager = CommandManager()
        self.register_commands()
        self.download_manager = download_manager

    def load_translations(self):
        """Загружает переводы для текущего языка"""
        lang_file = os.path.join(self.current_directory, "vendor", "core", "language", f"{self.language}.json")
        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"ai_chat_window_title": "AI Chat", "input_placeholder": "Type a message...", "send_button": "Send"}

    def load_settings(self):
        """Загружает все настройки чата"""
        settings_path = os.path.join(self.current_directory, "vendor", "data", "chat_settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    self.api_key = settings.get("api_key", "")
                    self.chat_model = settings.get("last_model", "deepseek/deepseek-r1")
            except Exception as e:
                print(f"Error loading settings: {e}")
        
        # Инициализация модели
        self.init_model_worker()

    def save_settings(self):
        """Сохраняет все настройки чата"""
        settings_path = os.path.join(self.current_directory, "vendor", "data", "chat_settings.json")
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        settings = {
            "api_key": self.api_key,
            "last_model": self.chat_model
        }
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def init_model_worker(self):
        """Инициализирует модель и рабочий поток"""
        self.worker = ModelWorker(self.api_key, self.chat_model, self.language)
        self.worker.responseReady.connect(self.handle_response)
        self.worker.errorOccurred.connect(self.handle_error)
        self.worker.statusChanged.connect(self.handle_status)
        
        # Инициализация потока
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

    def register_commands(self):
        """Регистрирует все команды"""
        self.command_manager.register_command("/clear", self._command_clear_chat)
        self.command_manager.register_command("/help", self._command_show_help)
        self.command_manager.register_command("/download", self._command_download_data)
        self.command_manager.register_command("/send_message", self._command_create_message)
        self.command_manager.register_command("/set_api_key", self._command_set_api_key)

        # Формирование информации о командах
        commands_info = "Доступные команды:\n"
        for cmd, info in self.chat_history.get_commands().items():
            commands_info += f"{info['usage']} - {info['description']}\n"
        self.worker.set_commands_info(commands_info)

    def init_ui(self):
        """Инициализирует пользовательский интерфейс"""
        self.setWindowTitle(self.translations.get("ai_chat_window_title", "AI Chat"))
        self.setWindowIcon(IconManager.get_icon("chat"))
        self.setMinimumSize(800, 600)
        if self.theme_manager.get_current_platform() == "windows":
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Основной макет
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.addLayout(self.create_title_bar())
        self.main_layout.addWidget(self.create_message_area())
        self.main_layout.addLayout(self.create_input_area())

        self.update_styles()
        self.center_window()

    def create_title_bar(self):
        """Создает панель заголовка"""
        title_layout = QHBoxLayout()

        # Иконка модели
        model_icon = QSvgWidget()
        model_icon.load(IconManager.get_images("model"))
        model_icon.setFixedSize(24, 24)
        title_layout.addWidget(model_icon)

        # Формат чата
        self.chat_format_label = QLabel("llama-2")
        title_layout.addWidget(self.chat_format_label)

        # Выбор модели
        self.model_combo = QComboBox()
        self.update_model_list()
        self.model_combo.setFixedWidth(220)
        self.model_combo.currentTextChanged.connect(self.change_model)
        title_layout.addWidget(self.model_combo)
        
        # Растягивающий элемент
        title_layout.addItem(QSpacerItem(10, 10, QSizePolicy.Policy.Expanding))

        # Кнопки управления окном
        if self.theme_manager.get_current_platform() == "windows":
            for icon, handler in [("roll_up_button", self.showMinimized), ("button_close", self.close)]:
                btn = self.theme_manager.create_title_button(IconManager.get_images(icon), handler)
                title_layout.addWidget(btn)

        return title_layout

    def create_message_area(self):
        """Создает область сообщений"""
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        
        self.chat_widget = QWidget()
        self.chat_widget.setObjectName("ChatWindow")
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.addStretch(1)  # Растягивающий элемент в конце
        
        self.scroll_area.setWidget(self.chat_widget)
        return self.scroll_area

    def create_input_area(self):
        """Создает область ввода сообщения"""
        input_layout = QHBoxLayout()
        
        self.message_input = QLineEdit(self)
        self.message_input.setPlaceholderText(
            self.translations.get("input_placeholder", "Type a message...")
        )
        self.message_input.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton(parent=self)
        self.send_button.setIcon(QIcon(IconManager.get_images("send")))
        self.send_button.setIconSize(QSize(40, 40))
        self.send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.send_button.setText(self.translations.get("send_button", "Send"))
        self.send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_button)
        return input_layout

    def load_history(self):
        """Загружает историю сообщений"""
        messages = self.chat_history.get_messages()
        self._command_clear_chat()
        for item in messages:
            if "command" in item:
                self.add_message(f"Команда: {item['command']}", "user")
            else:
                self.add_message(item["text"], item["sender"], item["type"])

    def update_model_list(self):
        """Обновляет список доступных моделей"""
        self.model_combo.clear()
        model_path = os.path.join(self.current_directory, "vendor", "models")
        local_models = []

        if os.path.isdir(model_path):
            for name in os.listdir(model_path):
                if os.path.isfile(os.path.join(model_path, name)):
                    model_name = name.rsplit(".", 1)[0]
                    local_models.append(model_name)

        if local_models:
            self.model_combo.addItem("Using network models")
            self.model_combo.addItems(local_models)
        else:
            self.model_combo.addItem("Not install models, uses network model")

    def change_model(self, model_name):
        """Обработчик смены модели"""
        if model_name == "Using network models":
            self.chat_model = "deepseek/deepseek-r1"
        else:
            self.chat_model = model_name
        
        # Обновляем модель в воркере
        self.worker.model_name = self.chat_model
        self.save_settings()
        self.add_message(f"Модель изменена на: {model_name}", "system", "info")

    def send_message(self):
        """Отправляет сообщение пользователя"""
        if self.is_generating:
            return

        message = self.message_input.text().strip()
        if not message:
            return

        # Блокируем интерфейс сразу для всех случаев
        self.block_ui(True)
        
        self.add_message(message, "user")
        self.message_input.clear()

        # Обработка команд
        if message.startswith("/"):
            try:
                self.command_manager.execute(message)
            finally:
                # Разблокируем интерфейс после выполнения команды
                self.block_ui(False)
            return

        # Отправляем сообщение в модель (не блокируем, так как блокировка уже сделана)
        self.worker.set_prompt(message)
        QTimer.singleShot(0, self.worker.response)

    def handle_response(self, response):
        message, msg_type = response
        self.add_message(message, "bot", msg_type)
        self.ui_block_signal.emit(False)

    def handle_error(self, error_msg):
        self.add_message(error_msg, "bot", "error")
        self.ui_block_signal.emit(False)

    def handle_status(self, status_msg):
        print(f"Status: {status_msg}")

    def block_ui(self, block):
        """Блокирует/разблокирует интерфейс"""
        self.is_generating = block
        self.send_button.setEnabled(not block)
        self.message_input.setEnabled(not block)
        
        # Визуальная индикация блокировки
        if block:
            self.send_button.setText("...")
            self.send_button.setStyleSheet(
                self.send_button.styleSheet() + "color: gray;"
            )
        else:
            self.send_button.setText(self.translations.get("send_button", "Send"))
            self.update_styles()
            
    def add_message(self, text, sender="user", type_message="", not_history:bool = False):
        """Добавляет сообщение в чат и перезаписывает файл истории чата"""
        # Переводим сообщения от бота/системы
        if sender in ["bot", "system"]:
            translated_text = self.translate_message(text)
        else:
            translated_text = text

        message = MessageWidget(
            type_message,
            translated_text,
            sender,
            self.theme_manager.theme_palette[self.theme]
        )

        self.messages.append(message)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, message)
        self.scroll_to_bottom()

        # Сохраняем в историю
        if sender != "system":
            # Создаем новую запись сообщения
            message_data = {
                "id": str(uuid.uuid4()),
                "text": text,
                "sender": sender,
                "type": type_message if type_message != "" else "info",
                "timestamp": datetime.now().isoformat()
            }

            # Загружаем текущую историю
            history = self.chat_history._load_history()

            # Добавляем новое сообщение
            if(not not_history): history["messages"].append(message_data)

            # Перезаписываем файл истории
            self.chat_history._save_history(history)
            
            
    
    def scroll_to_bottom(self):
        """Прокручивает чат вниз"""
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def translate_message(self, text):
        return text

    # Команды
    def _command_clear_chat(self, args=None):
        """Очистка чата"""
        # Сохраняем системные сообщения
        system_messages = [msg for msg in self.messages if msg.sender == "system"]
        
        # Удаляем все виджеты сообщений
        for i in reversed(range(self.chat_layout.count())):
            widget = self.chat_layout.itemAt(i).widget()
            if widget and widget != self.spacer:
                widget.deleteLater()
        
        self.messages = []
        self.chat_layout.addStretch(1)
        
        # Восстанавливаем системные сообщения
        for msg in system_messages:
            self.chat_layout.insertWidget(0, msg)
            self.messages.append(msg)
        
        self.chat_history.clear_history()
        self.worker.clear_context()
        self.add_message("Чат очищен.", "bot", not_history=True)

    def _command_show_help(self, args=None):
        """Показывает справку по командам"""
        commands = self.chat_history.get_commands()
        help_message = "Команды:<br>"
        for cmd, info in commands.items():
            help_message += f"{info['usage']} - {info['description']}<br>"
        help_message += "Версия чата: alpha-0.0.1\nРазработчики: Подсевалов Илья и Максимов Виктор"
        help_message = help_message.replace("<code>", "").replace("</code>", "")
        print(help_message)
        self.add_message(help_message, "bot")

    def _command_create_message(self, args=None):
        """Создает сообщение по команде"""
        try:
            message_text = args.get('text', '')
            message_sender = args.get('sender', 'user')
            message_type = args.get('type', '')

            if not message_text:
                raise ValueError("Текст сообщения не указан")

            self.add_message(message_text, message_sender, message_type)
        except Exception as e:
            self.add_message(f"Что-то пошло не так: {e}", "bot", "error")
        
    def _command_download_data(self, args=None):
        """Загружает данные по команде"""
        try:
            url = args.get('url', '')
            folder_name = args.get('type', 'downloads')

            if not url:
                raise ValueError("URL не указан")

            self.add_message(f"Начата загрузка из {url} в папку '{folder_name}'", "bot", "info")
            threading.Thread(
                target=self.download_manager.download_file, 
                args=(url, folder_name, self.update_model_list if folder_name == "models" else None),
                daemon=True
            ).start()
        except Exception as e:
            self.add_message(f"Ошибка: {str(e)}", "bot", "error")

    def _command_set_api_key(self, args=None):
        """Устанавливает API ключ"""
        try:
            api_key = args.get('api', '')
            if not api_key:
                raise ValueError("API ключ не указан")

            self.api_key = api_key
            self.worker.api_key = api_key
            self.save_settings()
            self.add_message(f"Вы выбрали api-ключ: {self.api_key}", "bot", "warning")
            self.add_message("API ключ успешно сохранен", "bot", "info")
        except Exception as e:
            self.add_message(f"Ошибка: {str(e)}", "bot", "error")

    def update_styles(self):
        """Обновляет стили интерфейса"""
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
            QSvgWidget {{
                color: {fg};
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
            QPushButton:disabled {{
                background-color: {bg};
                color: {border};
                border-color: {border};
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