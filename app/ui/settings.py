from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSlider
from PyQt6.QtCore import Qt
from app.utils.logger import logger

class SettingsWindow(QWidget):
    def __init__(self, audio_controller):
        super().__init__()
        self.audio = audio_controller
        self._setup_ui()
        logger.info("Окно настроек инициализировано")

    def _setup_ui(self):
        self.setWindowTitle("Настройки Volume Control")
        self.setFixedSize(300, 100)
        
        layout = QVBoxLayout()
        
        # Слайдер громкости
        self.volume_label = QLabel("Громкость по умолчанию:")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.audio.volume.GetMasterVolumeLevelScalar() * 100))
        self.volume_slider.valueChanged.connect(self._update_volume)
        
        layout.addWidget(self.volume_label)
        layout.addWidget(self.volume_slider)
        self.setLayout(layout)

    def _update_volume(self, value):
        level = value / 100
        self.audio.set_volume(level)
        logger.debug(f"Установлена громкость: {value}%")
