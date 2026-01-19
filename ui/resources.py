import os.path
from PySide6.QtGui import QIcon


RESOURCES_PATH = os.path.join(os.path.dirname(__file__), 'resources')
ICONS_PATH = os.path.join(RESOURCES_PATH, 'icons')


class Icons:
    binary_24 = 'binary-24.png'


def icon_path(icon_name: str) -> str:
    return os.path.join(ICONS_PATH, icon_name)


def load_icon(icon_name: str) -> QIcon:
    return QIcon(icon_path(icon_name))
