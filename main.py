import sys
import comtypes
import os
import json
from pathlib import Path
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from pycaw.pycaw import AudioUtilities

comtypes.CoInitialize()

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
    def save_settings(cls, data):
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
            "groups": [
                {"name": "Category 1", "hotkey": "", "apps": []},
                {"name": "Category 2", "hotkey": "", "apps": []},
                {"name": "Category 3", "hotkey": "", "apps": []}
            ],
            "volume_controls": {
                "Vol+": "",
                "Vol-": "",
                "Mute": ""
            }
        }

def load_stylesheet():
    try:
        with open('dark_theme.qss', 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading stylesheet: {e}")
        return ""

class HotkeyLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.keys = []
        self.modifiers = Qt.KeyboardModifier.NoModifier
        self.setMinimumWidth(120)

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

class AudioSessionWidget(QListWidgetItem):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.process_name = self.get_process_name()
        self.setText(self.process_name)

    def get_process_name(self):
        try:
            return self.session.Process and self.session.Process.name() or "System"
        except:
            return "Unknown"

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

class EditableTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabBar(EditableTabBar(self))
        self.tabBar().edit_requested.connect(self.handle_tab_edited)

    def handle_tab_edited(self, index):
        self.tabBar().update()
        self.window().update_group_names()

class EditableLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumWidth(120)
        self.editor = QLineEdit(self)
        self.editor.setWindowFlags(Qt.WindowType.Popup)
        self.editor.setMinimumWidth(120)
        self.editor.hide()
        self.editor.editingFinished.connect(self.finish_editing)
        self.editor.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.editor.hide()
            return True
        return super().eventFilter(obj, event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_editing()
        super().mouseDoubleClickEvent(event)

    def start_editing(self):
        global_pos = self.mapToGlobal(QPoint(0, 0))
        self.editor.move(global_pos)
        self.editor.resize(max(self.width(), 120), self.height())
        self.editor.setText(self.text())
        self.editor.selectAll()
        self.editor.show()
        self.editor.setFocus()

    def finish_editing(self):
        new_text = self.editor.text()
        if new_text:
            self.setText(new_text)
        self.editor.hide()
        self.window().update_group_names_by_label(self)

class AppsTab(QWidget):
    tab_renamed = pyqtSignal(int, str)

    def __init__(self):
        super().__init__()
        self.sessions = []
        self.init_ui()
        self.init_audio()
        self.start_updater()

    def init_ui(self):
        layout = QHBoxLayout()
        
        self.left_panel = CustomListWidget()
        self.left_panel.setDragEnabled(True)
        
        btn_panel = QHBoxLayout()
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_item)
        btn_panel.addWidget(self.delete_btn)
        
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.left_panel)
        left_layout.addLayout(btn_panel)
        
        self.right_tabs = EditableTabWidget()
        self.right_tabs.setTabPosition(QTabWidget.TabPosition.South)
        
        for i in range(3):
            tab = QWidget()
            tab.list = CustomListWidget()
            tab.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            tab.list.customContextMenuRequested.connect(self.show_context_menu)
            tab.list.setAcceptDrops(True)
            tab.layout = QVBoxLayout()
            tab.layout.addWidget(tab.list)
            tab.setLayout(tab.layout)
            self.right_tabs.addTab(tab, f"Category {i+1}")
        
        layout.addLayout(left_layout, 40)
        layout.addWidget(self.right_tabs, 60)
        self.setLayout(layout)

    def show_context_menu(self, pos):
        list_widget = self.sender()
        if item := list_widget.itemAt(pos):
            menu = QMenu()
            delete_action = menu.addAction("Delete")
            if menu.exec(list_widget.mapToGlobal(pos)) == delete_action:
                list_widget.takeItem(list_widget.row(item))

    def init_audio(self):
        self.update_sessions()

    def start_updater(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_sessions)
        self.timer.start(1000)

    def update_sessions(self):
        sessions = AudioUtilities.GetAllSessions()
        new_sessions = [s for s in sessions if s.Process]
        
        if len(new_sessions) != len(self.sessions):
            self.left_panel.clear()
            for session in new_sessions:
                item = AudioSessionWidget(session)
                self.left_panel.addItem(item)
            self.sessions = new_sessions

    def delete_item(self):
        if current_tab := self.right_tabs.currentWidget():
            if current_item := current_tab.list.currentItem():
                current_tab.list.takeItem(current_tab.list.row(current_item))

    def add_application_to_group(self, app_name, group_index):
        tab_widget = self.right_tabs.widget(group_index)
        if not any(tab_widget.list.item(i).text() == app_name 
                 for i in range(tab_widget.list.count())):
            tab_widget.list.addItem(QListWidgetItem(app_name))

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = SettingsManager.load_settings()
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 250)
        self.resize(600, 300)
        self.init_ui()
        self.load_current_settings()

    def init_ui(self):
        tab_widget = QTabWidget()
        
        hotkeys_tab = QWidget()
        main_hotkeys_layout = QHBoxLayout()
        
        self.groups_layout = QFormLayout()
        self.group_edits = []
        for i in range(3):
            edit = HotkeyLineEdit()
            label = EditableLabel(f"Category {i+1} -")
            label.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Preferred)
            self.groups_layout.addRow(label, edit)
            self.group_edits.append(edit)
        
        volume_layout = QFormLayout()
        self.volume_controls = {}
        for control in ["Vol+", "Vol-", "Mute"]:
            edit = HotkeyLineEdit()
            volume_layout.addRow(QLabel(f"{control} -"), edit)
            self.volume_controls[control] = edit
        
        main_hotkeys_layout.addLayout(self.groups_layout, 60)
        main_hotkeys_layout.addLayout(volume_layout, 40)
        hotkeys_tab.setLayout(main_hotkeys_layout)
        
        self.apps_tab = AppsTab()
        
        etc_tab = QWidget()
        etc_layout = QVBoxLayout()
        etc_layout.addWidget(QLabel("Additional Settings"))
        etc_tab.setLayout(etc_layout)

        tab_widget.addTab(hotkeys_tab, "Hotkeys")
        tab_widget.addTab(self.apps_tab, "Apps")
        tab_widget.addTab(etc_tab, "Etc")

        main_layout = QVBoxLayout()
        main_layout.addWidget(tab_widget)
        self.setLayout(main_layout)

    def load_current_settings(self):
        # Load group names and hotkeys
        for i in range(3):
            self.apps_tab.right_tabs.setTabText(i, self.settings["groups"][i]["name"])
            self.group_edits[i].setText(self.settings["groups"][i]["hotkey"])
            
            # Load apps in groups
            tab_widget = self.apps_tab.right_tabs.widget(i)
            tab_widget.list.clear()
            for app in self.settings["groups"][i]["apps"]:
                tab_widget.list.addItem(QListWidgetItem(app))

        # Load volume controls
        for control in ["Vol+", "Vol-", "Mute"]:
            self.volume_controls[control].setText(self.settings["volume_controls"][control])

    def save_current_settings(self):
        # Save group names and hotkeys
        for i in range(3):
            self.settings["groups"][i]["name"] = self.apps_tab.right_tabs.tabText(i)
            self.settings["groups"][i]["hotkey"] = self.group_edits[i].text()
            
            # Save apps in groups
            tab_widget = self.apps_tab.right_tabs.widget(i)
            self.settings["groups"][i]["apps"] = [
                tab_widget.list.item(j).text() 
                for j in range(tab_widget.list.count())
            ]

        # Save volume controls
        for control in ["Vol+", "Vol-", "Mute"]:
            self.settings["volume_controls"][control] = self.volume_controls[control].text()
            
        return SettingsManager.save_settings(self.settings)

    def update_group_names(self):
        for i in range(3):
            label = self.groups_layout.itemAt(i, QFormLayout.ItemRole.LabelRole).widget()
            label.setText(f"{self.apps_tab.right_tabs.tabText(i)} -")

    def update_group_names_by_label(self, label):
        for i in range(3):
            if self.groups_layout.itemAt(i, QFormLayout.ItemRole.LabelRole).widget() == label:
                self.apps_tab.right_tabs.setTabText(i, label.text().replace(" -", ""))
                break

class TrayApp(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon("icon.ico"))
        
        self.menu = QMenu()
        self.settings_action = self.menu.addAction("Settings")
        self.exit_action = self.menu.addAction("Exit")
        
        self.settings_action.triggered.connect(self.show_settings)
        self.exit_action.triggered.connect(self.on_exit)
        
        self.setContextMenu(self.menu)
        self.settings_window = None

    def show_settings(self):
        if not self.settings_window:
            self.settings_window = SettingsWindow()
        self.settings_window.show()

    def on_exit(self):
        if self.settings_window:
            self.settings_window.save_current_settings()
        QApplication.instance().quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    style = load_stylesheet()
    if style:
        app.setStyleSheet(style)
    else:
        print("Using default styles")
    
    main_window = QMainWindow()
    main_window.hide()
    
    tray = TrayApp(main_window)
    tray.show()
    
    app.aboutToQuit.connect(lambda: tray.settings_window.save_current_settings() if tray.settings_window else None)
    
    sys.exit(app.exec())