import threading

import uvicorn

from app.core.utils.browser_launch import open_url_with_fallback

_SERVER_STARTED = False
_LOG_PORT = 8000
_LOG_URL = f"http://localhost:{_LOG_PORT}"

def _start_server() -> None:
    uvicorn.run("app.web.log_server:app", host="127.0.0.1", port=_LOG_PORT, log_level="error")

def show_logs_dashboard() -> str:
    global _SERVER_STARTED

    if not _SERVER_STARTED:
        thread = threading.Thread(target=_start_server, daemon=True)
        thread.start()
        _SERVER_STARTED = True

    opened_in_opera = open_url_with_fallback(_LOG_URL)
    if opened_in_opera:
        return "Abrindo o painel de logs no Opera."
    return "Abrindo o painel de logs no navegador."
