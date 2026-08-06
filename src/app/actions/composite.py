import random
from app.actions.apps import open_app
from app.actions.youtube import search_video_on_youtube

WORK_MUSIC_QUERIES = [
    "Michael Jackson Bad",
    "Michael Jackson Billie Jean",
    "https://music.youtube.com/watch?v=TTzD6gWV16s",
    "Combichrist - Never Surrender [HQ] [Devil May Cry Soundtrack]"
]

_WORK_APP_NAME = "visual studio code"

def start_work_mode() -> str:
    music_query = random.choice(WORK_MUSIC_QUERIES)

    music_result = search_video_on_youtube(music_query)
    app_result = open_app(_WORK_APP_NAME)
    return f"{app_result} {music_result}"