from ai_model_manager import ModelManager

def main():
    # Путь к вашей GGUF модели
    model_path = "models/your_model.gguf"
    
    # Создаем экземпляр менеджера моделей
    model_manager = ModelManager(model_path)
    
    # Загружаем модель
    success, message = model_manager.load_model()
    print(message)
    
    if success:
        # Пример использования
        while True:
            user_input = input("\nВведите ваш запрос (или 'выход' для завершения): ")
            if user_input.lower() == 'выход':
                break
                
            response = model_manager.generate_response(user_input)
            print("\nОтвет модели:", response)

if __name__ == "__main__":
    main() 