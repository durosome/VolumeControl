import json
from pathlib import Path

class SettingsManager:
    SETTINGS_FILE = "app_settings.json"
    
    @classmethod
    def load_settings(cls):
        try:
            if Path(cls.SETTINGS_FILE).exists():
                with open(cls.SETTINGS_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
        return cls.default_settings()

    @classmethod
    def save_settings(cls, data):
        try:
            with open(cls.SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
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

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = SettingsManager.load_settings()
        # ... остальной код инициализации ...

    def init_ui(self):
        # ... существующий код ...
        self.load_current_settings()

    def load_current_settings(self):
        # Загрузка названий групп
        for i in range(3):
            self.apps_tab.right_tabs.setTabText(i, self.settings["groups"][i]["name"])
            
            # Загрузка приложений в группы
            tab_widget = self.apps_tab.right_tabs.widget(i)
            tab_widget.list.clear()
            for app in self.settings["groups"][i]["apps"]:
                tab_widget.list.addItem(QListWidgetItem(app))

        # Загрузка горячих клавиш
        for i, group in enumerate(self.settings["groups"]):
            self.group_edits[i].setText(group["hotkey"])
            
        for control in ["Vol+", "Vol-", "Mute"]:
            self.volume_controls[control].setText(self.settings["volume_controls"][control])

    def save_current_settings(self):
        # Сохранение названий групп
        for i in range(3):
            self.settings["groups"][i]["name"] = self.apps_tab.right_tabs.tabText(i)
            
            # Сохранение приложений в группах
            tab_widget = self.apps_tab.right_tabs.widget(i)
            self.settings["groups"][i]["apps"] = [
                tab_widget.list.item(j).text() 
                for j in range(tab_widget.list.count())
            ]

        # Сохранение горячих клавиш
        for i in range(3):
            self.settings["groups"][i]["hotkey"] = self.group_edits[i].text()
            
        for control in ["Vol+", "Vol-", "Mute"]:
            self.settings["volume_controls"][control] = self.volume_controls[control].text()
            
        return SettingsManager.save_settings(self.settings)

class TrayApp(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)
        # ... существующий код ...
        self.aboutToQuit = self.save_before_exit

    def save_before_exit(self):
        if hasattr(self, 'settings_window') and self.settings_window:
            self.settings_window.save_current_settings()

class AppsTab(QWidget):
    # ... существующий код ...
    
    def add_application_to_group(self, app_name, group_index):
        tab_widget = self.right_tabs.widget(group_index)
        if not any(tab_widget.list.item(i).text() == app_name 
                 for i in range(tab_widget.list.count())):
            tab_widget.list.addItem(QListWidgetItem(app_name))

# В главный цикл добавьте обработку закрытия
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # ... существующий код ...
    
    # Обработка закрытия приложения
    app.aboutToQuit.connect(lambda: tray.settings_window.save_current_settings())
    
    sys.exit(app.exec())