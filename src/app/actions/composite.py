from app.actions.apps import open_app
from app.actions.youtube import search_video_on_youtube

_WORK_APP_NAME = "visual studio code"
_WORK_MUSIC_QUERY = "Michael Jackson Bad"

def start_work_mode() -> str:
    music_result = search_video_on_youtube(_WORK_MUSIC_QUERY)
    app_result = open_app(_WORK_APP_NAME)
    return f"{app_result} {music_result}"