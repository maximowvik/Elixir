from PyQt6.QtGui import QIcon

class IconManager:
    @staticmethod
    def get_icon(window_name):
        icons = {
            "main": "vendor/icon/logonew.ico",
            "qr_code": "vendor/icon/scan.ico",
            "speed_test": "vendor/icon/speed.ico",
            "paint": "vendor/icon/paint.ico",
            "pc_info": "vendor/icon/info.ico",
            "translator": "vendor/icon/journal.ico",
            "screen_recorder": "vendor/icon/video.ico",
            "screen_share": "vendor/icon/computer.ico",
        }
        return QIcon(icons.get(window_name, "vendor/icon/icon.ico"))
    @staticmethod
    def get_images(window_name) -> str:
        images = {
            "main": "vendor/images/logonew.png",
            "main_logo": "vendor/images/logo.png",
            "qr_code": "vendor/images/scan.png",
            "speed_test": "vendor/images/speed.png",
            "paint": "vendor/images/paint.png",
            "pc_info": "vendor/images/info.png",
            "translator": "vendor/images/journal.png",
            "screen_recorder": "vendor/images/video.png",
            "screen_share": "vendor/images/computer.png",
            "chat":"vendor/images/chat.png",
            "screenshot":"vendor/images/folder.png",
            "browser":"vendor/images/globe.png",
            "audio":"vendor/images/audio.png",
            "microphone":"vendor/images/mic.png",
            "speed_test":"vendor/images/speed.png",
            "change_theme":"vendor/images/themes.png",
            "button_close":"vendor/images/close.png",
        }
        return images.get(window_name, "vendor/images/images.png")