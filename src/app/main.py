import re
import random
import unicodedata
import asyncio
from pathlib import Path
from app.core.tts import speak_async
from app.core.stt import listen, listen_with_cancel_check
from app.core.intent import process_command
from app.core.wake_word import WakeWordDetector
from app.core.logging_config import setup_logging, setup_command_logger, setup_cancel_check_logger, get_logger

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
_GREETINGS = [
    "E aí, {username}! Bora nessa.",
    "Oi, {username}, tudo pronto por aqui.",
    "{username}, Nix online.",
    "Fala, {username}! Pode chamar quando quiser.",
    "Pronto, {username}. É só me chamar.",
]

_MIN_SECONDS_BETWEEN_RESTARTS = 5
_MAX_RESTART_BACKOFF = 60

log = get_logger("main")

def _random_greeting(username: str) -> str:
    return random.choice(_GREETINGS).format(username=username)

def sanitize_username(raw: str) -> str:
    normalized = unicodedata.normalize("NFKD", raw)
    without_accents = "".join(c for c in normalized if not unicodedata.combining(c))
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", without_accents.lower().replace(" ", "_"))
    return cleaned

def save_username_to_env(username: str) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    new_line = f"NIX_USERNAME={username}"
    for i, line in enumerate(lines):
        if line.startswith("NIX_USERNAME="):
            lines[i] = new_line
            break
    else:
        lines.append(new_line)
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

def _is_negative(text: str) -> bool:
    text = text.lower()
    return any(word in text for word in ["não", "nao", "errado", "incorreto"])

async def _safe_speak(text: str) -> None:
    try:
        await speak_async(text)
    except Exception:
        log.exception("Falha ao gerar/tocar TTS para o texto: %r", text)

def _safe_listen(duration: int = 3, use_command_context: bool = False) -> str:
    try:
        return listen(duration=duration, use_command_context=use_command_context)
        # return listen(use_command_context=use_command_context)
    except Exception:
        log.exception("Falha ao capturar/transcrever áudio")
        return ""

def _safe_listen_with_cancel_check(duration: int = 5, use_command_context: bool = True) -> tuple[str, bool]:
    try:
        return listen_with_cancel_check(duration=duration, use_command_context=use_command_context)
    except Exception:
        log.exception("Falha ao capturar/transcrever áudio (com checagem de cancelamento)")
        return "", False

async def _capture_confirmed_name(max_attempts: int = 3) -> str:
    await _safe_speak("Oi! Ainda não te conheço. Qual é o seu nome?")

    raw_name = ""
    for attempt in range(max_attempts):
        raw_name = _safe_listen()

        if not raw_name:
            await _safe_speak("Não consegui te ouvir, pode repetir?")
            continue

        await _safe_speak(f"Entendi {raw_name}. Está correto?")
        confirmation = _safe_listen()

        if not _is_negative(confirmation):
            return raw_name

        if attempt < max_attempts - 1:
            await _safe_speak("Desculpa, pode repetir seu nome, por favor?")

    await _safe_speak(f"Ok, vou seguir com {raw_name or 'usuário'} por enquanto.")
    return raw_name or "usuario"

async def ensure_username() -> str:
    from app.config import settings

    if settings.NIX_USERNAME:
        return settings.NIX_USERNAME

    raw_name = await _capture_confirmed_name()

    username = sanitize_username(raw_name)
    save_username_to_env(username)

    return username

async def _handle_one_command(wake_word_detector: WakeWordDetector) -> bool:
    try:
        await asyncio.to_thread(wake_word_detector.listen_for_wake_word)
    except Exception:
        log.exception("Falha ao escutar a wake word, tentando de novo")
        await asyncio.sleep(1)
        return True

    user_text, was_cancelled_early = _safe_listen_with_cancel_check(duration=5, use_command_context=True)

    if was_cancelled_early:
        await _safe_speak("Comando cancelado.")
        return True

    if not user_text:
        await _safe_speak("Não consegui te ouvir. Diga 'hey jarvis' de novo quando quiser tentar.")
        return True

    if any(word in user_text.lower() for word in ["parar", "sair", "encerrar"]):
        await _safe_speak("Até logo!")
        return False

    try:
        result = await process_command(user_text)
    except Exception:
        log.exception("Falha ao processar o comando: %r", user_text)
        result = "Desculpa, algo deu errado ao processar esse comando."

    await _safe_speak(result)
    return True

async def command_loop(wake_word_detector: WakeWordDetector):
    while True:
        should_continue = await _handle_one_command(wake_word_detector)
        if not should_continue:
            break

async def main():
    setup_logging()
    setup_command_logger()
    setup_cancel_check_logger()
    log.info("Nix iniciando...")

    username = await ensure_username()
    await _safe_speak(_random_greeting(username))

    backoff = _MIN_SECONDS_BETWEEN_RESTARTS

    while True:
        try:
            wake_word_detector = WakeWordDetector()
            await command_loop(wake_word_detector)
            log.info("Nix encerrado normalmente pelo usuário.")
            break
        except Exception:
            log.exception(
                "Loop principal quebrou de forma inesperada. Reiniciando em %ds...",
                backoff,
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _MAX_RESTART_BACKOFF)
            