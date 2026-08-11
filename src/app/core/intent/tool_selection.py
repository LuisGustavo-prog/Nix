import re
from difflib import get_close_matches
from app.core.intent.tools import TOOL_SCHEMAS, TOOLS_BY_NAME
_CATEGORY_RULES = [
    (["abre", "abrir", "fecha", "fechar"], ["open_app", "close_app"]),
    (["volume", "som", "mudo", "muta", "desmuta", "áudio", "audio"], ["set_volume", "adjust_volume", "mute"]),
    (["luz noturna", "night light"], ["toggle_night_light"]),
    (
        ["pausa", "pause", "despausa", "próxima", "proxima", "volta", "volte", "anterior", "continua", "retoma", "play", "stop", "para a música", "para a musica", "pare a música", "pare a musica"],
        ["control_media"],
    ),
    (["youtube"], ["search_video_on_youtube", "control_media"]),
    (["navegador", "opera"], ["search_in_browser"]),
    (["modo de escrita", "ditado", "escreve", "escrever", "digita"], ["dictate_text"]),
    (["bora trabalhar", "vamos trabalhar", "hora de trabalhar"], ["start_work_mode"]),
    (
        ["mostrar log", "mostrar logs", "exibir log", "exibir logs", "abrir log", "abrir logs", "painel de logs", "central de logs", "painel de informações"],
        ["show_logs_dashboard"],
    ),
    (["desenhar", "desenho"], ["open_app"]),
]

_ACTION_VERBS = [
    "abre", "abrir", "abra", "fecha", "fechar", "feche",
    "toca", "tocar", "coloca", "colocar",
    "pesquisa", "pesquisar", "busca", "buscar",
]

_TRIGGER_VOCABULARY = sorted({
    word
    for keywords, _ in _CATEGORY_RULES
    for phrase in keywords
    for word in phrase.split()
} | set(_ACTION_VERBS))


def needs_correction(user_text: str, cutoff: float = 0.75) -> bool:
    words = re.findall(r"[a-zà-ÿ]+", user_text.lower())
    for word in words:
        if word in _TRIGGER_VOCABULARY:
            continue
        if get_close_matches(word, _TRIGGER_VOCABULARY, n=1, cutoff=cutoff):
            return True
    return False


def select_tools(user_text: str) -> list:
    text = user_text.lower()
    selected_names = set()

    for keywords, tool_names in _CATEGORY_RULES:
        if any(keyword in text for keyword in keywords):
            selected_names.update(tool_names)

    if not selected_names:
        return TOOL_SCHEMAS

    return [TOOLS_BY_NAME[name] for name in selected_names if name in TOOLS_BY_NAME]
