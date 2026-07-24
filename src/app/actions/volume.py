from pycaw.pycaw import AudioUtilities

def _get_volume_interface():
    device = AudioUtilities.GetSpeakers()
    return device.EndpointVolume

def set_volume(percentage: int) -> str:
    percentage = max(0, min(100, percentage))
    volume = _get_volume_interface()
    volume.SetMasterVolumeLevelScalar(percentage / 100, None)
    return f"Volume ajustado para {percentage} por cento."

def increase_volume(step: int = 10) -> str:
    volume = _get_volume_interface()
    current = volume.GetMasterVolumeLevelScalar()
    new_level = min(1.0, current + (step / 100))
    volume.SetMasterVolumeLevelScalar(new_level, None)
    return f"Volume aumentado para {int(new_level * 100)} por cento."

def decrease_volume(step: int = 10) -> str:
    volume = _get_volume_interface()
    current = volume.GetMasterVolumeLevelScalar()
    new_level = max(0.0, current - (step / 100))
    volume.SetMasterVolumeLevelScalar(new_level, None)
    return f"Volume diminuído para {int(new_level * 100)} por cento."

def mute(should_mute: bool = True) -> str:
    volume = _get_volume_interface()
    volume.SetMute(1 if should_mute else 0, None)
    return "Áudio mutado." if should_mute else "Áudio desmutado."
