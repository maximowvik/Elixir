import json
import os
import uuid
from datetime import datetime

class ChatHistory:
    def __init__(self, current_directory: str):
        self.current_directory = current_directory
        self.history_file = os.path.join(current_directory, "vendor", "data", "chat_history.json")
        self.commands = {
            "/clear": {
                "id": "cmd_clear",
                "description": "Очистить чат",
                "usage": "/clear"
            },
            "/help": {
                "id": "cmd_help",
                "description": "Показать список команд",
                "usage": "/help"
            },
            "/download": {
                "id": "cmd_download",
                "description": "Загрузить файл",
                "usage": "/download --url=\"<download link>\" --type=\"<download folder>\""
            },
            "/send_message": {
                "id": "cmd_send",
                "description": "Отправить сообщение",
                "usage": "/send_message --text=\"<message text>\" --sender=\"<sender name>\" --type=\"<message type>\""
            }
        }
        self._ensure_history_file()

    def _ensure_history_file(self):
        """Создает файл истории, если он не существует"""
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        if not os.path.exists(self.history_file):
            initial_data = {
                "messages": [],
                "commands": self.commands,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
            self._save_history(initial_data)

    def _load_history(self):
        """Загружает историю из файла"""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"messages": [], "commands": self.commands}

    def _save_history(self, data):
        """Сохраняет историю в файл"""
        data["last_updated"] = datetime.now().isoformat()
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_message(self, text: str, sender: str, type_message: str = ""):
        """Добавляет новое сообщение в историю"""
        history = self._load_history()
        message = {
            "id": str(uuid.uuid4()),
            "text": text,
            "sender": sender,
            "type": type_message if type_message != "" else "info",
            "timestamp": datetime.now().isoformat()
        }
        history["messages"].append(message)
        self._save_history(history)
        return message["id"]

    def add_command(self, command: str, args: dict = None):
        """Добавляет выполнение команды в историю"""
        if command not in self.commands:
            return None
        
        history = self._load_history()
        command_entry = {
            "id": self.commands[command]["id"],
            "command": command,
            "args": args or {},
            "timestamp": datetime.now().isoformat()
        }
        history["messages"].append(command_entry)
        self._save_history(history)
        return command_entry["id"]

    def clear_history(self):
        """Очищает историю сообщений"""
        history = self._load_history()
        history["messages"] = []
        self._save_history(history)

    def get_messages(self):
        """Возвращает все сообщения из истории"""
        return self._load_history()["messages"]

    def get_commands(self):
        """Возвращает список доступных команд"""
        return self.commands 