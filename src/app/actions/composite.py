import random
import time
import pyautogui
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

def wait_and_maximize(title_keywords: str, timeout: int = 30) -> bool:
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        matching_windows = [win for win in gw.getAllWindows() if title_keywords.lower() in win.title.lower()]
        
        if matching_windows:
            win = matching_windows[0]
            if win.title != "":
                win.activate() 
                time.sleep(0.5) 
                win.maximize() 
                return True
                
        time.sleep(0.5) 
        
    print("Tempo limite excedido: o aplicativo demorou demais para abrir.")
    return False

def start_work_mode() -> str:
    music_query = random.choice(WORK_MUSIC_QUERIES)
    music_result = search_video_on_youtube(music_query)
    
    app_result = open_app(_WORK_APP_NAME)
    
    wait_and_maximize("Visual Studio Code")

    return f"{app_result} {music_result}"
