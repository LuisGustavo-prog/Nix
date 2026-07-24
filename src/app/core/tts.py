import asyncio
import time
import tempfile
from pathlib import Path
import edge_tts
import pygame

VOICE = "pt-BR-FranciscaNeural"

async def _generate_audio(text: str, output_path: Path) -> None:
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(output_path))

import time

def _play_audio(path: Path) -> None:
    pygame.mixer.init()
    pygame.mixer.music.load(str(path))
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.music.unload()  
    pygame.mixer.quit()
    time.sleep(0.2)  

async def speak_async(text: str) -> None:
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    await _generate_audio(text, tmp_path)
    _play_audio(tmp_path)

    tmp_path.unlink(missing_ok=True)

def speak(text: str) -> None:
    asyncio.run(speak_async(text))
