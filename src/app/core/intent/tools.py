from app.actions.apps import open_app, close_app
from app.actions.browser import search_in_browser
from app.actions.composite import start_work_mode
from app.actions.dictation import dictate_text
from app.actions.logs_dashboard import show_logs_dashboard
from app.actions.media_control import play_pause, next_track, previous_track, stop
from app.actions.night_light import toggle_night_light
from app.actions.volume import set_volume, increase_volume, decrease_volume, mute
from app.actions.youtube import search_video_on_youtube

def control_media(action: str) -> str:
    dispatch = {
        "play_pause": play_pause,
        "next_track": next_track,
        "previous_track": previous_track,
        "stop": stop,
    }
    function = dispatch.get(action)
    if function is None:
        return f"Ação de mídia desconhecida: {action}."
    return function()


def adjust_volume(direction: str, step: int = 10) -> str:
    if direction == "increase":
        return increase_volume(step)
    if direction == "decrease":
        return decrease_volume(step)
    return f"Direção de volume desconhecida: {direction}."

AVAILABLE_FUNCTIONS = {
    "open_app": open_app,
    "close_app": close_app,
    "set_volume": set_volume,
    "adjust_volume": adjust_volume,
    "mute": mute,
    "toggle_night_light": toggle_night_light,
    "control_media": control_media,
    "search_in_browser": search_in_browser,
    "dictate_text": dictate_text,
    "search_video_on_youtube": search_video_on_youtube,
    "start_work_mode": start_work_mode,
    "show_logs_dashboard": show_logs_dashboard,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Abre um aplicativo, dado o nome dele.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Nome do app, ex: 'bloco de notas', 'spotify', 'opera'.",
                    }
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_app",
            "description": "Fecha um aplicativo que está rodando, dado o nome dele.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Nome do app, ex: 'notepad', 'spotify'.",
                    }
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": (
                "Define o volume para um valor absoluto exato. Use quando o "
                "usuário citar um número, ex: 'coloca o volume em 20'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "percentage": {
                        "type": "integer",
                        "description": "Porcentagem final desejada, de 0 a 100.",
                    }
                },
                "required": ["percentage"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_volume",
            "description": (
                "Aumenta ou diminui o volume relativamente ao nível atual, "
                "sem valor final específico, ex: 'aumenta o volume', 'abaixa "
                "o som'. Se o usuário citar um número, use set_volume."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["increase", "decrease"],
                        "description": "'increase' para aumentar, 'decrease' para diminuir.",
                    },
                    "step": {
                        "type": "integer",
                        "description": "Pontos percentuais a ajustar. Padrão 10.",
                    },
                },
                "required": ["direction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mute",
            "description": "Muta ou desmuta o áudio do sistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "should_mute": {
                        "type": "boolean",
                        "description": "True para mutar, false para desmutar. Padrão true.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "toggle_night_light",
            "description": (
                "Liga ou desliga a luz noturna do Windows. Use para 'ativa/"
                "desativa/liga/desliga a luz noturna', sem parâmetros."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "control_media",
            "description": (
                "Controla a reprodução de mídia atual (música ou vídeo), "
                "sem precisar saber a faixa ou o app. Ações: 'play_pause' "
                "(pausa/retoma, ex: 'pausa a música', 'dá play'), 'next_track' "
                "('próxima música'), 'previous_track' ('volta a música'), "
                "'stop' (parar de vez, só quando pedido explicitamente, "
                "diferente de pausar)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["play_pause", "next_track", "previous_track", "stop"],
                    }
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_in_browser",
            "description": (
                "Busca um assunto no navegador Opera. Use SOMENTE se o "
                "usuário mencionar explicitamente 'navegador' ou 'opera', "
                "ex: 'pesquisa receita de bolo no navegador', 'busca sobre "
                "IA no navegador'. Se ele mencionar YouTube, use "
                "search_video_on_youtube, não essa."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "O termo a ser pesquisado.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dictate_text",
            "description": (
                "Ativa o modo de escrita: grava a fala seguinte e digita o "
                "texto onde o cursor estiver. Ex: 'ativa o modo de escrita'."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_video_on_youtube",
            "description": (
                "Busca uma MÚSICA no YouTube Music e toca o primeiro "
                "resultado. SÓ use esta ferramenta se o usuário mencionar "
                "explicitamente a palavra 'YouTube' no comando, ex: 'toca "
                "[música] no YouTube', 'coloca [música] no YouTube', "
                "'pesquisa [música] no YouTube'. Se o usuário disser só "
                "'toca [música]' ou 'coloca [música] pra tocar', SEM "
                "mencionar YouTube, NÃO chame esta ferramenta, ela vai "
                "ficar ambígua com controle de mídia. NÃO use para vídeos "
                "que não sejam música (tutoriais, notícias, vlogs etc.), o "
                "Nix não busca esse tipo de conteúdo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Nome da música e/ou artista a ser tocado.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_work_mode",
            "description": (
                "Comando composto: abre o VSCode e já toca uma música pra "
                "começar a trabalhar. Use para 'bora trabalhar', 'vamos "
                "trabalhar', 'hora de trabalhar', sem parâmetros."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

TOOLS_BY_NAME = {tool["function"]["name"]: tool for tool in TOOL_SCHEMAS}
