import time
import pyautogui
from app.core.stt import listen

_TYPING_INTERVAL = 0.02
_DICTATION_DURATION = 8

def dictate_text() -> str:
    dictated_text = listen(duration=_DICTATION_DURATION)

    if not dictated_text:
        return "Não consegui captar nada para ditar."

    time.sleep(0.3)
    pyautogui.write(dictated_text, interval=_TYPING_INTERVAL)

    return "Texto ditado."
