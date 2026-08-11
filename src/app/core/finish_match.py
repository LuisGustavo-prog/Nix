import re
from difflib import get_close_matches

_FINISH_WORD_VARIANTS = ("finalizar", "finaliza", "termina", "terminar", "conclui", "concluir", "encerra", "encerrar")
_COMMAND_WORD_VARIANTS = ("comando", "comandos")
_FINISH_CUTOFF = 0.72
_COMMAND_CUTOFF = 0.75

_TRIGGER_PATTERN = re.compile(
    r"\b(?:finaliza(?:r)?|termina(?:r)?|conclui(?:r)?|encerra(?:r)?)\s+(?:o\s+)?comandos?\b",
    re.IGNORECASE,
)
_TRAILING_TRIGGER_PATTERN = re.compile(
    r"\s*\b(?:finaliza(?:r)?|termina(?:r)?|conclui(?:r)?|encerra(?:r)?)\s+(?:o\s+)?comandos?\b\.?\s*$",
    re.IGNORECASE,
)

def is_finish_command(text: str) -> bool:
    text = text.lower()

    if _TRIGGER_PATTERN.search(text):
        return True

    words = [w.strip(",.!?") for w in text.split()]

    has_finish_word = any(
        get_close_matches(word, _FINISH_WORD_VARIANTS, n=1, cutoff=_FINISH_CUTOFF)
        for word in words
    )
    if not has_finish_word:
        return False

    has_command_word = any(
        get_close_matches(word, _COMMAND_WORD_VARIANTS, n=1, cutoff=_COMMAND_CUTOFF)
        for word in words
    )
    return has_command_word

def strip_trailing_finish_phrase(text: str) -> str:
    return _TRAILING_TRIGGER_PATTERN.sub("", text).strip()
