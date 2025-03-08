import sys
import comtypes
import json
from pathlib import Path
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from pycaw.pycaw import AudioUtilities

comtypes.CoInitialize()

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
            
        if not self.groups:
            self.groups = [
                Group("Games", "Num1"),
                Group("Music", "Num2"),
                Group("Voice", "Num3")
            ]
            
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
                "Vol+": "Num+",
                "Vol-": "Num-",
                "Mute": "Num*"
            }
        }

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

class AudioSessionWidget(QListWidgetItem):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.process_name = self.get_clean_process_name()
        self.setText(self.process_name)

    def get_clean_process_name(self):
        try:
            if self.session.Process:
                name = self.session.Process.name()
                return name.strip() if name else "System"
            return "System"
        except:
            return "Unknown"

class CustomListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected_item()
        else:
            super().keyPressEvent(event)

    def delete_selected_item(self):
        if current_item := self.currentItem():
            self.takeItem(self.row(current_item))

    def startDrag(self, supportedActions):
        drag = QDrag(self)
        mimeData = self.model().mimeData(self.selectedIndexes())
        drag.setMimeData(mimeData)
        drag.exec(Qt.DropAction.MoveAction)

    def dropEvent(self, event):
        if event.source() == self:
            return super().dropEvent(event)
            
        if event.source().currentItem():
            item_text = event.source().currentItem().text().strip()
            if item_text:
                self.addItem(QListWidgetItem(item_text))
        event.accept()

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

class EditableLabel(QLabel):
    editingFinished = pyqtSignal()
    
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
        self.editingFinished.emit()

class AppsTab(QWidget):
    def __init__(self, group_manager):
        super().__init__()
        self.group_manager = group_manager
        self.sessions = []
        self.init_ui()
        self.init_audio()
        self.start_updater()

    def init_ui(self):
        layout = QHBoxLayout()
        
        self.left_panel = CustomListWidget()
        self.left_panel.setDragEnabled(True)
        self.left_panel.setAcceptDrops(False)
        
        btn_panel = QHBoxLayout()
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_item)
        btn_panel.addWidget(self.delete_btn)
        
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.left_panel)
        left_layout.addLayout(btn_panel)
        
        self.right_tabs = QTabWidget()
        self.right_tabs.setTabPosition(QTabWidget.TabPosition.South)
        self.right_tabs.setTabBar(EditableTabBar())
        self.right_tabs.tabBar().edit_requested.connect(self.handle_tab_edited)
        
        for group in self.group_manager.groups:
            self.add_group_tab(group)
        
        layout.addLayout(left_layout, 40)
        layout.addWidget(self.right_tabs, 60)
        self.setLayout(layout)

    def handle_tab_edited(self, index):
        new_name = self.right_tabs.tabText(index)
        self.group_manager.groups[index].name = new_name

    def add_group_tab(self, group):
        tab = QWidget()
        tab.list = CustomListWidget()
        tab.list.setAcceptDrops(True)
        tab.list.setDragEnabled(False)
        tab.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tab.list.customContextMenuRequested.connect(self.show_context_menu)
        
        tab.list.model().rowsInserted.connect(
            lambda: self.update_group_apps(group, tab.list))
        tab.list.model().rowsRemoved.connect(
            lambda: self.update_group_apps(group, tab.list))
        
        for app in group.apps:
            if app.strip():
                tab.list.addItem(QListWidgetItem(app.strip()))
        
        tab.layout = QVBoxLayout()
        tab.layout.addWidget(tab.list)
        tab.setLayout(tab.layout)
        self.right_tabs.addTab(tab, group.name)

    def update_group_apps(self, group, list_widget):
        group.apps = [list_widget.item(i).text().strip() 
                     for i in range(list_widget.count())
                     if list_widget.item(i) and list_widget.item(i).text().strip()]

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

class SettingsWindow(QWidget):
    def __init__(self, group_manager, volume_controls):
        super().__init__()
        self.group_manager = group_manager
        self.volume_controls = volume_controls
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 400)
        self.init_ui()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

    def init_ui(self):
        tab_widget = QTabWidget()
        
        hotkeys_tab = QWidget()
        main_hotkeys_layout = QHBoxLayout()
        
        self.groups_layout = QFormLayout()
        self.group_edits = []
        self.group_labels = []
        
        for group in self.group_manager.groups:
            edit = HotkeyLineEdit()
            edit.setText(group.hotkey)
            edit.textChanged.connect(lambda text, g=group: setattr(g, 'hotkey', text))
            
            label = EditableLabel(f"{group.name} -")
            label.setText(f"{group.name} -")
            group.add_observer(lambda g, lbl=label: lbl.setText(f"{g.name} -"))
            label.editingFinished.connect(lambda l=label: self.update_group_name(l))
            
            self.groups_layout.addRow(label, edit)
            self.group_edits.append(edit)
            self.group_labels.append(label)
        
        volume_layout = QFormLayout()
        self.volume_edits = {}
        for control in ["Vol+", "Vol-", "Mute"]:
            edit = HotkeyLineEdit()
            edit.setText(self.volume_controls.get(control, ""))
            edit.textChanged.connect(lambda text, c=control: self.update_volume_control(c, text))
            volume_layout.addRow(QLabel(f"{control} -"), edit)
            self.volume_edits[control] = edit
        
        main_hotkeys_layout.addLayout(self.groups_layout, 60)
        main_hotkeys_layout.addLayout(volume_layout, 40)
        hotkeys_tab.setLayout(main_hotkeys_layout)
        
        self.apps_tab = AppsTab(self.group_manager)
        
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

    def update_group_name(self, label):
        for i, lbl in enumerate(self.group_labels):
            if lbl == label:
                new_name = label.text().replace(" -", "")
                self.group_manager.groups[i].name = new_name
                self.apps_tab.right_tabs.setTabText(i, new_name)
                break

    def update_volume_control(self, control, value):
        self.volume_controls[control] = value

    def closeEvent(self, event):
        SettingsManager.save_settings(self.group_manager, self.volume_controls)
        self.hide()
        event.ignore()

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
        if self.settings_window:
            self.settings_window.close()
        QApplication.instance().quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    try:
        with open('dark_theme.qss', 'r') as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print(f"Error loading styles: {e}")
    
    tray = TrayApp()
    tray.show()
    
    app.exec()