import os
import requests

class Download_Manager:
    def __init__(self, on_download_finished=None):
        self.on_download_finished = on_download_finished
        

    def download_file(self, url, folder_name, on_download_finished=None):
        try:
            os.makedirs(folder_name, exist_ok=True)

            local_filename = url.split("/")[-1]
            file_path = os.path.join(f"vendor/{folder_name}", local_filename)

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                              "AppleWebKit/537.36 (KHTML, like Gecko) " +
                              "Chrome/112.0.0.0 Safari/537.36"
            }

            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            if on_download_finished:
                on_download_finished()

            return [f"Файл успешно загружен: {file_path}", "bot", "info"]

        except Exception as e:
            return [f"Ошибка загрузки: {str(e)}", "bot", "error"]