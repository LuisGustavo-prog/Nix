import re
import random
import unicodedata
import asyncio
from pathlib import Path
from app.core.tts import speak_async
from app.core.stt import listen
from app.core.intent import process_command
from app.core.wake_word import WakeWordDetector

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
_GREETINGS = [
    "E aí, {username}! Bora nessa.",
    "Oi, {username}, tudo pronto por aqui.",
    "{username}, Nix online.",
    "Fala, {username}! Pode chamar quando quiser.",
    "Pronto, {username}. É só me chamar.",
]

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

async def _capture_confirmed_name(max_attempts: int = 3) -> str:
    await speak_async("Oi! Ainda não te conheço. Qual é o seu nome?")

    for attempt in range(max_attempts):
        raw_name = listen()

        await speak_async(f"Entendi {raw_name}. Está correto?")
        confirmation = listen()

        if not _is_negative(confirmation):
            return raw_name

        if attempt < max_attempts - 1:
            await speak_async("Desculpa, pode repetir seu nome, por favor?")

    await speak_async(f"Ok, vou seguir com {raw_name} por enquanto.")
    return raw_name

async def ensure_username() -> str:
    from app.config import settings

    if settings.NIX_USERNAME:
        return settings.NIX_USERNAME

    raw_name = await _capture_confirmed_name()

    username = sanitize_username(raw_name)
    save_username_to_env(username)

    # if await username_collection_exists(username):
    #     await speak_async(f"Encontrei um perfil existente para {raw_name}. Vou continuar com ele.")
    # else:
    #     await speak_async(f"Prazer, {raw_name}! Criando seu perfil agora.")

    return username

async def command_loop(wake_word_detector: WakeWordDetector):
    while True:
        await asyncio.to_thread(wake_word_detector.listen_for_wake_word)

        user_text = listen(duration=5, use_command_context=True)

        if not user_text:
            await speak_async("Não consegui te ouvir. Diga 'hey jarvis' de novo quando quiser tentar.")
            continue

        if any(word in user_text.lower() for word in ["parar", "sair", "encerrar"]):
            await speak_async("Até logo!")
            break

        try:
            result = await process_command(user_text)
        except Exception:
            result = "Desculpa, algo deu errado ao processar esse comando."

        await speak_async(result)

async def main():
    username = await ensure_username()
    await speak_async(_random_greeting(username))

    wake_word_detector = WakeWordDetector()
    await command_loop(wake_word_detector)
    