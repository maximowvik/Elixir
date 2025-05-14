import os
import requests
import re

class Download_Manager:
    def __init__(self, on_download_finished=None):
        self.on_download_finished = on_download_finished

    def get_filename_from_response(self, response, url):
        content_disposition = response.headers.get('Content-Disposition')
        if content_disposition:
            filenames = re.findall('filename="?([^"]+)"?', content_disposition)
            if filenames:
                return filenames[0]

        local_filename = url.split("/")[-1]
        if not local_filename:
            return "downloaded_file"
        return local_filename

    def download_file(self, url, folder_name, on_download_finished=None):
        print(f"Start download from {url} into folder {folder_name}")
        try:
            full_folder_path = os.path.join("vendor", folder_name)
            os.makedirs(full_folder_path, exist_ok=True)

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                              "AppleWebKit/537.36 (KHTML, like Gecko) " +
                              "Chrome/112.0.0.0 Safari/537.36"
            }

            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()

            local_filename = self.get_filename_from_response(response, url)
            file_path = os.path.join(full_folder_path, local_filename)

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            if on_download_finished:
                on_download_finished()

            return [f"Файл успешно загружен: {file_path}", "bot", "info"]

        except Exception as e:
            return [f"Ошибка загрузки: {str(e)}", "bot", "error"]
