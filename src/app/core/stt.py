import time
import tempfile
from pathlib import Path
import numpy as np
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
DURATION_SECONDS = 3
_KNOWN_CORRECTIONS = {
    "niki": "nix",
    "nike": "nix",
    "nick": "nix",
    "nikes": "nix",
    "editado": "ditado"
}
_INITIAL_PROMPT = (
    "Comandos de voz para o assistente Nix: abrir aplicativos, "
    "tocar música no Spotify, pesquisar vídeos no YouTube, "
    "controlar volume, fechar programas."
)

_model = WhisperModel("small", device="cpu", compute_type="int8")

def _play_beep(duration: float = 0.2, frequency: int = 880) -> None:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    tone = np.sin(frequency * t * 2 * np.pi) * 0.8  
    sd.play(tone.astype(np.float32), SAMPLE_RATE)
    sd.wait()

def _record_audio(output_path: Path, duration: int = DURATION_SECONDS) -> None:
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    sf.write(str(output_path), audio, SAMPLE_RATE)

def _correct_known_mishearings(text: str) -> str:
    words = text.split()
    corrected = [
        _KNOWN_CORRECTIONS.get(word.lower().strip(",.!?"), word)
        for word in words
    ]
    return " ".join(corrected)

def listen(duration: int = DURATION_SECONDS, use_command_context: bool = False) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    time.sleep(0.3)
    _play_beep()
    _record_audio(tmp_path, duration)

    transcribe_kwargs = {"language": "pt", "vad_filter": True}
    if use_command_context:
        transcribe_kwargs["initial_prompt"] = _INITIAL_PROMPT

    segments, _ = _model.transcribe(
        str(tmp_path),
        beam_size=5,
        condition_on_previous_text=False,
        **transcribe_kwargs,
    )
    text = " ".join(segment.text for segment in segments).strip()
    text = _correct_known_mishearings(text)

    print(f"[STT] Texto transcrito: '{text}'")  # debug temporário

    tmp_path.unlink(missing_ok=True)
    return text
