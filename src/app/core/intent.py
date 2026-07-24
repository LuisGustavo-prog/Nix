import re
import json
import asyncio
from groq import Groq, BadRequestError
from app.actions.browser import search_in_browser
from app.config import settings
from app.actions.apps import open_app, close_app
from app.actions.night_light import toggle_night_light
from app.actions.volume import set_volume, increase_volume, decrease_volume, mute
from app.actions.media_control import play_pause, next_track, previous_track, stop
from app.actions.dictation import dictate_text
from app.actions.youtube import search_video_on_youtube
from app.actions.composite import start_work_mode

client = Groq(api_key=settings.GROQ_API_KEY)

MODEL = "llama-3.3-70b-versatile"
_CORRECTION_MODEL = "llama-3.1-8b-instant"  

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

_AVAILABLE_FUNCTIONS = {
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
}
_TOOLS = [
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
                "Busca um vídeo no YouTube e abre o primeiro resultado, "
                "priorizando música quando fizer sentido. Use tanto pra "
                "vídeos comuns ('procura um vídeo sobre programação no "
                "YouTube') quanto pra tocar música, já que não há Spotify "
                "integrado ('toca [música/artista]', 'coloca [música] pra "
                "tocar', 'toca [música] no YouTube')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Termo, música/artista ou assunto do vídeo buscado.",
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
    }
]

def _match_simple_command(user_text: str):
    text = user_text.lower()
    has_digit = any(char.isdigit() for char in text)

    if re.search(r"\b(desmuta|desmute|desmutar)\b", text):
        return "mute", {"should_mute": False}
    if re.search(r"\b(muta|mute|mutar)\b", text):
        return "mute", {"should_mute": True}

    if any(word in text for word in ["volume", "som", "áudio", "audio"]):
        if has_digit:
            percentage_match = re.search(r"(\d{1,3})\s*(%|por cento)?", text)
            if percentage_match:
                percentage = max(0, min(100, int(percentage_match.group(1))))
                return "set_volume", {"percentage": percentage}
        else:
            if re.search(r"\b(aument\w*|sobe|sobre)\b", text):
                return "adjust_volume", {"direction": "increase"}
            if re.search(r"\b(abaix\w*|diminu\w*|baixa)\b", text):
                return "adjust_volume", {"direction": "decrease"}

    if "luz noturna" in text or "night light" in text:
        return "toggle_night_light", {}

    if re.search(r"\b(pausa|pause)\b", text) or "dá play" in text or "da play" in text:
        return "control_media", {"action": "play_pause"}
    if re.search(r"\b(pr[oó]xima|pula|pular)\b", text):
        return "control_media", {"action": "next_track"}
    if "anterior" in text or ("volta" in text and any(w in text for w in ["música", "musica", "faixa"])):
        return "control_media", {"action": "previous_track"}
    if re.search(r"para(r)? a (m[uú]sica)", text):
        return "control_media", {"action": "stop"}

    if "modo de escrita" in text or "modo de digitação" in text:
        return "dictate_text", {}

    if any(phrase in text for phrase in ["bora trabalhar", "vamos trabalhar", "hora de trabalhar"]):
        return "start_work_mode", {}

    return None

_CORRECTION_SYSTEM_PROMPT = (
    "Você corrige erros óbvios de transcrição de voz em português "
    "brasileiro, sem mudar o sentido da frase nem adicionar informação "
    "nova. Responda só com a frase corrigida, sem aspas, sem explicações."
)

def _correct_transcription(user_text: str) -> str:
    try:
        response = client.chat.completions.create(
            model=_CORRECTION_MODEL,
            messages=[
                {"role": "system", "content": _CORRECTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            max_tokens=60,
            temperature=0,
        )
        corrected = response.choices[0].message.content
        return corrected.strip() if corrected else user_text
    except Exception:
        return user_text

_TOOLS_BY_NAME = {tool["function"]["name"]: tool for tool in _TOOLS}
_CATEGORY_RULES = [
    (["abre", "abrir", "fecha", "fechar"], ["open_app", "close_app"]),
    (["volume", "som", "mudo", "muta", "desmuta", "áudio", "audio"], ["set_volume", "adjust_volume", "mute"]),
    (["luz noturna", "night light"], ["toggle_night_light"]),
    (
        ["pausa", "pause", "toca", "tocar", "próxima", "proxima", "anterior", "continua", "retoma", "play", "stop", "para a música", "para a musica"],
        ["control_media", "search_video_on_youtube"],
    ),
    (["youtube"], ["search_video_on_youtube"]),
    (["navegador", "opera"], ["search_in_browser"]),
    (["modo de escrita", "ditado", "escreve", "escrever", "digita"], ["dictate_text"]),
]

def _select_tools(user_text: str) -> list:
    text = user_text.lower()
    selected_names = set()

    for keywords, tool_names in _CATEGORY_RULES:
        if any(keyword in text for keyword in keywords):
            selected_names.update(tool_names)

    if not selected_names:
        return _TOOLS

    return [_TOOLS_BY_NAME[name] for name in selected_names if name in _TOOLS_BY_NAME]

_SYSTEM_PROMPT = (
    "Você é o Nix, assistente de voz pessoal. Chame a ferramenta certa "
    "para o comando do usuário. Se nenhuma tool corresponder, responda "
    "em texto, breve."
)

def _call_groq_with_tools(user_text: str):
    max_attempts = 3
    last_error = None
    selected_tools = _select_tools(user_text)

    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_text},
                ],
                tools=selected_tools,
                tool_choice="auto",
                parallel_tool_calls=False,  
            )
            return response
        except BadRequestError as e:
            last_error = e
            continue

    raise last_error

_FAILED_GENERATION_PATTERN = re.compile(
    r"'failed_generation':\s*'(?P<raw>.*?)'\}", re.DOTALL
)
_FUNCTION_NAME_PATTERN = re.compile(r"<function=(?P<name>\w+)")
_JSON_ARGS_PATTERN = re.compile(r"(?P<args>\{.*\})", re.DOTALL)

def _try_parse_broken_tool_call(error_text: str):
    generation_match = _FAILED_GENERATION_PATTERN.search(error_text)
    if not generation_match:
        return None

    raw = generation_match.group("raw")

    name_match = _FUNCTION_NAME_PATTERN.search(raw)
    args_match = _JSON_ARGS_PATTERN.search(raw)
    if not name_match or not args_match:
        return None

    function_name = name_match.group("name")
    try:
        function_args = json.loads(args_match.group("args"))
    except json.JSONDecodeError:
        return None

    return function_name, function_args

async def _execute_function(function_to_call, function_args: dict) -> str:
    try:
        result = function_to_call(**function_args)
        if asyncio.iscoroutine(result):
            result = await result
        return result
    except TypeError:
        return "Recebi os parâmetros errados para executar esse comando. Pode repetir de um jeito diferente?"
    except Exception:
        return "Ocorreu um erro ao tentar executar esse comando."

async def process_command(user_text: str) -> str:
    quick_match = _match_simple_command(user_text)

    if quick_match is None:
        corrected_text = _correct_transcription(user_text)
        if corrected_text.strip().lower() != user_text.strip().lower():
            user_text = corrected_text
            quick_match = _match_simple_command(user_text)

    if quick_match:
        function_name, function_args = quick_match
        function_to_call = _AVAILABLE_FUNCTIONS.get(function_name)
        if function_to_call:
            return await _execute_function(function_to_call, function_args)

    try:
        response = _call_groq_with_tools(user_text)
    except BadRequestError as e:
        fallback = _try_parse_broken_tool_call(str(e))
        if fallback:
            function_name, function_args = fallback
            function_to_call = _AVAILABLE_FUNCTIONS.get(function_name)
            if function_to_call:
                return await _execute_function(function_to_call, function_args)

        return "Desculpa, não consegui processar esse comando. Pode repetir?"

    message = response.choices[0].message

    if message.tool_calls:
        results = []

        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments) or {}

            function_to_call = _AVAILABLE_FUNCTIONS.get(function_name)
            if function_to_call is None:
                results.append(f"Não sei executar a ação {function_name}.")
                continue

            result = await _execute_function(function_to_call, function_args)
            results.append(result)

        return " ".join(results)

    return message.content or "Não entendi o comando."
