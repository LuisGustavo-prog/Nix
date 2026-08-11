from urllib.parse import quote_plus

from app.core.utils.browser_launch import open_url_in_opera

_SEARCH_URL_TEMPLATE = "https://www.google.com/search?q={query}"

def search_in_browser(query: str) -> str:
    search_url = _SEARCH_URL_TEMPLATE.format(query=quote_plus(query))

    if not open_url_in_opera(search_url):
        return f"Não consegui abrir o Opera para buscar por {query}."

    return f"Buscando por {query} no Opera."
