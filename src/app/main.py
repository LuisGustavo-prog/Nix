import random
import asyncio
from app.core.tts import speak_async
from app.core.stt import listen_with_cancel_check
from app.core.intent import process_command
from app.core.wake_word import WakeWordDetector
from app.core.signals import RestartRequested, ShutdownRequested
from app.core.logging_config import setup_logging, setup_command_logger, setup_cancel_check_logger, get_logger
from app.prompts.greetings import STARTUP_GREETINGS
from app.web.username_server import capture_username_async

_MIN_SECONDS_BETWEEN_RESTARTS = 5
_MAX_RESTART_BACKOFF = 60

log = get_logger("main")

def _random_greeting(username: str) -> str:
    return random.choice(STARTUP_GREETINGS).format(username=username)

async def _safe_speak(text: str) -> None:
    try:
        await speak_async(text)
    except Exception:
        log.exception("Falha ao gerar/tocar TTS para o texto: %r", text)

def _safe_listen_with_cancel_check(duration: int = 5, use_command_context: bool = True) -> tuple[str, bool]:
    try:
        return listen_with_cancel_check(duration=duration, use_command_context=use_command_context)
    except Exception:
        log.exception("Falha ao capturar/transcrever áudio (com checagem de cancelamento)")
        return "", False

_USERNAME_CAPTURE_TIMEOUT_SECONDS = 5 * 60

async def ensure_username() -> str:
    from app.config import settings

    if settings.NIX_USERNAME:
        return settings.NIX_USERNAME

    await _safe_speak(
        "Oi! Ainda não te conheço. Abri uma página no navegador pra você "
        "digitar seu nome, é só preencher lá."
    )

    raw_name, username = await capture_username_async(timeout=_USERNAME_CAPTURE_TIMEOUT_SECONDS)

    if username == "usuario" and raw_name == "usuario":
        await _safe_speak(
            "Não recebi seu nome a tempo pela página. Vou seguir como "
            "'usuário' por enquanto, reinicia quando quiser tentar de novo."
        )
    else:
        await _safe_speak(f"Beleza, {raw_name}! Nome salvo.")

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

    try:
        result = await process_command(user_text)
    except (ShutdownRequested, RestartRequested) as signal:
        await _safe_speak(str(signal))
        raise
    except Exception:
        log.exception("Falha ao processar o comando: %r", user_text)
        await _safe_speak("Desculpa, algo deu errado ao processar esse comando.")
        return True

    await _safe_speak(result)
    return True

async def command_loop(wake_word_detector: WakeWordDetector):
    while True:
        await _handle_one_command(wake_word_detector)

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
        except ShutdownRequested:
            log.info("Nix encerrado por comando de voz.")
            break
        except RestartRequested:
            log.info("Reiniciando o Nix por comando de voz...")
            raise
        except Exception:
            log.exception(
                "Loop principal quebrou de forma inesperada. Reiniciando em %ds...",
                backoff,
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _MAX_RESTART_BACKOFF)
