import sys
import comtypes
import os
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from pycaw.pycaw import AudioUtilities

# Инициализация COM для PyCaw
comtypes.CoInitialize()

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

class EditableTabBar(QTabBar):
    edit_requested = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor = QLineEdit(self)
        self.editor.setWindowFlags(Qt.WindowType.Popup)
        self.editor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
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
        self.editor.resize(rect.width(), rect.height())
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
        self.editor = QLineEdit(self)
        self.editor.setWindowFlags(Qt.WindowType.Popup)
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
        self.editor.resize(self.size())
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
        
        self.left_panel = QListWidget()
        self.left_panel.setDragEnabled(True)
        self.left_panel.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
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
            tab.list = QListWidget()
            tab.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            tab.list.customContextMenuRequested.connect(self.show_context_menu)
            tab.list.setAcceptDrops(True)
            tab.list.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
            tab.list.keyPressEvent = self.list_key_press_event
            tab.layout = QVBoxLayout()
            tab.layout.addWidget(tab.list)
            tab.setLayout(tab.layout)
            self.right_tabs.addTab(tab, f"Category {i+1}")
        
        layout.addLayout(left_layout, 40)
        layout.addWidget(self.right_tabs, 60)
        self.setLayout(layout)

    def list_key_press_event(self, event):
        if event.key() == Qt.Key.Key_Delete:
            list_widget = self.sender()
            if list_widget and isinstance(list_widget, QListWidget):
                current_item = list_widget.currentItem()
                if current_item:
                    row = list_widget.row(current_item)
                    list_widget.takeItem(row)
        else:
            super(QListWidget, self.sender()).keyPressEvent(event)

    def show_context_menu(self, pos):
        list_widget = self.sender()
        item = list_widget.itemAt(pos)
        if item:
            menu = QMenu()
            delete_action = menu.addAction("Delete")
            action = menu.exec(list_widget.mapToGlobal(pos))
            if action == delete_action:
                row = list_widget.row(item)
                list_widget.takeItem(row)

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
        current_tab = self.right_tabs.currentWidget()
        if current_tab:
            current_item = current_tab.list.currentItem()
            if current_item:
                row = current_tab.list.row(current_item)
                current_tab.list.takeItem(row)

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setMinimumSize(550, 200)
        self.resize(550, 200)
        self.init_ui()

    def init_ui(self):
        tab_widget = QTabWidget()
        
        hotkeys_tab = QWidget()
        main_hotkeys_layout = QHBoxLayout()
        
        self.groups_layout = QFormLayout()
        self.group_edits = []
        for i in range(3):
            edit = HotkeyLineEdit()
            label = EditableLabel(f"Category {i+1} -")
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

    def update_group_names(self):
        for i in range(3):
            label = self.groups_layout.itemAt(i, QFormLayout.ItemRole.LabelRole).widget()
            tab_name = self.apps_tab.right_tabs.tabText(i)
            label.setText(f"{tab_name} -")

    def update_group_names_by_label(self, label):
        index = None
        for i in range(3):
            if self.groups_layout.itemAt(i, QFormLayout.ItemRole.LabelRole).widget() == label:
                index = i
                break
        if index is not None:
            new_name = label.text().replace(" -", "")
            self.apps_tab.right_tabs.setTabText(index, new_name)

class TrayApp(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon("icon.ico"))
        
        self.menu = QMenu()
        self.settings_action = self.menu.addAction("Settings")
        self.exit_action = self.menu.addAction("Exit")
        
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
    style = load_stylesheet()
    if style:
        app.setStyleSheet(style)
    else:
        print("Using default styles")
    
    main_window = QMainWindow()
    main_window.hide()
    
    tray = TrayApp(main_window)
    tray.show()
    
    sys.exit(app.exec())