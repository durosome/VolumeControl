import keyboard
from PyQt6.QtCore import QObject, pyqtSignal
from app.utils.logger import logger

class HotkeyManager(QObject):
    volume_up_triggered = pyqtSignal()
    volume_down_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._register_hotkeys()
        logger.info("Горячие клавиши зарегистрированы")

    def _register_hotkeys(self):
        # Явно регистрируем обе комбинации
        keyboard.add_hotkey("ctrl+shift+up", self._on_volume_up)
        keyboard.add_hotkey("ctrl+shift+down", self._on_volume_down)
        logger.debug("Клавиши: Ctrl+Shift+Up/Down")

    def _on_volume_up(self):
        self.volume_up_triggered.emit()
        logger.debug("Volume Up pressed")

    def _on_volume_down(self):
        self.volume_down_triggered.emit()
        logger.debug("Volume Down pressed")