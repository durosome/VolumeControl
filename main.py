import sys
import comtypes
import json
from pathlib import Path
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from pycaw.pycaw import AudioUtilities

comtypes.CoInitialize()

# Модель данных
class Group:
    def __init__(self, name="New Category", hotkey="", apps=None):
        self._name = name
        self.hotkey = hotkey
        self.apps = apps if apps else []
        self.observers = []

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        self.notify_observers()

    def add_observer(self, callback):
        if callback not in self.observers:
            self.observers.append(callback)

    def notify_observers(self):
        for callback in self.observers:
            callback(self)

class GroupManager:
    def __init__(self):
        self.groups = []
        
    def initialize(self, settings_data):
        self.groups.clear()
        for g_data in settings_data.get("groups", []):
            group = Group(
                name=g_data.get("name", "New Category"),
                hotkey=g_data.get("hotkey", ""),
                apps=g_data.get("apps", [])
            )
            self.groups.append(group)
            
    def get_group_data(self):
        return [{
            "name": g.name,
            "hotkey": g.hotkey,
            "apps": g.apps
        } for g in self.groups]

class SettingsManager:
    SETTINGS_FILE = "app_settings.json"
    
    @classmethod
    def load_settings(cls):
        try:
            if Path(cls.SETTINGS_FILE).exists():
                with open(cls.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
        return cls.default_settings()

    @classmethod
    def save_settings(cls, group_manager, volume_controls):
        data = {
            "groups": group_manager.get_group_data(),
            "volume_controls": volume_controls
        }
        try:
            with open(cls.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    @staticmethod
    def default_settings():
        return {
            "groups": [],
            "volume_controls": {
                "Vol+": "",
                "Vol-": "",
                "Mute": ""
            }
        }

# Компоненты UI
class HotkeyLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMinimumWidth(120)
        self.keys = []
        self.modifiers = Qt.KeyboardModifier.NoModifier

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key in [Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta]:
            return

        modifier_names = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            modifier_names.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            modifier_names.append("Shift")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            modifier_names.append("Alt")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            modifier_names.append("Win")

        key_name = QKeySequence(key).toString(QKeySequence.SequenceFormat.NativeText)
        
        if event.nativeVirtualKey() >= 0x60 and event.nativeVirtualKey() <= 0x6F:
            key_name = f"Num{key_name}"

        full_sequence = "+".join(modifier_names + [key_name])
        self.setText(full_sequence)
        self.modifiers = modifiers
        self.keys = [key]

class CustomListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected_item()
        else:
            super().keyPressEvent(event)

    def delete_selected_item(self):
        if current_item := self.currentItem():
            self.takeItem(self.row(current_item))

class EditableTabBar(QTabBar):
    edit_requested = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor = QLineEdit(self)
        self.editor.setWindowFlags(Qt.WindowType.Popup)
        self.editor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.editor.setMinimumWidth(120)
        self.editor.hide()
        self.editor.editingFinished.connect(self.finish_editing)
        self.editor.installEventFilter(self)
        self.current_edit_index = -1

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.editor.hide()
            return True
        return super().eventFilter(obj, event)

    def mouseDoubleClickEvent(self, event):
        index = self.tabAt(event.pos())
        if index >= 0:
            self.start_edit(index)
        super().mouseDoubleClickEvent(event)

    def start_edit(self, index):
        self.current_edit_index = index
        rect = self.tabRect(index)
        global_pos = self.mapToGlobal(rect.topLeft())
        self.editor.move(global_pos)
        self.editor.resize(max(rect.width(), 120), rect.height())
        self.editor.setText(self.tabText(index))
        self.editor.selectAll()
        self.editor.show()
        self.editor.setFocus()

    def finish_editing(self):
        if self.current_edit_index >= 0:
            new_text = self.editor.text()
            if new_text:
                self.setTabText(self.current_edit_index, new_text)
                self.edit_requested.emit(self.current_edit_index)
            self.editor.hide()
            self.current_edit_index = -1

class GroupTabWidget(QTabWidget):
    def __init__(self, group_manager, parent=None):
        super().__init__(parent)
        self.group_manager = group_manager
        self.setTabPosition(QTabWidget.TabPosition.South)
        self.init_tabs()
        
    def init_tabs(self):
        for group in self.group_manager.groups:
            self.add_group_tab(group)
            
    def add_group_tab(self, group):
        tab = QWidget()
        tab.list = CustomListWidget()
        tab.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tab.layout = QVBoxLayout()
        tab.layout.addWidget(tab.list)
        tab.setLayout(tab.layout)
        self.addTab(tab, group.name)

class GroupsSettingsWidget(QWidget):
    def __init__(self, group_manager, parent=None):
        super().__init__(parent)
        self.group_manager = group_manager
        self.init_ui()
        
    def init_ui(self):
        layout = QFormLayout()
        self.group_edits = []
        
        for group in self.group_manager.groups:
            edit = HotkeyLineEdit()
            edit.setText(group.hotkey)
            edit.textChanged.connect(lambda text, g=group: setattr(g, 'hotkey', text))
            
            label = QLabel(f"{group.name} -")
            group.add_observer(lambda g, lbl=label: lbl.setText(f"{g.name} -"))
            
            layout.addRow(label, edit)
            self.group_edits.append(edit)
            
        self.setLayout(layout)

class SettingsWindow(QWidget):
    def __init__(self, group_manager, volume_controls):
        super().__init__()
        self.group_manager = group_manager
        self.volume_controls = volume_controls
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 400)
        self.init_ui()
        
    def init_ui(self):
        tab_widget = QTabWidget()
        
        # Вкладка Hotkeys
        hotkeys_tab = GroupsSettingsWidget(self.group_manager)
        
        # Вкладка Apps
        apps_tab = QWidget()
        layout = QHBoxLayout()
        self.apps_widget = GroupTabWidget(self.group_manager)
        layout.addWidget(self.apps_widget)
        apps_tab.setLayout(layout)
        
        # Вкладка Volume Controls
        volume_tab = self.create_volume_tab()
        
        tab_widget.addTab(hotkeys_tab, "Hotkeys")
        tab_widget.addTab(apps_tab, "Apps")
        tab_widget.addTab(volume_tab, "Volume")
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(tab_widget)
        self.setLayout(main_layout)
        
    def create_volume_tab(self):
        tab = QWidget()
        layout = QFormLayout()
        
        self.volume_edits = {}
        for control in ["Vol+", "Vol-", "Mute"]:
            edit = HotkeyLineEdit()
            edit.setText(self.volume_controls.get(control, ""))
            layout.addRow(QLabel(f"{control} -"), edit)
            self.volume_edits[control] = edit
            
        tab.setLayout(layout)
        return tab

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
        self.setIcon(QIcon("icon.ico"))
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
        # Сохраняем настройки перед выходом
        volume_controls = {
            "Vol+": self.settings_window.volume_edits["Vol+"].text(),
            "Vol-": self.settings_window.volume_edits["Vol-"].text(),
            "Mute": self.settings_window.volume_edits["Mute"].text()
        } if self.settings_window else {}
        
        SettingsManager.save_settings(self.group_manager, volume_controls)
        QApplication.instance().quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Загрузка стилей
    try:
        with open('dark_theme.qss', 'r') as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print(f"Error loading styles: {e}")
    
    tray = TrayApp()
    tray.show()
    
    app.exec()