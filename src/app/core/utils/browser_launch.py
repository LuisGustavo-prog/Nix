import subprocess
import webbrowser
import win32com.client
from app.actions.apps import resolve_app_path

def resolve_shortcut_target(lnk_path: str) -> str:
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(lnk_path)
    return shortcut.Targetpath

def resolve_opera_executable() -> str | None:
    opera_path = resolve_app_path("opera")
    if opera_path is None:
        return None

    if opera_path.lower().endswith(".lnk"):
        opera_path = resolve_shortcut_target(opera_path)

    return opera_path

def open_url_in_opera(url: str) -> bool:
    opera_path = resolve_opera_executable()
    if opera_path is None:
        return False

    try:
        subprocess.Popen([opera_path, url])
        return True
    except Exception:
        return False

def open_url_with_fallback(url: str) -> bool:
    if open_url_in_opera(url):
        return True

    webbrowser.open(url)
    return False
