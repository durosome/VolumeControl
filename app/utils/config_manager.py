import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class SettingsManager:  # <-- Класс должен называться именно так!
    def __init__(self, file_path="config.json"):
        self.file_path = Path(file_path)
        self.config = self._load_config()
        
    def _load_config(self):
        default_config = {
            "hotkeys": {
                "volume_up": "ctrl+shift+up",
                "volume_down": "ctrl+shift+down"
            }
        }
        
        try:
            if not self.file_path.exists() or self.file_path.stat().st_size == 0:
                logger.warning("Конфиг не найден. Создаю новый")
                self._save_default(default_config)
                return default_config
                
            with open(self.file_path, 'r') as f:
                return json.load(f)
                
        except json.JSONDecodeError:
            logger.error("Ошибка в конфиге. Восстанавливаю дефолт")
            self._save_default(default_config)
            return default_config
            
    def _save_default(self, config):
        with open(self.file_path, 'w') as f:
            json.dump(config, f, indent=4)
            
    def save(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.config, f, indent=4)