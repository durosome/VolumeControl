from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from app.utils.logger import logger

class TrayIcon(QSystemTrayIcon):
    def __init__(self, on_settings_clicked, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon("assets/icons/icon.png"))
        self._create_menu()
        self.on_settings = on_settings_clicked
        logger.info("Трей-иконка инициализирована")

    def _create_menu(self):
        menu = QMenu()
        
        # Пункты меню
        self.settings_action = QAction("Настройки", self)
        self.settings_action.triggered.connect(self._open_settings)
        self.exit_action = QAction("Выход", self)
        
        menu.addAction(self.settings_action)
        menu.addAction(self.exit_action)
        self.setContextMenu(menu)

    def _open_settings(self):
        self.on_settings()
        logger.debug("Запрошено открытие настроек")