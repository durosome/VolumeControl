from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from widgets import *
from models import GroupManager
from models import SettingsManager

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
    def closeEvent(self, event):
        # Сохраняем настройки при закрытии окна
        success = SettingsManager.save_settings(
            self.group_manager, 
            self.volume_controls
        )
        if not success:
            QMessageBox.warning(
                self,
                "Ошибка сохранения",
                "Не удалось сохранить настройки!",
                QMessageBox.StandardButton.Ok
            )
         # Закрываем окно корректно
        self.hide()
        event.accept()  # Изменено с ignore() на accept()

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