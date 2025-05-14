import os
import traceback
from PyQt6.QtCore import QObject, pyqtSignal
from llama_cpp import Llama

class ModelWorker(QObject):
    responseReady = pyqtSignal(list)
    finished = pyqtSignal()

    def __init__(self, prompt: str, model_path: str):
        super().__init__()
        self.prompt = prompt
        self.model_path = model_path
        self.llm = None
        self.dialog = []

    def load_model(self):
        try:
            if not os.path.exists(self.model_path):
                self.responseReady.emit([f"Файл не найден: {self.model_path}", "error"])
                self.finished.emit()
                return

            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=2048,
                n_threads=6,
                n_gpu_layers=0
            )
        except Exception as e:
            self.responseReady.emit([f"Ошибка: {traceback.format_exc()}", "error"])
            self.finished.emit()

    def run(self):
        if not self.llm:
            self.responseReady.emit(["Модель не загружена", "error"])
            self.finished.emit()
            return

        try:
            self.dialog.append({"role": "user", "content": self.prompt})
            
            response = self.llm.create_chat_completion(
                messages=self.dialog,
                temperature=0.7,
                max_tokens=512
            )
            
            answer = response['choices'][0]['message']['content']
            self.responseReady.emit([answer, "response"])
            
        except Exception as e:
            self.responseReady.emit([f"Ошибка: {traceback.format_exc()}", "error"])
        finally:
            self.finished.emit()