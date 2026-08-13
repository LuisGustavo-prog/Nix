import asyncio
import time
import tempfile
from pathlib import Path
import edge_tts
import pygame

from app.core.logging_config import get_logger

log = get_logger("tts")

VOICE = "pt-BR-FranciscaNeural"

async def _generate_audio(text: str, output_path: Path) -> None:
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(output_path))

_mixer_ready = False

def _ensure_mixer_ready() -> None:
    global _mixer_ready
    if not _mixer_ready:
        pygame.mixer.init()
        _mixer_ready = True

def _play_audio(path: Path) -> None:
    _ensure_mixer_ready()
    pygame.mixer.music.load(str(path))
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.music.unload()
    time.sleep(0.2)  

async def speak_async(text: str) -> None:
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        await _generate_audio(text, tmp_path)
    except Exception:
        log.exception("Falha ao gerar áudio (TTS), pulando essa fala: %r", text)
        tmp_path.unlink(missing_ok=True)
        return

    try:
        _play_audio(tmp_path)
    except Exception:
        log.exception("Falha ao reproduzir áudio (TTS)")
    finally:
        tmp_path.unlink(missing_ok=True)

def speak(text: str) -> None:
    asyncio.run(speak_async(text))
    