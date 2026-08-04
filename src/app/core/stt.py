import time
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from app.core.audio import record_audio_smart, SAMPLE_RATE
from app.core.logging_config import get_logger

log = get_logger("stt")

_KNOWN_CORRECTIONS = {
    "niki": "nix",
    "nike": "nix",
    "nick": "nix",
    "nikes": "nix",
    "editado": "ditado",
    "ópera": "opera",
}

_INITIAL_PROMPT = (
    "Comandos de voz para o assistente Nix, em português, com nomes de "
    "músicas e artistas que podem estar em inglês, ex: toca Bohemian "
    "Rhapsody do Queen no YouTube, abrir aplicativos, pesquisar vídeos "
    "no YouTube, controlar volume, fechar programas."
)

_model = WhisperModel(
    "large-v3-turbo",
    device="cpu",
    compute_type="int8",
    cpu_threads=4
)

def _play_beep(duration: float = 0.2, frequency: int = 880) -> None:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    tone = np.sin(frequency * t * 2 * np.pi) * 0.8
    sd.play(tone.astype(np.float32), SAMPLE_RATE)
    sd.wait()

def _correct_known_mishearings(text: str) -> str:
    words = text.split()
    corrected = [
        _KNOWN_CORRECTIONS.get(word.lower().strip(",.!?"), word)
        for word in words
    ]
    return " ".join(corrected)

def listen(duration: float | None = None, use_command_context: bool = False) -> str:
    time.sleep(0.1)
    _play_beep()

    audio_data = record_audio_smart()

    if audio_data is None:
        return ""

    transcribe_kwargs = {"language": "pt", "vad_filter": True}
    if use_command_context:
        transcribe_kwargs["initial_prompt"] = _INITIAL_PROMPT

    segments, _ = _model.transcribe(
        audio_data,
        beam_size=5,
        condition_on_previous_text=False,
        **transcribe_kwargs,
    )

    text = " ".join(segment.text for segment in segments).strip()
    text = _correct_known_mishearings(text)

    log.debug("Texto transcrito: %r", text)
    return text
