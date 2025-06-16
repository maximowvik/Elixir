from PyQt6.QtGui import QIcon

class IconManager:
    @staticmethod
    def get_icon(icon_name:str) -> QIcon:
        icons = {
            "main": "vendor/icon/logonew.ico",
            "qr_code": "vendor/icon/scan.ico",
            "speed_test": "vendor/icon/speed.ico",
            "paint": "vendor/icon/paint.ico",
            "chat": "vendor/icon/chat.ico",
            "pc_info": "vendor/icon/info.ico",
            "translator": "vendor/icon/journal.ico",
            "screen_recorder": "vendor/icon/video.ico",
            "screen_share": "vendor/icon/computer.ico",
            "audio_recording": "vendor/icon/mic.ico",
            "audio": "vendor/icon/audio.ico",
            "screenshot":"vendor/icon/folder.ico"
        }
        return QIcon(icons.get(icon_name, "vendor/icon/icon.ico"))
    @staticmethod
    def get_images(image_name:str) -> str:
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
            "roll_up_button":"vendor/images/minus.png",
            "expanded": "vendor/images/expand.png",
            "back":"vendor/images/back.png",
            "forward":"vendor/images/forward.png",
            "reload":"vendor/images/reload.png",
            "home":"vendor/images/home.png",
            "plus":"vendor/images/plus.png",
            "send_link":"vendor/images/send2.png",
            "lock":"vendor/images/lock.png",
            "unlock":"vendor/images/unlock.png",
            "send":"vendor/images/send.png",
            "user":"vendor/images/SVG/user.svg",
            "computer":"vendor/images/SVG/computer.svg",
            "bot":"vendor/images/SVG/bot.svg",
            "model":"vendor/images/SVG/model.svg",
            "mute":"vendor/images/SVG/mute.svg",
            "unmute":"vendor/images/SVG/unmute.svg",
        }
        return images.get(image_name, "vendor/images/images.png")