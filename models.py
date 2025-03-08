import json
from pathlib import Path

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

if __name__ == "__main__":
    # Тестовое сохранение настроек
    gm = GroupManager()
    gm.initialize(SettingsManager.default_settings())
    SettingsManager.save_settings(gm, {"Vol+": "Num+", "Vol-": "Num-", "Mute": "Num*"})