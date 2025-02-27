import sys
from PyQt6.QtWidgets import QApplication
from app.core.hotkeys import HotkeyManager
from app.core.audio import AudioController
from app.ui.tray_icon import TrayIcon
from app.ui.settings import SettingsWindow
from app.utils.config_manager import SettingsManager
from app.utils.logger import logger

class App:
    def __init__(self):
        self.settings = SettingsManager()
        self.audio = AudioController()
        self.hotkeys = HotkeyManager()
        self.tray_icon = TrayIcon(self.show_settings)
        self.settings_window = None


        # Связи
        self.hotkeys.volume_up_triggered.connect(self.audio.volume_up)
        self.hotkeys.volume_down_triggered.connect(self.audio.volume_down)
        self.tray_icon.exit_action.triggered.connect(self.quit)

    def run(self):
        self.tray_icon.show()
        logger.info("Приложение запущено")

    def show_settings(self):
        if not self.settings_window:
            self.settings_window = SettingsWindow(self.audio)
        self.settings_window.show()
        logger.info("Окно настроек отображено")

    def quit(self):
        self.settings.save()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    application = App()
    application.run()
    sys.exit(app.exec())
