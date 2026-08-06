import re
import json
import time
import asyncio
from datetime import datetime
from difflib import get_close_matches
from groq import AsyncGroq, BadRequestError, RateLimitError
from app.actions.browser import search_in_browser
from app.config import settings
from app.actions.apps import open_app, close_app
from app.actions.night_light import toggle_night_light
from app.actions.volume import set_volume, increase_volume, decrease_volume, mute
from app.actions.media_control import play_pause, next_track, previous_track, stop
from app.actions.dictation import dictate_text
from app.actions.youtube import search_video_on_youtube
from app.actions.composite import start_work_mode
from app.core.logging_config import get_command_logger
from app.core.cancel_match import is_cancel_command
from app.core.signals import RestartRequested, ShutdownRequested

client = AsyncGroq(
    api_key=settings.GROQ_API_KEY,
    max_retries=0,
    timeout=8.0,
)

MODEL = "llama-3.3-70b-versatile"
_CORRECTION_MODEL = "llama-3.1-8b-instant"

_correction_cooldown_until = 0.0
_tools_cooldown_until = 0.0
_RATE_LIMIT_COOLDOWN_SECONDS = 60.0

_correction_tokens_remaining: int | None = None
_tools_tokens_remaining: int | None = None
_LOW_TOKEN_BUFFER = 300  # margem de segurança pra não gastar os últimos tokens da cota


def _update_remaining_tokens(headers, kind: str) -> None:
    global _correction_tokens_remaining, _tools_tokens_remaining

    raw_value = headers.get("x-ratelimit-remaining-tokens")
    if raw_value is None:
        return
    try:
        remaining = int(raw_value)
    except ValueError:
        return

    if kind == "correction":
        _correction_tokens_remaining = remaining
    else:
        _tools_tokens_remaining = remaining


class _ToolsInCooldown(Exception):
    """Levantada quando o Tier 1 está em cooldown por rate limit recente."""

cmd_log = get_command_logger()

_BLOCK_WIDTH = 64

def _log_command(heard_text: str, tier: str, action_desc: str, response: str) -> None:
    """
    Grava um "cartão" por comando em comandos.log, em vez de uma linha
    corrida cheia de "|". Isso deixa muito mais fácil escanear visualmente
    um arquivo que só cresce: cada comando fica isolado num bloco com
    borda própria, com cada campo na sua linha.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"┌─ {timestamp} ─ {tier} "
    header = header + "─" * max(0, _BLOCK_WIDTH - len(header))

    block = (
        f"{header}\n"
        f"│ ouvido   : {heard_text!r}\n"
        f"│ ação     : {action_desc}\n"
        f"│ resposta : {response!r}\n"
        f"└{'─' * _BLOCK_WIDTH}"
    )
    cmd_log.info(block)

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
    }
]

_YOUTUBE_PATTERN = re.compile(
    r"\b(?:toca|tocar|coloca|colocar|abre|abrir|pesquisa|pesquisar|busca|buscar)\s+"
    r"(?:a\s+m[uú]sica\s+|o\s+v[íi]deo\s+(?:de|da|do)\s+|o\s+v[íi]deo\s+)?"
    r"(.+?)\s+no\s+youtube\b",
    re.IGNORECASE,
)
_BROWSER_PATTERN = re.compile(
    r"\b(?:pesquisa|pesquisar|busca|buscar)\s+(?:sobre\s+|por\s+)?"
    r"(.+?)\s+no\s+(?:navegador|opera)\b",
    re.IGNORECASE,
)
_OPEN_APP_PATTERN = re.compile(r"\b(?:abre|abrir|abra)\s+(?:(?:o|a|ou)\s+)?(.+)", re.IGNORECASE)
_CLOSE_APP_PATTERN = re.compile(r"\b(?:fecha|fechar|feche)\s+(?:(?:o|a|ou)\s+)?(.+)", re.IGNORECASE)

_TRAILING_FILLER_WORDS = ("por favor", "pra mim", "para mim")

def _strip_trailing_filler(value: str) -> str:
    cleaned = value.strip(" .,!?")
    for filler in _TRAILING_FILLER_WORDS:
        if cleaned.lower().endswith(filler):
            cleaned = cleaned[: -len(filler)].strip(" .,!?")
    return cleaned

_FIXED_RESTART_PHRASES = {"reiniciar nix", "iniciar nix", "re-iniciar mix", "reiniciar", "iniciar"}
_FIXED_SHUTDOWN_PHRASE = "encerrar nix"

def _normalize_for_fixed_match(text: str) -> str:
    cleaned = _strip_trailing_filler(text).strip().lower()
    cleaned = cleaned.replace("-", "").replace("_", "")
    cleaned = re.sub(r"[.,!?]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def _is_restart_command(text: str) -> bool:
    return _normalize_for_fixed_match(text) in _FIXED_RESTART_PHRASES

def _is_shutdown_command(text: str) -> bool:
    return _normalize_for_fixed_match(text) == _FIXED_SHUTDOWN_PHRASE

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

    if re.search(r"\b(pausa|pause|despausa|despause|continua|continue|retoma|retomar)\b", text) or "dá play" in text or "da play" in text:
        return "control_media", {"action": "play_pause"}
    if re.search(r"\b(pr[oó]xima|pula|pular)\b", text):
        return "control_media", {"action": "next_track"}
    if re.search(r"\b(anterior|volt[ae]|voltar)\b", text):
        return "control_media", {"action": "previous_track"}
    if re.search(r"\b(para|pare|parar)\s+a\s+(m[uú]sica)\b", text):
        return "control_media", {"action": "stop"}

    if any(phrase in text for phrase in ["modo de escrita", "modo de digitação", "modo de ditado"]) or re.search(r"\b(escreve|escrever|digita|ditar)\b", text):
        return "dictate_text", {}

    if any(phrase in text for phrase in ["bora trabalhar", "vamos trabalhar", "hora de trabalhar"]):
        return "start_work_mode", {}

    if any(phrase in text for phrase in ["quero desenhar", "vou desenhar", "bora desenhar"]):
        return "open_app", {"app_name": "paint"}

    match = _YOUTUBE_PATTERN.search(text)
    if match:
        query = _strip_trailing_filler(match.group(1))
        if query:
            return "search_video_on_youtube", {"query": query}

    match = _BROWSER_PATTERN.search(text)
    if match:
        query = _strip_trailing_filler(match.group(1))
        if query:
            return "search_in_browser", {"query": query}

    match = _CLOSE_APP_PATTERN.search(text)
    if match:
        app_name = _strip_trailing_filler(match.group(1))
        if app_name:
            return "close_app", {"app_name": app_name}

    match = _OPEN_APP_PATTERN.search(text)
    if match:
        app_name = _strip_trailing_filler(match.group(1))
        if app_name:
            return "open_app", {"app_name": app_name}

    return None

_CORRECTION_SYSTEM_PROMPT = (
    "Você corrige erros óbvios de transcrição de voz em português "
    "brasileiro, sem mudar o sentido da frase nem adicionar informação "
    "nova. Responda só com a frase corrigida, sem aspas, sem explicações."
)

async def _correct_transcription(user_text: str) -> str:
    global _correction_cooldown_until

    if time.monotonic() < _correction_cooldown_until:
        return user_text

    if _correction_tokens_remaining is not None and _correction_tokens_remaining < _LOW_TOKEN_BUFFER:
        return user_text

    try:
        raw_response = await client.chat.completions.with_raw_response.create(
            model=_CORRECTION_MODEL,
            messages=[
                {"role": "system", "content": _CORRECTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            max_tokens=60,
            temperature=0,
        )
        _update_remaining_tokens(raw_response.headers, "correction")
        response = await raw_response.parse()
        corrected = response.choices[0].message.content
        return corrected.strip() if corrected else user_text
    except RateLimitError:
        _correction_cooldown_until = time.monotonic() + _RATE_LIMIT_COOLDOWN_SECONDS
        return user_text
    except Exception:
        return user_text

_TOOLS_BY_NAME = {tool["function"]["name"]: tool for tool in _TOOLS}
_CATEGORY_RULES = [
    (["abre", "abrir", "fecha", "fechar"], ["open_app", "close_app"]),
    (["volume", "som", "mudo", "muta", "desmuta", "áudio", "audio"], ["set_volume", "adjust_volume", "mute"]),
    (["luz noturna", "night light"], ["toggle_night_light"]),
    (
        ["pausa", "pause", "despausa", "próxima", "proxima", "volta", "volte", "anterior", "continua", "retoma", "play", "stop", "para a música", "para a musica", "pare a música", "pare a musica"],
        ["control_media"],
    ),
    (["youtube"], ["search_video_on_youtube", "control_media"]),
    (["navegador", "opera"], ["search_in_browser"]),
    (["modo de escrita", "ditado", "escreve", "escrever", "digita"], ["dictate_text"]),
]

_ACTION_VERBS = [
    "abre", "abrir", "abra", "fecha", "fechar", "feche",
    "toca", "tocar", "coloca", "colocar",
    "pesquisa", "pesquisar", "busca", "buscar",
]
_TRIGGER_VOCABULARY = sorted({
    word
    for keywords, _ in _CATEGORY_RULES
    for phrase in keywords
    for word in phrase.split()
} | set(_ACTION_VERBS))

def _needs_correction(user_text: str, cutoff: float = 0.75) -> bool:
    words = re.findall(r"[a-zà-ÿ]+", user_text.lower())
    for word in words:
        if word in _TRIGGER_VOCABULARY:
            continue
        if get_close_matches(word, _TRIGGER_VOCABULARY, n=1, cutoff=cutoff):
            return True
    return False

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

async def _call_groq_with_tools(user_text: str):
    global _tools_cooldown_until

    if time.monotonic() < _tools_cooldown_until:
        raise _ToolsInCooldown()

    if _tools_tokens_remaining is not None and _tools_tokens_remaining < _LOW_TOKEN_BUFFER:
        raise _ToolsInCooldown()

    max_attempts = 3
    last_error = None
    selected_tools = _select_tools(user_text)

    for attempt in range(max_attempts):
        try:
            raw_response = await client.chat.completions.with_raw_response.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_text},
                ],
                tools=selected_tools,
                tool_choice="auto",
                parallel_tool_calls=False,
            )
            _update_remaining_tokens(raw_response.headers, "tools")
            return await raw_response.parse()
        except BadRequestError as e:
            last_error = e
            continue
        except RateLimitError:
            _tools_cooldown_until = time.monotonic() + _RATE_LIMIT_COOLDOWN_SECONDS
            raise

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
    if is_cancel_command(user_text):
        _log_command(user_text, "TIER_0_CANCELLED", "nenhuma", "Comando cancelado.")
        return "Comando cancelado."

    if _is_shutdown_command(user_text):
        response_text = "Até logo!"
        _log_command(user_text, "TIER_0_SHUTDOWN", "shutdown_nix", response_text)
        raise ShutdownRequested(response_text)

    if _is_restart_command(user_text):
        response_text = "Reiniciando, já volto."
        _log_command(user_text, "TIER_0_RESTART", "restart_nix", response_text)
        raise RestartRequested(response_text)

    quick_match = _match_simple_command(user_text)
    was_corrected = False

    if quick_match is None and _needs_correction(user_text):
        corrected_text = await _correct_transcription(user_text)
        if corrected_text.strip().lower() != user_text.strip().lower():
            was_corrected = True
            user_text = corrected_text
            quick_match = _match_simple_command(user_text)

    if quick_match:
        function_name, function_args = quick_match
        function_to_call = _AVAILABLE_FUNCTIONS.get(function_name)
        if function_to_call:
            response_text = await _execute_function(function_to_call, function_args)
            tier = "TIER_0_5_CORRECTED_MATCH" if was_corrected else "TIER_0_QUICK_MATCH"
            _log_command(user_text, tier, f"{function_name}({function_args})", response_text)
            return response_text

    try:
        response = await _call_groq_with_tools(user_text)
    except (RateLimitError, _ToolsInCooldown):
        tier = "TIER_1_RATE_LIMIT+TIER_0_5" if was_corrected else "TIER_1_RATE_LIMIT"
        _log_command(user_text, tier, "nenhuma", "Tá pegado agora, tenta de novo daqui a pouco.")
        return "Tá pegado agora, tenta de novo daqui a pouco."
    except BadRequestError as e:
        fallback = _try_parse_broken_tool_call(str(e))
        if fallback:
            function_name, function_args = fallback
            function_to_call = _AVAILABLE_FUNCTIONS.get(function_name)
            if function_to_call:
                response_text = await _execute_function(function_to_call, function_args)
                tier = "TIER_1_FALLBACK_PARSE+TIER_0_5" if was_corrected else "TIER_1_FALLBACK_PARSE"
                _log_command(user_text, tier, f"{function_name}({function_args})", response_text)
                return response_text

        tier = "TIER_1_FALLBACK_FAILED+TIER_0_5" if was_corrected else "TIER_1_FALLBACK_FAILED"
        _log_command(user_text, tier, "nenhuma", "Desculpa, não consegui processar esse comando. Pode repetir?")
        return "Desculpa, não consegui processar esse comando. Pode repetir?"

    message = response.choices[0].message

    if message.tool_calls:
        results = []

        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments) or {}

            function_to_call = _AVAILABLE_FUNCTIONS.get(function_name)
            if function_to_call is None:
                error_msg = f"Não sei executar a ação {function_name}."
                results.append(error_msg)
                tier = "TIER_1_UNKNOWN_TOOL+TIER_0_5" if was_corrected else "TIER_1_UNKNOWN_TOOL"
                _log_command(user_text, tier, function_name, error_msg)
                continue

            result = await _execute_function(function_to_call, function_args)
            results.append(result)
            tier = "TIER_1_TOOL_CALL+TIER_0_5" if was_corrected else "TIER_1_TOOL_CALL"
            _log_command(user_text, tier, f"{function_name}({function_args})", result)

        return " ".join(results)

    final_response = message.content or "Não entendi o comando."
    tier = "TIER_1_TEXT_ONLY+TIER_0_5" if was_corrected else "TIER_1_TEXT_ONLY"
    _log_command(user_text, tier, "nenhuma", final_response)
    return final_response
