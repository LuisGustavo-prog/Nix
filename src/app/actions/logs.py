import threading
import subprocess
import uvicorn
import win32com.client
from app.actions.apps import resolve_app_path

_SERVER_STARTED = False
_LOG_PORT = 8000
_LOG_URL = f"http://localhost:{_LOG_PORT}"

def _resolve_shortcut_target(lnk_path: str) -> str:
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(lnk_path)
    return shortcut.Targetpath

def _start_server():
    uvicorn.run("app.web.log_server:app", host="127.0.0.1", port=_LOG_PORT, log_level="error")

def show_logs_dashboard() -> str:
    global _SERVER_STARTED

    if not _SERVER_STARTED:
        thread = threading.Thread(target=_start_server, daemon=True)
        thread.start()
        _SERVER_STARTED = True

    opera_path = resolve_app_path("opera")

    if opera_path:
        if opera_path.lower().endswith(".lnk"):
            opera_path = _resolve_shortcut_target(opera_path)
        try:
            subprocess.Popen([opera_path, _LOG_URL])
            return "Abrindo o painel de logs no Opera."
        except Exception:
            pass

    import webbrowser
    webbrowser.open(_LOG_URL)
    return "Abrindo o painel de logs no navegador."
