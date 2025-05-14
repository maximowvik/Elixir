import os
import time
import traceback
from llama_cpp import Llama  # Правильный импорт
from PyQt6.QtCore import QObject, pyqtSignal


class ModelWorker(QObject):
    responseReady = pyqtSignal(list)  # Сигнал: [text, message_type]
    finished = pyqtSignal()

    def __init__(self, prompt: str, model_path: str):
        super().__init__()
        self.prompt = prompt
        self.model_path = model_path
        self.llm = None

    def load_model(self):
        """Загружает модель (вызывается в главном потоке!)."""
        try:
            # Проверяем, существует ли файл модели
            if not os.path.isfile(self.model_path):
                self.responseReady.emit([f"Файл модели не найден: {self.model_path}", "error"])
                self.finished.emit()
                return

            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=2048,
                n_threads=8,
                n_gpu_layers=0,  # Если есть GPU, можно увеличить
                verbose=False
            )
        except Exception:
            self.responseReady.emit([f"Ошибка загрузки модели: {traceback.format_exc()}", "error"])
            self.finished.emit()

    def run(self):
        """Генерирует ответ в фоновом потоке."""
        if not self.llm:
            self.responseReady.emit(["Модель не загружена!", "error"])
            self.finished.emit()
            return

        try:
            response = self.llm.create_chat_completion(
                messages=[{"role": "user", "content": self.prompt}],
                temperature=0.7,
                max_tokens=256,
            )
            answer = response['choices'][0]['message']['content']
            self.responseReady.emit([answer, "response"])
        except Exception:
            self.responseReady.emit([f"Ошибка генерации: {traceback.format_exc()}", "error"])
        finally:
            self.finished.emit()