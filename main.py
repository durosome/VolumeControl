import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *

DARK_STYLE = """
    QWidget {
        background-color: #2D2D2D;
        color: #CCCCCC;
        font-family: Segoe UI;
        font-size: 12px;
    }
    
    QTabWidget::pane {
        border: 1px solid #404040;
        margin: -1px 0 0 -1px;
    }
    
    QTabBar::tab {
        background: #353535;
        border: 1px solid #404040;
        padding: 8px 15px;
    }
    
    QTabBar::tab:selected {
        background: #2D2D2D;
        border-bottom-color: #2D2D2D;
    }
    
    QLineEdit {
        background: #353535;
        border: 1px solid #404040;
        padding: 5px;
        border-radius: 3px;
    }
    
    QListWidget {
        background: #353535;
        border: 1px solid #404040;
        border-radius: 3px;
    }
    
    QPushButton {
        background: #404040;
        border: 1px solid #4D4D4D;
        padding: 5px 15px;
        border-radius: 3px;
    }
    
    QPushButton:hover {
        background: #4D4D4D;
    }
    
    QMenu {
        background: #353535;
        border: 1px solid #404040;
    }
    
    QMenu::item:selected {
        background: #404040;
    }
"""

class HotkeyLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.keys = []
        self.modifiers = Qt.KeyboardModifier.NoModifier

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        # Игнорируем одиночные нажатия модификаторов
        if key in [Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta]:
            return

        # Обрабатываем модификаторы
        modifier_names = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            modifier_names.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            modifier_names.append("Shift")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            modifier_names.append("Alt")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            modifier_names.append("Win")

        # Обрабатываем основную клавишу
        key_name = QKeySequence(key).toString(QKeySequence.SequenceFormat.NativeText)
        
        # Для цифр Numpad добавляем префикс
        if event.nativeVirtualKey() >= 0x60 and event.nativeVirtualKey() <= 0x6F:
            key_name = f"Num{key_name}"

        # Формируем полную комбинацию
        full_sequence = "+".join(modifier_names + [key_name])

        # Обновляем текст в поле
        self.setText(full_sequence)
        
        # Сохраняем комбинацию для последующего использования
        self.modifiers = modifiers
        self.keys = [key]

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Настройки")
        self.setMinimumSize(600, 400)
        self.init_ui()

    def init_ui(self):
        # Создаем вкладки
        tab_widget = QTabWidget()
        
        # Вкладка Hotkeys
        hotkeys_tab = QWidget()
        hotkeys_layout = QFormLayout()
        
        # Группы 1-3
        self.group_edits = []
        for i in range(1, 4):
            edit = HotkeyLineEdit()
            hotkeys_layout.addRow(QLabel(f"Группа {i} -"), edit)
            self.group_edits.append(edit)
        
        hotkeys_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        # Контролы громкости
        self.volume_controls = {}
        for control in ["Vol+", "Vol-", "Mute"]:
            edit = HotkeyLineEdit()
            hotkeys_layout.addRow(QLabel(f"{control} -"), edit)
            self.volume_controls[control] = edit
        
        hotkeys_tab.setLayout(hotkeys_layout)

        # Вкладка Apps
        apps_tab = QWidget()
        apps_layout = QHBoxLayout()
        
        # Левый список
        left_panel = QVBoxLayout()
        self.apps_list = QListWidget()
        self.apps_list.addItems(["Приложение 1", "Приложение 2", "Приложение 3"])
        left_panel.addWidget(self.apps_list)
        
        # Кнопки
        btn_panel = QHBoxLayout()
        btn_panel.addWidget(QPushButton("Delete"))
        btn_panel.addWidget(QPushButton("Save"))
        left_panel.addLayout(btn_panel)
        
        # Правые вкладки
        right_tabs = QTabWidget()
        for i in range(1, 4):
            tab = QWidget()
            tab.layout = QVBoxLayout()
            tab.list = QListWidget()
            tab.list.addItems([f"Элемент {j}" for j in range(1, 6)])
            tab.layout.addWidget(tab.list)
            tab.setLayout(tab.layout)
            right_tabs.addTab(tab, f"Категория {i}")
        
        apps_layout.addLayout(left_panel, 40)
        apps_layout.addWidget(right_tabs, 60)
        apps_tab.setLayout(apps_layout)

        # Вкладка Etc
        etc_tab = QWidget()
        etc_layout = QVBoxLayout()
        etc_layout.addWidget(QLabel("Дополнительные настройки"))
        etc_tab.setLayout(etc_layout)

        # Добавляем вкладки
        tab_widget.addTab(hotkeys_tab, "Hotkeys")
        tab_widget.addTab(apps_tab, "Apps")
        tab_widget.addTab(etc_tab, "Etc")

        main_layout = QVBoxLayout()
        main_layout.addWidget(tab_widget)
        self.setLayout(main_layout)

class TrayApp(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon("icon.ico"))
        
        self.menu = QMenu()
        self.settings_action = self.menu.addAction("Настройки")
        self.exit_action = self.menu.addAction("Выход")
        
        self.settings_action.triggered.connect(self.show_settings)
        self.exit_action.triggered.connect(QApplication.instance().quit)
        
        self.setContextMenu(self.menu)
        self.settings_window = None

    def show_settings(self):
        if not self.settings_window:
            self.settings_window = SettingsWindow()
        self.settings_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Применяем кастомные стили
    app.setStyleSheet(DARK_STYLE)
    
    # Скрываем главное окно
    main_window = QMainWindow()
    main_window.hide()
    
    tray = TrayApp(main_window)
    tray.show()
    
    sys.exit(app.exec())