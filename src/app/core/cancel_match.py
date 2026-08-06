import re
from difflib import get_close_matches

_CANCEL_WORD_VARIANTS = ("cancelar", "cancela")
_COMMAND_WORD_VARIANTS = ("comando", "comandos")
_CANCEL_CUTOFF = 0.72
_COMMAND_CUTOFF = 0.75

_EXACT_PATTERN = re.compile(r"\bcancela(?:r)?\s+(?:o\s+)?comandos?\b", re.IGNORECASE)

def is_cancel_command(text: str) -> bool:
    text = text.lower()

    if _EXACT_PATTERN.search(text):
        return True

    words = [w.strip(",.!?") for w in text.split()]

    has_cancel_word = any(
        get_close_matches(word, _CANCEL_WORD_VARIANTS, n=1, cutoff=_CANCEL_CUTOFF)
        for word in words
    )
    if not has_cancel_word:
        return False

    has_command_word = any(
        get_close_matches(word, _COMMAND_WORD_VARIANTS, n=1, cutoff=_COMMAND_CUTOFF)
        for word in words
    )
    return has_command_word
