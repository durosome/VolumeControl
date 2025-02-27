from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from app.utils.logger import logger

class AudioController:
    def __init__(self):
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, 0, None)
        self.volume = interface.QueryInterface(IAudioEndpointVolume)
        logger.info("Аудиоконтроллер инициализирован")

    def set_volume(self, level: float) -> None:
        self.volume.SetMasterVolumeLevelScalar(level, None)
        logger.info(f"Громкость: {level*100:.0f}%")

    def volume_up(self) -> None:
        current = self.volume.GetMasterVolumeLevelScalar()
        new_level = min(current + 0.1, 1.0)
        self.set_volume(new_level)

    def volume_down(self) -> None:
        current = self.volume.GetMasterVolumeLevelScalar()
        new_level = max(current - 0.1, 0.0)
        self.set_volume(new_level)