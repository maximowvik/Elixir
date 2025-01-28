from PyQt6.QtGui import QIcon

class IconManager:
    @staticmethod
    def get_icon(window_name):
        icons = {
            "main": "pic/logonew.png",
            "qr_code": "icon/scan.ico",
            "speed_test": "icon/speed.ico",
            "paint": "icon/paint.ico",
            "pc_info": "icon/info.ico",
            "translator": "icon/journal.ico",
            "screen_recorder": "icon/video.ico",
            "screen_share": "icon/computer.ico",
        }
        return QIcon(icons.get(window_name, "icon/icon.ico"))