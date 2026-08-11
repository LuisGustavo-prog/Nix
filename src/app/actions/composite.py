import random
import time
import asyncio
import pygetwindow as gw
from app.actions.apps import open_app
from app.actions.youtube import search_video_on_youtube
from app.core.logging_config import get_logger
from app.prompts.content import WORK_MUSIC_QUERIES

log = get_logger("composite")

_WORK_APP_NAME = "visual studio code"
_WINDOW_WAIT_TIMEOUT_SECONDS = 15
_WINDOW_POLL_INTERVAL_SECONDS = 0.5
_WINDOW_ACTIVATE_SETTLE_SECONDS = 0.3

def _get_vscode_window_handles() -> set[int]:
    return {
        win._hWnd for win in gw.getAllWindows()
        if _WORK_APP_NAME in win.title.lower() and win.title.strip() != ""
    }

def wait_and_maximize_new_window(previous_handles: set[int], timeout: int = _WINDOW_WAIT_TIMEOUT_SECONDS) -> bool:
    start_time = time.time()

    while time.time() - start_time < timeout:
        all_windows = gw.getAllWindows()

        new_windows = [
            win for win in all_windows
            if _WORK_APP_NAME in win.title.lower()
            and win.title.strip() != ""
            and win._hWnd not in previous_handles
        ]

        if new_windows:
            target_win = new_windows[0]
            try:
                if target_win.isMinimized:
                    target_win.restore()
                target_win.activate()
                time.sleep(_WINDOW_ACTIVATE_SETTLE_SECONDS)
                target_win.maximize()
                return True
            except Exception:
                log.exception("Falha ao ativar/maximizar a nova janela do VS Code")

        time.sleep(_WINDOW_POLL_INTERVAL_SECONDS)

    log.warning("Tempo limite excedido: a nova janela do VS Code demorou demais para abrir.")
    return False

async def start_work_mode() -> str:
    music_query = random.choice(WORK_MUSIC_QUERIES)
    music_result = search_video_on_youtube(music_query)

    existing_handles = _get_vscode_window_handles()

    app_result = open_app(_WORK_APP_NAME)

    await asyncio.to_thread(wait_and_maximize_new_window, existing_handles)

    return f"{app_result} {music_result}"
