import subprocess
from urllib.parse import quote_plus
import win32com.client
from app.actions.apps import resolve_app_path

_SEARCH_URL_TEMPLATE = "https://www.google.com/search?q={query}"

def _resolve_shortcut_target(lnk_path: str) -> str:
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(lnk_path)
    return shortcut.Targetpath

def search_in_browser(query: str) -> str:
    opera_path = resolve_app_path("opera")

    if opera_path is None:
        return "Não consegui encontrar o Opera instalado."

    if opera_path.lower().endswith(".lnk"):
        opera_path = _resolve_shortcut_target(opera_path)

    search_url = _SEARCH_URL_TEMPLATE.format(query=quote_plus(query))

    try:
        subprocess.Popen([opera_path, search_url])
    except Exception:
        return f"Não consegui abrir o Opera para buscar por {query}."

    return f"Buscando por {query} no Opera."
