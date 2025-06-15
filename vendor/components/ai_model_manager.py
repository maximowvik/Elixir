import os
import traceback
from PyQt6.QtCore import QObject, pyqtSignal
import requests
import json

class ModelWorker(QObject):
    responseReady = pyqtSignal(list)  # [message, message_type]
    errorOccurred = pyqtSignal(str)   # error_message
    statusChanged = pyqtSignal(str)   # status_message

    def __init__(self, api_key: str = None, work_model: str = None, language: str = "en") -> None:
        super().__init__()
        self.api_key = api_key
        self.work_model = work_model or "deepseek/deepseek-r1"
        self.language = language
        
        # Инициализация контекста диалога
        self.reset_context()
        
        # Настройки запросов
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://openrouter.ai/api/v1/",
            "X-Title": "Elixir Launcher | Chat bot"
        }
        
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.current_prompt = ""
        self.commands_info = "No commands available"
        
    def reset_context(self):
        """Сброс контекста диалога"""
        self.dialogs = [{
            "role": "system", 
            "content": "You are a helpful AI assistant. Respond in the user's preferred language. Use Markdown to make your request and don't forget about emojis."
        }]
        self.statusChanged.emit("Context reset")

    def update_api_key(self, new_api_key: str):
        """Обновление API ключа"""
        self.api_key = new_api_key
        self.headers["Authorization"] = f"Bearer {self.api_key}"
        self.statusChanged.emit("API key updated")

    def update_model(self, new_model: str):
        """Обновление используемой модели"""
        self.work_model = new_model
        self.statusChanged.emit(f"Model changed to {new_model}")

    def set_commands_info(self, commands_info: str):
        """Установка информации о командах"""
        self.commands_info = commands_info
        self.add_to_context("system", f"Available commands:\n{commands_info}")

    def set_prompt(self, message: str):
        """Установка текущего промпта"""
        if message and message.strip():
            self.current_prompt = message.strip()
            self.statusChanged.emit("Prompt set")
        else:
            self.errorOccurred.emit("Empty prompt provided")

    def add_to_context(self, role: str, content: str):
        """Добавление сообщения в контекст"""
        try:
            if role not in ["system", "user", "assistant"]:
                raise ValueError("Invalid role specified")
                
            self.dialogs.append({
                "role": role,
                "content": content
            })
            
            # Ограничение размера контекста (последние 10 сообщений)
            if len(self.dialogs) > 10:
                self.dialogs.pop(1)  # Удаляем самое старое сообщение (но сохраняем системное)
                
        except Exception as e:
            self.errorOccurred.emit(f"Error adding to context: {str(e)}")

    def clear_context(self):
        """Очистка контекста диалога"""
        self.reset_context()
        self.statusChanged.emit("Dialog context cleared")

    def response(self):
        """Отправка запроса к API и обработка ответа"""
        try:
            if not self.current_prompt:
                self.errorOccurred.emit("No prompt set for the request")
                return

            if not self.api_key:
                self.errorOccurred.emit("API key is not set")
                return

            # Добавляем промпт пользователя в контекст
            self.add_to_context("user", self.current_prompt)
            
            # Формируем запрос
            payload = {
                "model": self.work_model,
                "messages": self.dialogs,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            self.statusChanged.emit("Sending request to API...")
            
            # Отправляем запрос
            response = requests.post(
                self.url,
                headers=self.headers,
                json=payload,
                timeout=30  # Таймаут 30 секунд
            )
            
            # Обрабатываем ответ
            if response.status_code == 200:
                response_json = response.json()
                reply = response_json["choices"][0]["message"]["content"]
                
                # Добавляем ответ ассистента в контекст
                self.add_to_context("assistant", reply)
                
                # Отправляем ответ
                self.responseReady.emit([reply, "success"])
                self.statusChanged.emit("Response received successfully")
            else:
                error_msg = f"API Error: {response.status_code} - {response.text}"
                self.errorOccurred.emit(error_msg)
                
        except requests.exceptions.Timeout:
            self.errorOccurred.emit("Request timeout: Server did not respond in time")
        except requests.exceptions.RequestException as e:
            self.errorOccurred.emit(f"Request failed: {str(e)}")
        except json.JSONDecodeError:
            self.errorOccurred.emit("Invalid JSON response from server")
        except Exception as e:
            self.errorOccurred.emit(f"Unexpected error: {str(e)}")
            traceback.print_exc()
        finally:
            self.current_prompt = ""  # Сбрасываем текущий промпт после обработки