import time
import re
import pyautogui
import pyperclip
from app.core.stt import listen_with_cancel_check
from app.core.logging_config import get_logger
from app.prompts.content import DICTATION_PUNCTUATION_MAP

log = get_logger("dictation")

_DEFAULT_DICTATION_DURATION = 10

def _format_punctuation(text: str) -> str:
    for pattern, replacement in DICTATION_PUNCTUATION_MAP.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = re.sub(r"\s+([.,;?!])", r"\1", text)

    return text.strip()

def dictate_text(duration: int = _DEFAULT_DICTATION_DURATION) -> str:
    dictated_text, was_cancelled = listen_with_cancel_check(
        duration=duration,
        use_command_context=False,
    )

    if was_cancelled:
        return "Ditado cancelado."

    if not dictated_text:
        return "Não consegui captar nada para ditar."

    formatted_text = _format_punctuation(dictated_text)
    if formatted_text:
        formatted_text = formatted_text[0].upper() + formatted_text[1:]

    previous_clipboard = pyperclip.paste()

    try:
        pyperclip.copy(formatted_text)
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "v")
    except Exception:
        log.exception("Erro ao colar o texto ditado")
        return "Houve um erro ao colar o texto ditado."
    finally:
        time.sleep(0.4)
        pyperclip.copy(previous_clipboard)

    return "Texto ditado com sucesso."
