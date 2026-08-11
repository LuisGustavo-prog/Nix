import requests
from app.config import ConfigError, settings
from app.core.utils.browser_launch import open_url_in_opera

_SEARCH_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"
_WATCH_URL_TEMPLATE = "https://music.youtube.com/watch?v={video_id}"
_MUSIC_CATEGORY_ID = "10"

def _search_video_id(query: str) -> str | None:
    params = {
        "part": "snippet",
        "q": query,
        "key": settings.YOUTUBE_API_KEY,
        "maxResults": 1,
        "type": "video",
        "videoCategoryId": _MUSIC_CATEGORY_ID,
    }

    response = requests.get(_SEARCH_ENDPOINT, params=params, timeout=5)
    response.raise_for_status()

    items = response.json().get("items", [])
    if not items:
        return None

    return items[0]["id"]["videoId"]

def search_video_on_youtube(query: str) -> str:
    try:
        settings.require("YOUTUBE_API_KEY")
    except ConfigError:
        return "A busca no YouTube ainda não está configurada."

    try:
        video_id = _search_video_id(query)
    except requests.RequestException:
        return "Não consegui me conectar ao YouTube agora."

    if video_id is None:
        return f"Não encontrei nenhuma música para {query}."

    video_url = _WATCH_URL_TEMPLATE.format(video_id=video_id)

    if not open_url_in_opera(video_url):
        return f"Não consegui abrir o vídeo de {query}."

    return f"Abrindo o vídeo de {query} no YouTube."
