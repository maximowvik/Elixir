import os
import json
import threading
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QSpacerItem, QSizePolicy, QLineEdit, QScrollArea, QLabel, QComboBox
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPainterPath, QFont, QScreen, QCursor
from PyQt6.QtCore import Qt, QSize, QRectF, QPoint, pyqtSignal, QObject, QTimer, QThread, QMetaObject, Q_ARG, QPropertyAnimation, QEasingCurve
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtSvgWidgets import QSvgWidget
from .iconmanager import IconManager
from .command_manager import CommandManager
from .message_widget import MessageWidget
from .ai_model_manager import WorkModel
from .chat_history import ChatHistory
import traceback

class LoadingIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.setInterval(50)  # Интервал обновления анимации
        self.hide()

    def start_animation(self):
        self.angle = 0
        self.timer.start()
        self.show()

    def stop_animation(self):
        self.timer.stop()
        self.hide()

    def rotate(self):
        self.angle = (self.angle + 10) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Получаем цвет из темы
        theme = self.parent().theme_manager.theme_palette[self.parent().theme]
        color = QColor(theme["fg"])
        
        # Рисуем круговую анимацию
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self.angle)
        
        for i in range(8):
            painter.rotate(45)
            alpha = 255 - (i * 32)
            color.setAlpha(alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QPoint(8, 0), 2, 2)

# Основное окно чата
class AIChatWindow(QWidget):
    add_message_signal = pyqtSignal(str, str, str)

    def __init__(self, language, theme_manager, download_manager, current_directory, llama_cpp_lib):
        super().__init__()
        self.setObjectName("ChatWindow")
        self.language = language
        self.theme_manager = theme_manager
        self.theme = self.theme_manager.current_theme()
        self.translations = self.load_translations(self.language)

        self.current_directory = current_directory
        self.chat_model = ""
        self.model_path = self.load_last_model() or "gpt2.Q8_0"  # Загружаем последнюю модель
        self.llama_cpp_lib = llama_cpp_lib
        
        self.theme_manager.theme_changed.connect(self.on_theme_changed)
        self.add_message_signal.connect(self.add_message)

        self._old_pos = None
        self.message_send_user = ""
        self.messages = []
        self.is_generating = False

        # Инициализация истории чата
        self.chat_history = ChatHistory(current_directory)

        self.initUI()
        self.load_history()
        
        # Инициализация воркера в фоне
        self.worker = WorkModel(self.current_directory, self.model_path, self.llama_cpp_lib)
        self.worker.response_ready.connect(self.show_response)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        
        # Подготавливаем информацию о командах для модели
        commands_info = "Доступные команды:\n"
        for cmd, info in self.chat_history.get_commands().items():
            commands_info += f"{info['usage']} - {info['description']}\n"
        self.worker.set_commands_info(commands_info)
        
        self.worker_thread.started.connect(self.worker.load_model)
        self.worker_thread.start()

        self.command_manager = CommandManager()
        self.command_manager.register_command("/clear", self._command_clear_chat)
        self.command_manager.register_command("/help", self._command_show_help)
        self.command_manager.register_command("/download", self._command_download_data)
        self.command_manager.register_command("/send_message", self._command_create_message)
        
        self.download_manager = download_manager

    def load_history(self):
        """Загружает историю сообщений"""
        messages = self.chat_history.get_messages()
        for message in messages:
            if "command" in message:  # Это команда
                self.add_message(f"Команда: {message['command']}", "user")
            else:  # Это обычное сообщение
                self.add_message(message["text"], message["sender"], message["type"])

    def init_worker(self):
        self.worker = WorkModel(self.current_directory, self.model_path, self.llama_cpp_lib)
        result = self.worker.load_model()
        self.add_message(result[0], "bot", result[1])
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
        self.send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.send_button.clicked.connect(self.send_message)

        self.input_layout.addWidget(self.message_input)
        self.input_layout.addWidget(self.send_button)
        self.main_layout.addLayout(self.input_layout)

        self.update_styles()
        self.center_window()

    def _create_title_bar(self):
        self.title_layout = QHBoxLayout()

        # Добавляем иконку модели
        model_icon = QSvgWidget()
        model_icon.load(IconManager.get_images("model"))
        model_icon.setFixedSize(24, 24)
        model_icon.setStyleSheet("""
            QSvgWidget {
                padding-right: 8px;
            }
        """)
        self.title_layout.addWidget(model_icon)

        # Добавляем формат чата
        self.chat_format_label = QLabel("llama-2")
        self.chat_format_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 10pt;
                padding: 0 10px;
            }
        """)
        self.title_layout.addWidget(self.chat_format_label)

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
            self.model_path = first_model

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
        """Меняет модель и сохраняет выбор"""
        if not model_name:
            self.response_ready.emit("Не указано имя модели", "warning")
            return
        self.model_path = model_name
        self.save_last_model(model_name)  # Сохраняем выбор модели
        QMetaObject.invokeMethod(
            self.worker, "change_model",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, model_name)
        )

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

            # Устанавливаем сохраненную модель
            saved_model = self.load_last_model()
            if saved_model and saved_model in list_model:
                index = self.model_combo.findText(saved_model)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)
                    self.model_path = saved_model
            else:
                # Если сохраненная модель не найдена, устанавливаем первую из списка
                first_model = list_model[0]
                self.model_combo.setCurrentIndex(0)
                self.model_path = first_model
        else:
            self.model_combo.addItem("Not install models")

        self.model_combo.blockSignals(False)
        
    def show_response(self, response):
        self.add_message(response, "bot")
        # Добавляем ответ модели в контекст
        self.worker.add_to_context("assistant", response)
        
        # Разблокируем отправку
        self.is_generating = False
        self.send_button.setEnabled(True)
        self.message_input.setEnabled(True)

    def send_message(self):
        if self.is_generating:  # Если идет генерация ответа, игнорируем отправку
            return

        message = self.message_input.text().strip()
        if not message:
            return

        self.message_send_user = message
        self.add_message(message, "user")
        self.message_input.clear()
        
        # Добавляем сообщение в контекст модели
        self.worker.add_to_context("user", message)
        
        # Проверяем, является ли сообщение командой
        if message.startswith("/"):
            self.command_manager.execute(message)
            return

        # Блокируем отправку и показываем индикатор загрузки
        self.is_generating = True
        self.send_button.setEnabled(False)
        self.message_input.setEnabled(False)
        
        # Отправляем сообщение в модель
        self.worker.generate_response(message)

    def add_message(self, text, sender="user", type_message=""):
        # Переводим сообщение, если оно от бота или системы
        if sender in ["bot", "system"]:
            translated_text = self.translate_message(text)
        else:
            translated_text = text

        message = MessageWidget(type_message, translated_text, sender, self.theme_manager.theme_palette[self.theme])
        self.messages.append(message)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, message)
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())
        
        # Сохраняем оригинальное сообщение в историю
        if sender != "system":  # Не сохраняем системные сообщения
            self.chat_history.add_message(text, sender, type_message)

    def translate_message(self, text):
        """Переводит сообщение на язык интерфейса"""
        # Словарь с переводами системных сообщений
        translations = {
            "ru": {
                "Чат очищен.": "Чат очищен.",
                "Команды:": "Команды:",
                "Версия чата: alpha-0.0.1": "Версия чата: alpha-0.0.1",
                "Разработчики: Подсевалов Илья и Максимов Виктор": "Разработчики: Подсевалов Илья и Максимов Виктор",
                "Превышен размер контекста. Попробуйте очистить историю чата командой /clear": "Превышен размер контекста. Попробуйте очистить историю чата командой /clear",
                "Модель не была успешно загружена": "Модель не была успешно загружена",
                "Ваш запрос был экранирован:": "Ваш запрос был экранирован:",
                "Ошибка генерации ответа:": "Ошибка генерации ответа:",
                "Начата загрузка из": "Начата загрузка из",
                "в папку": "в папку",
                "Ошибка:": "Ошибка:",
                "Что-то пошло не так:": "Что-то пошло не так:",
                "Текст сообщения не указан": "Текст сообщения не указан",
                "URL не указан": "URL не указан"
            },
            "en": {
                "Чат очищен.": "Chat cleared.",
                "Команды:": "Commands:",
                "Версия чата: alpha-0.0.1": "Chat version: alpha-0.0.1",
                "Разработчики: Подсевалов Илья и Максимов Виктор": "Developers: Podsevalov Ilya and Maksimov Viktor",
                "Превышен размер контекста. Попробуйте очистить историю чата командой /clear": "Context size exceeded. Try clearing chat history with /clear command",
                "Модель не была успешно загружена": "Model was not loaded successfully",
                "Ваш запрос был экранирован:": "Your request was escaped:",
                "Ошибка генерации ответа:": "Error generating response:",
                "Начата загрузка из": "Started downloading from",
                "в папку": "to folder",
                "Ошибка:": "Error:",
                "Что-то пошло не так:": "Something went wrong:",
                "Текст сообщения не указан": "Message text not specified",
                "URL не указан": "URL not specified"
            }
        }

        # Если это системное сообщение, переводим его
        for key in translations[self.language]:
            if text.startswith(key):
                return text.replace(key, translations[self.language][key])
        
        # Если это ответ от модели, переводим его
        if self.language == "en":
            # Здесь можно добавить интеграцию с сервисом перевода
            # Пока просто возвращаем оригинальный текст
            return text
        
        return text

    def _command_clear_chat(self, args=None):
        self.messages.clear()
        self.chat_widget.deleteLater()
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_widget.setObjectName("ChatWindow")
        self.chat_layout.addStretch(1)
        self.scroll_area.setWidget(self.chat_widget)
        self.add_message("Чат очищен.", "bot")
        self.chat_history.clear_history()
        self.worker.clear_context()  # Очищаем контекст чата в модели

    def _command_show_help(self, args=None):
        commands = self.chat_history.get_commands()
        help_message = "Команды:\n"
        for cmd, info in commands.items():
            help_message += f"{info['usage']} - {info['description']}\n"
        help_message += "\n\nВерсия чата: alpha-0.0.1\nРазработчики: Подсевалов Илья и Максимов Виктор"
        self.add_message(help_message, "bot")
        self.chat_history.add_command("/help")

    def _command_create_message(self, args=None):
        try:
            message_text = args.get('text', '')
            message_sender = args.get('sender', 'user')
            message_type = args.get('type', '')

            if not message_text:
                raise ValueError("Текст сообщения не указан")

            self.add_message(message_text, message_sender, message_type)
            self.chat_history.add_command("/send_message", args)
        except Exception as e:
            self.add_message(f"Что-то пошло не так: {e}", "bot", "error")
        
    def _command_download_data(self, args=None):
        try:
            url = args.get('url', '')
            folder_name = args.get('type', 'downloads')

            if not url:
                raise ValueError("URL не указан")

            self.add_message(f"Начата загрузка из {url} в папку '{folder_name}'", "bot", "info")
            method = self.update_model_list if folder_name == "models" else None
            
            threading.Thread(target=self.download_manager.download_file, args=(url, folder_name, method), daemon=True).start()
            self.chat_history.add_command("/download", args)
            
        except Exception as e:
            self.add_message(f"Ошибка: {str(e)}", "bot", "error")

    def _get_send_icon(self, color: str, size: int = 20) -> QIcon:
        svg = f'''<svg fill="none" height="24" viewBox="0 0 24 24" width="24" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><linearGradient id="paint0_linear_2545_5409" gradientUnits="userSpaceOnUse" x1=".999" x2="22.999" y1="1" y2="23.001"><stop offset="0" stop-color="#4ea2ea"/><stop offset=".244792" stop-color="#484dff"/><stop offset=".484375" stop-color="#cd0ef3"/><stop offset=".723958" stop-color="#f640bb"/><stop offset=".950204" stop-color="#fb6d64"/></linearGradient><g clip-rule="evenodd" fill="url(#paint0_linear_2545_5409)" fill-rule="evenodd"><path d="m1.00009 3.21918c0-1.22562.99356-2.21918 2.21918-2.21918.33637 0 .66834.07647.97081.22362l17.34822 8.43968c.8943.435 1.4618 1.3423 1.4618 2.3367s-.5675 1.9017-1.4618 2.3367l-17.34822 8.4397c-.30247.1471-.63444.2236-.97081.2236-1.22562 0-2.21918-.9936-2.21918-2.2192 0-.1928-.013218-.3882.04422-.5749l2-6.5c.10298-.3347.37353-.5911.71325-.676l4.11943-1.0299-4.11943-1.0299c-.33972-.0849-.61027-.3413-.71325-.676l-2-6.50001c-.057439-.18669-.04422-.38213-.04422-.57491z" opacity=".2"/><path d="m1.00009 3.21918c0-1.22562.99356-2.21918 2.21918-2.21918.33637 0 .66834.07647.97081.22362l17.34822 8.43968c.8943.435 1.4618 1.3423 1.4618 2.3367s-.5675 1.9017-1.4618 2.3367l-17.34822 8.4397c-.30247.1471-.63444.2236-.97081.2236-1.22562 0-2.21918-.9936-2.21918-2.2192 0-.1928-.013218-.3882.04422-.5749l2-6.5c.10298-.3347.37353-.5911.71325-.676l4.11943-1.0299-4.11943-1.0299c-.33972-.0849-.61027-.3413-.71325-.676l-2-6.50001c-.057439-.18669-.04422-.38213-.04422-.57491zm2.21918-.21918c-.12105 0-.21918.09813-.21918.21918v.13045l1.78987 5.81706 7.45264 1.86321c.4452.1112.7575.5112.7575.9701s-.3123.8589-.7575.9701l-7.45264 1.8632-1.78987 5.8171v.1304c0 .1211.09813.2192.21918.2192.03323 0 .06601-.0076.09588-.0221l17.34825-8.4397c.206-.1002.3367-.3091.3367-.5382s-.1307-.438-.3367-.5382l-17.34825-8.43971c-.02987-.01454-.06266-.02209-.09588-.02209z"/></g></svg>'''
        image = QPixmap(size, size)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        renderer = QSvgRenderer(bytearray(svg, encoding='utf-8'))
        renderer.render(painter)
        painter.end()
        return QIcon(image)
    
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
            
    def closeEvent(self, event):
        """При закрытии окна сохраняем текущую модель"""
        self.save_last_model(self.model_path)
        super().closeEvent(event)

    def load_last_model(self):
        """Загружает последнюю использованную модель из файла настроек"""
        try:
            settings_path = os.path.join(self.current_directory, "vendor", "data", "chat_settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    return settings.get("last_model")
        except Exception:
            pass
        return None

    def save_last_model(self, model_name):
        """Сохраняет последнюю использованную модель в файл настроек"""
        try:
            settings_path = os.path.join(self.current_directory, "vendor", "data", "chat_settings.json")
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            
            settings = {}
            if os.path.exists(settings_path):
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            
            settings["last_model"] = model_name
            
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except Exception:
            pass