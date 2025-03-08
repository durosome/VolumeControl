from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from models import SettingsManager, GroupManager
from windows import SettingsWindow

class TrayApp(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_data = SettingsManager.load_settings()
        self.group_manager = GroupManager()
        self.group_manager.initialize(self.settings_data)
        self.volume_controls = self.settings_data.get("volume_controls", {})
        self.settings_window = None
        self.init_ui()

    def init_ui(self):
        try:
            self.setIcon(QIcon("icon.ico"))
        except:
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.blue)
            self.setIcon(QIcon(pixmap))
        
        menu = QMenu()
        
        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.show_settings)
        
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.on_exit)
        
        self.setContextMenu(menu)

    def show_settings(self):
        if not self.settings_window:
            self.settings_window = SettingsWindow(
                self.group_manager,
                self.volume_controls
            )
        self.settings_window.show()

    def on_exit(self):
        # Сохраняем настройки при выходе
        SettingsManager.save_settings(
            self.group_manager,
            self.volume_controls
        )
        
        if self.settings_window:
            self.settings_window.close()
            
        QApplication.instance().quit()