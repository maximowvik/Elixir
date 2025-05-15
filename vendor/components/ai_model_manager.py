import os
import traceback
from PyQt6.QtCore import QObject, pyqtSignal
import requests
import json

API_KEY = ""
MODEL = "deepseek/deepseek-r1"

class ModelWorker(QObject):
    responseReady = pyqtSignal(list)
    finished = pyqtSignal()

    def __init__(self, prompt: str, model_path: str):
        super().__init__()
        self.prompt = prompt
        self.model_path = model_path
        self.dialog = []

    def load_model(self):
        try:
            if not os.path.exists(self.model_path):
                self.responseReady.emit([f"Файл модели: {self.model_path} - не был найден", "error"])
                self.finished.emit()
                return
            else:
                self.responseReady.emit([f"Файл модели: {self.model_path} - был найден"])
            
        except Exception as e:
            self.responseReady.emit([f"Ошибка: {traceback.format_exc()}", "error"])
            self.finished.emit()

    def run(self):
        try:
            self.dialog.append({"role": "user", "content": self.prompt})
            
            response = self.chat_stream(self.prompt)
            self.responseReady.emit([response, "response"])
            
        except Exception as e:
            self.responseReady.emit([f"Ошибка: {traceback.format_exc()}", "error"])
        finally:
            self.finished.emit()
            
    def process_content(self, content):
        return content.replace('<think>', '').replace('</think>', '')

    def chat_stream(self, prompt):
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True
        }

        with requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            stream=True
        ) as response:
            if response.status_code != 200:
                self.responseReady.emit([f"Ошибка API: {response.status_code}", "error"])
                return ""

            full_response = []
            
            for chunk in response.iter_lines():
                if chunk:
                    chunk_str = chunk.decode('utf-8').replace('data: ', '')
                    try:
                        chunk_json = json.loads(chunk_str)
                        if "choices" in chunk_json:
                            content = chunk_json["choices"][0]["delta"].get("content", "")
                            if content:
                                cleaned = self.process_content(content)
                                full_response.append(cleaned)
                    except:
                        pass

            print()  # Перенос строки после завершения потока
            return ''.join(full_response)