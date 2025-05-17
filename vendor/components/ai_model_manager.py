import os
import traceback
from llama_cpp import Llama

class ModelManager:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self.dialog = []

    def load_model(self):
        try:
            if not os.path.exists(self.model_path):
                return False, f"Файл модели: {self.model_path} - не был найден"
            
            self.model = Llama(
                model_path=self.model_path,
                n_ctx=2048,
                n_threads=4
            )
            return True, f"Модель успешно загружена: {self.model_path}"
            
        except Exception as e:
            return False, f"Ошибка при загрузке модели: {traceback.format_exc()}"

    def process_content(self, content):
        return content.replace('<think>', '').replace('</think>', '')

    def generate_response(self, prompt: str):
        try:
            if not self.model:
                return "Ошибка: Модель не загружена"
            
            self.dialog.append({"role": "user", "content": prompt})
            
            response = self.model(
                prompt,
                max_tokens=512,
                temperature=0.7,
                stop=["User:", "\n\n"]
            )
            
            generated_text = response['choices'][0]['text']
            cleaned_response = self.process_content(generated_text)
            
            self.dialog.append({"role": "assistant", "content": cleaned_response})
            return cleaned_response
            
        except Exception as e:
            return f"Ошибка при генерации ответа: {traceback.format_exc()}"