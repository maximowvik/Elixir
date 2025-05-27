from llama_cpp import Llama
import time, os
import traceback
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

class WorkModel(QObject):
    response_ready = pyqtSignal(str, str)  # text, type

    def __init__(self, current_directory:str, model_name: str, llamma: Llama = None, n_ctx: int = 512, n_threads: int = 8, n_gpu_layers: int = 0) -> list:
        super().__init__()
        self.current_directory = current_directory
        self.model_name = model_name
        self.full_path_model = f"{self.current_directory}\\vendor\\models\\{self.model_name}.gguf"
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers
        self.llama = llamma
        self.llm = None
        self.chat_context = []
        self.commands_info = ""
        self.max_context_messages = 5  # Ограничиваем количество сообщений в контексте

    def set_commands_info(self, commands_info: str):
        """Устанавливает информацию о доступных командах"""
        self.commands_info = commands_info

    def add_to_context(self, role: str, content: str):
        """Добавляет сообщение в контекст чата"""
        # Добавляем новое сообщение
        self.chat_context.append({"role": role, "content": content})
        
        # Если контекст превышает максимальный размер, удаляем самые старые сообщения
        while len(self.chat_context) > self.max_context_messages:
            self.chat_context.pop(0)

    def clear_context(self):
        """Очищает контекст чата"""
        self.chat_context = []

    @pyqtSlot()
    def load_model(self):
        if not os.path.exists(self.full_path_model):
            self.response_ready.emit(f"Model file not found: {self.full_path_model}", "error")
            return
        start_time = time.time()
        try:
            self.llm = self.llama(
                model_path=self.full_path_model,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=self.n_gpu_layers
            )
            self.response_ready.emit(f"Модель: {self.model_name}\n-успешно загружена за {time.time() - start_time:.2f} секунд\n\nЯ могу помочь вам с различными задачами. Вот что я умею:\n{self.commands_info}", "info")
        except Exception:
            self.response_ready.emit(f"Ошибка загрузки модели: {traceback.format_exc()}", "error")
        
    @pyqtSlot(str)
    def change_model(self, model_name: str):
        if not model_name:
            self.response_ready.emit("Не указано имя модели", "warning")
            return
        self.model_name = model_name
        self.full_path_model = f"{self.current_directory}/vendor/models/{self.model_name}.gguf"
        self.load_model()

    @pyqtSlot(str)
    def generate_response(self, user_input: str):
        if self.llm == None:
            self.response_ready.emit(f"Модель не была успешно загружена\nВаш запрос был экранирован: {user_input}", "error")
            return
        try:
            # Добавляем сообщение пользователя в контекст
            self.add_to_context("user", user_input)

            # Если пользователь спрашивает о возможностях, добавляем информацию о командах
            if "что ты умеешь" in user_input.lower() or "что ты можешь" in user_input.lower():
                user_input += f"\n\nВот что я умею:\n{self.commands_info}"

            # Формируем сообщения для модели с учетом контекста
            messages = self.chat_context.copy()
            
            response = self.llm.create_chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=2048,  # Увеличиваем максимальное количество токенов
                top_p=0.95,      # Добавляем параметр top_p для лучшей генерации
                top_k=40,        # Добавляем параметр top_k для лучшей генерации
                repeat_penalty=1.1,  # Добавляем штраф за повторения
                stop=["User:", "Assistant:", "\n\n"]  # Добавляем стоп-слова для предотвращения бесконечных ответов
            )
            
            response_text = response['choices'][0]['message']['content'].strip()
            # Добавляем ответ бота в контекст
            self.add_to_context("assistant", response_text)
            
            self.response_ready.emit(response_text, "")
        except Exception as e:
            error_message = f"Ошибка генерации ответа: {str(e)}"
            if "exceed context window" in str(e):
                error_message = "Превышен размер контекста. Попробуйте очистить историю чата командой /clear"
            self.response_ready.emit(error_message, "error")
