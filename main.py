import sys
import json
import subprocess
import ctypes
from pathlib import Path
from typing import List

from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QPushButton, QTabWidget, QListWidgetItem, QMessageBox
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QMetaObject, Q_ARG
from PyQt5.QtGui import QIcon

from pynput import keyboard

# Запрос прав администратора
if not ctypes.windll.shell32.IsUserAnAdmin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
    sys.exit()

class HotkeyHandler(QObject):
    action_signal = pyqtSignal(str, int)

class GroupListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)

    def dropEvent(self, event):
        source = event.source()
        if source:
            for item in source.selectedItems():
                new_item = QListWidgetItem(item.text())
                new_item.setData(Qt.UserRole, item.data(Qt.UserRole))
                self.addItem(new_item)
            event.accept()

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Настройки')
        self.setStyleSheet("background-color: #2E2E2E; color: #FFFFFF;")  # Тёмная тема
        self.layout = QHBoxLayout(self)  # Изменено на горизонтальный макет

        self.apps_list = QListWidget()
        self.apps_list.setDragEnabled(True)
        self.apps_list.setDragDropMode(QListWidget.DragOnly)
        self.apps_list.setFixedHeight(100)  # Ограничение высоты списка
        self.apps_list.setFixedWidth(100)  # Ограничение высоты списка
        self.groups_tabs = QTabWidget()
        self.groups_tabs.setFixedHeight(100)  # Ограничение высоты списка
        self.groups_tabs.setFixedWidth(200)  # Ограничение высоты списка
        self.refresh_button = QPushButton('Обновить')
        self.save_button = QPushButton('Сохранить')
        self.delete_button = QPushButton('Удалить')
        buttons_layout = QVBoxLayout()
        buttons_layout.addWidget(self.refresh_button)
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.delete_button)

        self.groups = [GroupListWidget() for _ in range(3)]
        # Установка жилья в виджеты
        self.groups_tabs.addTab(self.groups[0], 'Игры')
        self.groups_tabs.addTab(self.groups[1], 'Музыка')
        self.groups_tabs.addTab(self.groups[2], 'Голос')

        self.layout.addWidget(self.apps_list)
        self.layout.addLayout(buttons_layout)
        self.layout.addWidget(self.groups_tabs)

        # Соединение кнопок с функциями
        self.refresh_button.clicked.connect(self.refresh_apps)
        self.save_button.clicked.connect(self.save_groups)
        self.delete_button.clicked.connect(self.delete_selected)

        self.load_groups()

    def refresh_apps(self):
        json_path = Path('test.json')
        try:
            if json_path.exists():
                json_path.unlink()

            subprocess.run(
                ['SoundVolumeView.exe', '/sjson', str(json_path), '/encoding', 'utf16'],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5
            )

            with open(json_path, 'rb') as f:
                content = f.read().decode('utf-16-le').lstrip('\ufeff')
                data = json.loads(content)

            current_pids = {self.apps_list.item(i).data(Qt.UserRole) 
                          for i in range(self.apps_list.count())}
            
            new_items = []
            for item in data:
                if (isinstance(item, dict) and 
                    item.get('Type') == 'Application' and 
                    item.get('Direction') == 'Render'):
                    pid = item.get('Process ID')
                    name = item.get('Name', 'Unknown')
                    if pid and pid not in current_pids:
                        new_items.append((name, pid))

            for name, pid in new_items:
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, pid)
                self.apps_list.addItem(item)

        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка обновления: {str(e)}')

    def save_groups(self):
        groups = {
            f'group{i+1}': [
                {'name': group.item(j).text(), 'pid': group.item(j).data(Qt.UserRole)}
                for j in range(group.count())
            ] for i, group in enumerate(self.groups)
        }
        try:
            with open('groups.json', 'w', encoding='utf-8') as f:
                json.dump(groups, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка сохранения: {e}')

    def load_groups(self):
        try:
            with open('groups.json', 'r', encoding='utf-8') as f:
                groups = json.load(f)
        except FileNotFoundError:
            return

        for i in range(3):
            self.groups[i].clear()
            for item in groups.get(f'group{i+1}', []):
                list_item = QListWidgetItem(item['name'])
                list_item.setData(Qt.UserRole, item['pid'])
                self.groups[i].addItem(list_item)

    def delete_selected(self):
        current_tab = self.groups_tabs.currentWidget()
        for item in current_tab.selectedItems():
            current_tab.takeItem(current_tab.row(item))

    def get_group_pids(self, group_num: int) -> List[int]:
        if 0 <= group_num < 3:
            return [self.groups[group_num].item(i).data(Qt.UserRole)
                   for i in range(self.groups[group_num].count())]
        return []

class TrayApp(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon('icon.ico'))
        self.settings_window = SettingsWindow()
        menu = QMenu()
        settings_action = menu.addAction('Настройки')
        settings_action.triggered.connect(self.show_settings)
        exit_action = menu.addAction('Выход')
        exit_action.triggered.connect(QApplication.instance().quit)
        self.setContextMenu(menu)

    def show_settings(self):
        self.settings_window.show()

class HotkeyManager:
    def __init__(self, handler):
        self.handler = handler
        self.pressed = set()
        self.num_keys = {97: 1, 98: 2, 99: 3}  # Клавиши Numpad 1-3
        self.action_keys = {
            107: 'increase',  # Numpad +
            109: 'decrease',  # Numpad -
            106: 'switch'     # Numpad *
        }
        self.listener = None

    def start(self):
        def on_press(key):
            try:
                vk = key.vk
                if vk in self.num_keys or vk in self.action_keys:
                    self.pressed.add(vk)
                    self.check_combinations()
            except AttributeError:
                pass

        def on_release(key):
            try:
                vk = key.vk
                if vk in self.pressed:
                    self.pressed.remove(vk)
            except (AttributeError, KeyError):
                pass

        self.listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release,
            win32_event_filter=lambda msg, data: True
        )
        self.listener.start()

    def check_combinations(self):
        active_num = None
        active_action = None

        # Определяем нажатую цифровую клавишу
        for vk in self.pressed:
            if vk in self.num_keys:
                active_num = self.num_keys[vk]
                break

        # Определяем действие
        for vk in self.pressed:
            if vk in self.action_keys:
                active_action = self.action_keys[vk]
                break

        if active_num and active_action:
            self.handler(active_action, active_num)

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Используем стиль Fusion
    app.setQuitOnLastWindowClosed(False)

    # Установка темного стиля для приложения
    app.setStyleSheet("QMainWindow {background-color: #2E2E2E;} "
                      "QWidget {background-color: #2E2E2E; color: #FFFFFF;} "
                      "QPushButton {background-color: #505050; color: #FFFFFF;} "
                      "QListWidget {background-color: #505050; color: #FFFFFF;}")

    tray = TrayApp()
    tray.show()

    handler = HotkeyHandler()

    def handle_action(action: str, group: int):
        pids = tray.settings_window.get_group_pids(group - 1)
        if not pids:
            return

        for pid in pids:
            try:
                if action == 'switch':
                    subprocess.run(
                        ['SoundVolumeView.exe', '/Switch', str(pid)],
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    step = 10
                    volume_change = step if action == 'increase' else -step
                    subprocess.run(
                        ['SoundVolumeView.exe', '/ChangeVolume', 
                         str(pid), str(volume_change)],
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
            except Exception as e:
                print(f"Ошибка обработки PID {pid}: {str(e)}")

    handler.action_signal.connect(handle_action)
    hotkey_manager = HotkeyManager(lambda a, g: handler.action_signal.emit(a, g))
    hotkey_manager.start()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
