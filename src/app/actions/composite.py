import random
import time
import asyncio
import pygetwindow as gw
from app.actions.apps import open_app
from app.actions.youtube import search_video_on_youtube

WORK_MUSIC_QUERIES = [
    "Michael Jackson Bad",
    "Michael Jackson Billie Jean",
    "https://music.youtube.com/watch?v=TTzD6gWV16s",
    "Combichrist - Never Surrender [HQ] [Devil May Cry Soundtrack]"
]

_WORK_APP_NAME = "visual studio code"

def _get_vscode_window_handles() -> set[int]:
    return {
        win._hWnd for win in gw.getAllWindows() 
        if _WORK_APP_NAME in win.title.lower() and win.title.strip() != ""
    }

def wait_and_maximize_new_window(previous_handles: set[int], timeout: int = 15) -> bool:
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
                time.sleep(0.3)
                target_win.maximize()
                return True
            except Exception:
                pass
                
        time.sleep(0.5) 
        
    print("Tempo limite excedido: a nova janela do VS Code demorou demais para abrir.")
    return False

async def start_work_mode() -> str:
    music_query = random.choice(WORK_MUSIC_QUERIES)
    music_result = search_video_on_youtube(music_query)
    
    existing_handles = _get_vscode_window_handles()
    
    app_result = open_app(_WORK_APP_NAME)
    
    await asyncio.to_thread(wait_and_maximize_new_window, existing_handles)

    return f"{app_result} {music_result}"
