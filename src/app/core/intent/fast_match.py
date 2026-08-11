import re

_YOUTUBE_PATTERN = re.compile(
    r"\b(?:toca|tocar|coloca|colocar|abre|abrir|pesquisa|pesquisar|busca|buscar)\s+"
    r"(?:a\s+m[uú]sica\s+|o\s+v[íi]deo\s+(?:de|da|do)\s+|o\s+v[íi]deo\s+)?"
    r"(.+?)\s+no\s+youtube\b",
    re.IGNORECASE,
)
_BROWSER_PATTERN = re.compile(
    r"\b(?:pesquisa|pesquisar|busca|buscar)\s+(?:sobre\s+|por\s+)?"
    r"(.+?)\s+no\s+(?:navegador|opera)\b",
    re.IGNORECASE,
)
_OPEN_APP_PATTERN = re.compile(r"\b(?:abre|abrir|abra)\s+(?:(?:o|a|ou)\s+)?(.+)", re.IGNORECASE)
_CLOSE_APP_PATTERN = re.compile(r"\b(?:fecha|fechar|feche)\s+(?:(?:o|a|ou)\s+)?(.+)", re.IGNORECASE)
_TRAILING_FILLER_WORDS = ("por favor", "pra mim", "para mim")
_FIXED_RESTART_PHRASES = {"reiniciar nix", "iniciar nix", "re-iniciar mix", "reiniciar", "iniciar"}
_FIXED_SHUTDOWN_PHRASE = "encerrar"

def _strip_trailing_filler(value: str) -> str:
    cleaned = value.strip(" .,!?")
    for filler in _TRAILING_FILLER_WORDS:
        if cleaned.lower().endswith(filler):
            cleaned = cleaned[: -len(filler)].strip(" .,!?")
    return cleaned

def _normalize_for_fixed_match(text: str) -> str:
    cleaned = _strip_trailing_filler(text).strip().lower()
    cleaned = cleaned.replace("-", "").replace("_", "")
    cleaned = re.sub(r"[.,!?]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def is_restart_command(text: str) -> bool:
    return _normalize_for_fixed_match(text) in _FIXED_RESTART_PHRASES

def is_shutdown_command(text: str) -> bool:
    return _normalize_for_fixed_match(text) == _FIXED_SHUTDOWN_PHRASE

def match_simple_command(user_text: str):
    text = user_text.lower()
    has_digit = any(char.isdigit() for char in text)

    if re.search(r"\b(desmuta|desmute|desmutar)\b", text):
        return "mute", {"should_mute": False}
    if re.search(r"\b(muta|mute|mutar)\b", text):
        return "mute", {"should_mute": True}

    if any(word in text for word in ["volume", "som", "áudio", "audio"]):
        if has_digit:
            percentage_match = re.search(r"(\d{1,3})\s*(%|por cento)?", text)
            if percentage_match:
                percentage = max(0, min(100, int(percentage_match.group(1))))
                return "set_volume", {"percentage": percentage}
        else:
            if re.search(r"\b(aument\w*|sobe|sobre)\b", text):
                return "adjust_volume", {"direction": "increase"}
            if re.search(r"\b(abaix\w*|diminu\w*|baixa)\b", text):
                return "adjust_volume", {"direction": "decrease"}

    if "luz noturna" in text or "night light" in text:
        return "toggle_night_light", {}

    if re.search(r"\b(pausa\w*|pause|despausa\w*|despause|continu\w*|retom\w*)\b", text) or "dá play" in text or "da play" in text:
        return "control_media", {"action": "play_pause"}
    if re.search(r"\b(pr[oó]xima|pula|pular)\b", text):
        return "control_media", {"action": "next_track"}
    if re.search(r"\b(anterior|volt[ae]|voltar)\b", text):
        return "control_media", {"action": "previous_track"}
    if re.search(r"\bvoc[eê]\s+a\s+m[uú]sica\b", text):
        return "control_media", {"action": "previous_track"}
    if re.search(r"\b(para|pare|parar)\s+a\s+(m[uú]sica)\b", text):
        return "control_media", {"action": "stop"}

    if any(phrase in text for phrase in ["modo de escrita", "modo de digitação", "modo de ditado"]) or re.search(r"\b(escreve|escrever|digita|ditar)\b", text):
        return "dictate_text", {}

    if any(phrase in text for phrase in ["bora trabalhar", "vamos trabalhar", "hora de trabalhar"]):
        return "start_work_mode", {}

    if any(phrase in text for phrase in ["mostrar log", "mostrar logs", "exibir log", "exibir logs", "abrir log", "abrir logs", "painel de logs", "central de logs", "painel de informações"]):
        return "show_logs_dashboard", {}

    if any(phrase in text for phrase in ["quero desenhar", "vou desenhar", "bora desenhar"]):
        return "open_app", {"app_name": "paint"}

    match = _YOUTUBE_PATTERN.search(text)
    if match:
        query = _strip_trailing_filler(match.group(1))
        if query:
            return "search_video_on_youtube", {"query": query}

    match = _BROWSER_PATTERN.search(text)
    if match:
        query = _strip_trailing_filler(match.group(1))
        if query:
            return "search_in_browser", {"query": query}

    match = _CLOSE_APP_PATTERN.search(text)
    if match:
        app_name = _strip_trailing_filler(match.group(1))
        if app_name:
            return "close_app", {"app_name": app_name}

    match = _OPEN_APP_PATTERN.search(text)
    if match:
        app_name = _strip_trailing_filler(match.group(1))
        if app_name:
            return "open_app", {"app_name": app_name}

    return None
