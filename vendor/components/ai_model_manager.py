from llama_cpp import Llama
import time
import os
import traceback
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

class WorkModel(QObject):
    response_ready = pyqtSignal(str, str)  # text, type

    def __init__(self, current_directory: str, model_name: str, llamma: Llama = None, n_ctx: int = 512, n_threads: int = 8, n_gpu_layers: int = 0) -> None:
        super().__init__()
        self.current_directory = current_directory
        self.model_name = model_name
        self.full_path_model = os.path.join(self.current_directory, "vendor", "models", f"{self.model_name}.gguf") if self.model_name else ""
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers
        self.llama = llamma
        self.llm = None
        self.chat_context = []
        self.commands_info = ""
        self.max_context_messages = 5  # Limit the number of messages in the context

    def set_commands_info(self, commands_info: str):
        """Set information about available commands"""
        self.commands_info = commands_info

    def add_to_context(self, role: str, content: str):
        """Add a message to the chat context"""
        self.chat_context.append({"role": role, "content": content})

        # If the context exceeds the maximum size, remove the oldest messages
        while len(self.chat_context) > self.max_context_messages:
            self.chat_context.pop(0)

    def clear_context(self):
        """Clear the chat context"""
        self.chat_context = []

    @pyqtSlot()
    def load_model(self):
        if not self.full_path_model:
            self.response_ready.emit(f"Model file not found: {self.full_path_model}", "error")
            return
        elif not os.path.exists(self.full_path_model):
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
            self.response_ready.emit(
                f"Model: {self.model_name}\nSuccessfully loaded in {time.time() - start_time:.2f} seconds\n\n"
                f"I can help you with various tasks. Here's what I can do:\n{self.commands_info}",
                "info"
            )
        except Exception:
            self.response_ready.emit(f"Error loading model: {traceback.format_exc()}", "error")

    @pyqtSlot(str)
    def change_model(self, model_name: str):
        if not model_name:
            self.response_ready.emit("Model name not specified", "warning")
            return

        self.model_name = model_name
        self.full_path_model = os.path.join(self.current_directory, "vendor", "models", f"{self.model_name}.gguf")
        self.load_model()

    @pyqtSlot(str)
    def generate_response(self, user_input: str):
        if self.llm is None:
            self.response_ready.emit(f"Модель не была успешно загружена\nВаш запрос был экранирован: {user_input}", "error")
            return

        try:
            self.add_to_context("user", user_input)

            if "кто ты" in user_input.lower():
                response_text = "Привет! Я ваш виртуальный помощник. Чем могу помочь?"
                self.add_to_context("assistant", response_text)
                self.response_ready.emit(response_text, "")
                return

            messages = self.chat_context.copy()

            response = self.llm.create_chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=2048,
                top_p=0.95,
                top_k=40,
                repeat_penalty=1.1,
                stop=["User:", "Assistant:", "\n\n"]
            )

            response_text = response['choices'][0]['message']['content'].strip()
            self.add_to_context("assistant", response_text)

            self.response_ready.emit(response_text, "")
        except Exception as e:
            error_message = f"Ошибка генерации ответа: {str(e)}"
            if "exceed context window" in str(e):
                error_message = "Превышен размер контекста. Попробуйте очистить историю чата командой /clear"
            self.response_ready.emit(error_message, "error")

