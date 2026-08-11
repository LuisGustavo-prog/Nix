import asyncio
import json
import re
import time
from datetime import datetime
from groq import BadRequestError, RateLimitError
from app.core.cancel_match import is_cancel_command
from app.core.intent import fast_match
from app.core.intent.correction import correct_transcription
from app.core.intent.groq_client import (
    LOW_TOKEN_BUFFER,
    RATE_LIMIT_COOLDOWN_SECONDS,
    TOOL_CALLING_MODEL,
    client,
    read_remaining_tokens,
)
from app.core.intent.tool_selection import needs_correction, select_tools
from app.core.intent.tools import AVAILABLE_FUNCTIONS
from app.core.logging_config import get_command_logger, get_logger
from app.core.signals import RestartRequested, ShutdownRequested
from app.prompts.system_prompts import TOOL_CALLING_SYSTEM_PROMPT

cmd_log = get_command_logger()
log = get_logger("intent")

_BLOCK_WIDTH = 64

_tools_cooldown_until = 0.0
_tools_tokens_remaining: int | None = None

class _ToolsInCooldown(Exception):
    """Levantada quando o Tier 1 está em cooldown por rate limit recente."""

def _log_command(
    heard_text: str,
    tier: str,
    action_desc: str,
    response: str,
    corrected_text: str | None = None,
) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"┌─ {timestamp} ─ {tier} "
    header = header + "─" * max(0, _BLOCK_WIDTH - len(header))

    lines = [header, f"│ ouvido   : {heard_text!r}"]
    if corrected_text is not None and corrected_text.strip().lower() != heard_text.strip().lower():
        lines.append(f"│ corrigido: {corrected_text!r}")
    lines.append(f"│ ação     : {action_desc}")
    lines.append(f"│ resposta : {response!r}")
    lines.append(f"└{'─' * _BLOCK_WIDTH}")

    cmd_log.info("\n".join(lines))

async def _call_groq_with_tools(user_text: str):
    global _tools_cooldown_until, _tools_tokens_remaining

    if time.monotonic() < _tools_cooldown_until:
        raise _ToolsInCooldown()

    if _tools_tokens_remaining is not None and _tools_tokens_remaining < LOW_TOKEN_BUFFER:
        raise _ToolsInCooldown()

    max_attempts = 3
    last_error = None
    selected_tools = select_tools(user_text)

    for _attempt in range(max_attempts):
        try:
            raw_response = await client.chat.completions.with_raw_response.create(
                model=TOOL_CALLING_MODEL,
                messages=[
                    {"role": "system", "content": TOOL_CALLING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_text},
                ],
                tools=selected_tools,
                tool_choice="auto",
                parallel_tool_calls=False,
            )
            remaining = read_remaining_tokens(raw_response.headers)
            if remaining is not None:
                _tools_tokens_remaining = remaining
            return await raw_response.parse()
        except BadRequestError as e:
            last_error = e
            continue
        except RateLimitError:
            _tools_cooldown_until = time.monotonic() + RATE_LIMIT_COOLDOWN_SECONDS
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
        log.exception(
            "Parâmetros errados ao chamar %s com %r", function_to_call.__name__, function_args
        )
        return "Recebi os parâmetros errados para executar esse comando. Pode repetir de um jeito diferente?"
    except Exception:
        log.exception(
            "Falha ao executar %s com %r", function_to_call.__name__, function_args
        )
        return "Ocorreu um erro ao tentar executar esse comando."


async def process_command(user_text: str) -> str:
    if is_cancel_command(user_text):
        _log_command(user_text, "TIER_0_CANCELLED", "nenhuma", "Comando cancelado.")
        return "Comando cancelado."

    if fast_match.is_shutdown_command(user_text):
        response_text = "Até logo!"
        _log_command(user_text, "TIER_0_SHUTDOWN", "shutdown_nix", response_text)
        raise ShutdownRequested(response_text)

    if fast_match.is_restart_command(user_text):
        response_text = "Reiniciando, já volto."
        _log_command(user_text, "TIER_0_RESTART", "restart_nix", response_text)
        raise RestartRequested(response_text)

    quick_match = fast_match.match_simple_command(user_text)
    was_corrected = False
    raw_text = user_text

    if quick_match is None and needs_correction(user_text):
        corrected_text = await correct_transcription(user_text)
        if corrected_text.strip().lower() != user_text.strip().lower():
            was_corrected = True
            user_text = corrected_text
            quick_match = fast_match.match_simple_command(user_text)

    if quick_match:
        function_name, function_args = quick_match
        function_to_call = AVAILABLE_FUNCTIONS.get(function_name)
        if function_to_call:
            response_text = await _execute_function(function_to_call, function_args)
            tier = "TIER_0_5_CORRECTED_MATCH" if was_corrected else "TIER_0_QUICK_MATCH"
            _log_command(raw_text, tier, f"{function_name}({function_args})", response_text, corrected_text=user_text)
            return response_text

    try:
        response = await _call_groq_with_tools(user_text)
    except (RateLimitError, _ToolsInCooldown):
        tier = "TIER_1_RATE_LIMIT+TIER_0_5" if was_corrected else "TIER_1_RATE_LIMIT"
        _log_command(raw_text, tier, "nenhuma", "Tá pegado agora, tenta de novo daqui a pouco.", corrected_text=user_text)
        return "Tá pegado agora, tenta de novo daqui a pouco."
    except BadRequestError as e:
        fallback = _try_parse_broken_tool_call(str(e))
        if fallback:
            function_name, function_args = fallback
            function_to_call = AVAILABLE_FUNCTIONS.get(function_name)
            if function_to_call:
                response_text = await _execute_function(function_to_call, function_args)
                tier = "TIER_1_FALLBACK_PARSE+TIER_0_5" if was_corrected else "TIER_1_FALLBACK_PARSE"
                _log_command(raw_text, tier, f"{function_name}({function_args})", response_text, corrected_text=user_text)
                return response_text

        tier = "TIER_1_FALLBACK_FAILED+TIER_0_5" if was_corrected else "TIER_1_FALLBACK_FAILED"
        _log_command(raw_text, tier, "nenhuma", "Desculpa, não consegui processar esse comando. Pode repetir?", corrected_text=user_text)
        return "Desculpa, não consegui processar esse comando. Pode repetir?"

    message = response.choices[0].message

    if message.tool_calls:
        results = []

        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments) or {}

            function_to_call = AVAILABLE_FUNCTIONS.get(function_name)
            if function_to_call is None:
                error_msg = f"Não sei executar a ação {function_name}."
                results.append(error_msg)
                tier = "TIER_1_UNKNOWN_TOOL+TIER_0_5" if was_corrected else "TIER_1_UNKNOWN_TOOL"
                _log_command(raw_text, tier, function_name, error_msg, corrected_text=user_text)
                continue

            result = await _execute_function(function_to_call, function_args)
            results.append(result)
            tier = "TIER_1_TOOL_CALL+TIER_0_5" if was_corrected else "TIER_1_TOOL_CALL"
            _log_command(raw_text, tier, f"{function_name}({function_args})", result, corrected_text=user_text)

        return " ".join(results)

    final_response = message.content or "Não entendi o comando."
    tier = "TIER_1_TEXT_ONLY+TIER_0_5" if was_corrected else "TIER_1_TEXT_ONLY"
    _log_command(raw_text, tier, "nenhuma", final_response, corrected_text=user_text)
    return final_response
