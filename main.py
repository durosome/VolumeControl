import sys
import comtypes
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from pycaw.pycaw import AudioUtilities

# Инициализация COM для PyCaw
comtypes.CoInitialize()

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
        
        # Left panel
        self.left_panel = QListWidget()
        self.left_panel.setDragEnabled(True)
        self.left_panel.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        # Buttons
        btn_panel = QHBoxLayout()
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_item)
        btn_panel.addWidget(self.delete_btn)
        
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.left_panel)
        left_layout.addLayout(btn_panel)
        
        # Right tabs
        self.right_tabs = QTabWidget()
        self.right_tabs.setTabPosition(QTabWidget.TabPosition.South)
        
        for i in range(3):
            tab = QWidget()
            tab.list = QListWidget()
            tab.list.setAcceptDrops(True)
            tab.list.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
            tab.layout = QVBoxLayout()
            tab.layout.addWidget(tab.list)
            tab.setLayout(tab.layout)
            self.right_tabs.addTab(tab, f"Category {i+1}")
        
        self.right_tabs.tabBar().installEventFilter(self)
        
        layout.addLayout(left_layout, 40)
        layout.addWidget(self.right_tabs, 60)
        self.setLayout(layout)

    def eventFilter(self, source, event):
        if (event.type() == QEvent.Type.MouseButtonDblClick and 
            source is self.right_tabs.tabBar()):
            index = self.right_tabs.tabBar().tabAt(event.pos())
            if index >= 0:
                self.rename_tab(index)
                return True
        return super().eventFilter(source, event)

    def rename_tab(self, index):
        old_name = self.right_tabs.tabText(index)
        new_name, ok = QInputDialog.getText(
            self, "Rename Category", "New name:", text=old_name
        )
        if ok and new_name:
            self.right_tabs.setTabText(index, new_name)
            self.tab_renamed.emit(index, new_name)

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
        
        # Hotkeys Tab
        hotkeys_tab = QWidget()
        main_hotkeys_layout = QHBoxLayout()
        
        # Groups
        self.groups_layout = QFormLayout()
        self.group_edits = []
        for i in range(3):
            edit = HotkeyLineEdit()
            label = QLabel(f"Category {i+1} -")
            self.groups_layout.addRow(label, edit)
            self.group_edits.append(edit)
        
        # Volume controls
        volume_layout = QFormLayout()
        self.volume_controls = {}
        for control in ["Vol+", "Vol-", "Mute"]:
            edit = HotkeyLineEdit()
            volume_layout.addRow(QLabel(f"{control} -"), edit)
            self.volume_controls[control] = edit
        
        main_hotkeys_layout.addLayout(self.groups_layout, 60)
        main_hotkeys_layout.addLayout(volume_layout, 40)
        hotkeys_tab.setLayout(main_hotkeys_layout)
        
        # Apps Tab
        self.apps_tab = AppsTab()
        self.apps_tab.tab_renamed.connect(self.update_group_names)
        
        # Initial update
        QTimer.singleShot(0, self.update_group_names)
        
        # Etc Tab
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

    def update_group_names(self, index=None, name=None):
        for i in range(3):
            label = self.groups_layout.itemAt(i, QFormLayout.ItemRole.LabelRole).widget()
            tab_name = self.apps_tab.right_tabs.tabText(i)
            label.setText(f"{tab_name} -")

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
    app.setStyleSheet(DARK_STYLE)
    
    main_window = QMainWindow()
    main_window.hide()
    
    tray = TrayApp(main_window)
    tray.show()
    
    sys.exit(app.exec())