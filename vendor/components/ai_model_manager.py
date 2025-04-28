from typing import Optional
import os

class AI_Bot:
    def __init__(self, language: str = "en", model: Optional[str] = None, message: str = "Просто скажи, что ты есть!"):
        self.language:str = language
        self.model:str = model
        self.user_message:str = message
        self.storage_model:str = "vendor/models"
        if not os.path.isdir(self.storage_model):
            os.mkdir(self.storage_model)
        
    def set_model(self, model:str):
        self.model = model

    def set_language(self, language: str):
        self.language = language

    def set_message(self, message: str):
        self.user_message = message

    def ai_response(self) -> list:
        if self.model == None: return ["⚠️ No AI models have been installed", "error"]
        message = f"Message AI: \n{self.user_message}\nSelected model: {self.model}"
        return [message, ""]
