import os
import re
import time
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from app.core.audio import record_audio_smart, record_audio_with_cancel_check, SAMPLE_RATE
from app.core.logging_config import get_logger, get_cancel_check_logger
from app.core.cancel_match import is_cancel_command

log = get_logger("stt")
cancel_log = get_cancel_check_logger()

_TAG_WIDTH = 11

def _tag(label: str) -> str:
    return f"[{label:<{_TAG_WIDTH}}]"

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
_LOGICAL_CPUS = os.cpu_count() or 4
_MAIN_MODEL_THREADS = max(2, min(4, _LOGICAL_CPUS // 2))
_CANCEL_MODEL_THREADS = max(1, min(2, _LOGICAL_CPUS // 4))

_model = WhisperModel(
    "large-v3-turbo",
    device="cpu",
    compute_type="int8",
    cpu_threads=_MAIN_MODEL_THREADS
)

_cancel_model = WhisperModel(
    "tiny",
    device="cpu",
    compute_type="int8",
    cpu_threads=_CANCEL_MODEL_THREADS,
)
_CANCEL_CHECK_PROMPT = "cancelar comando, cancela comando"

def _warmup_cancel_model() -> None:
    start = time.monotonic()
    try:
        rng = np.random.default_rng()
        dummy_audio = (rng.standard_normal(SAMPLE_RATE * 2) * 0.02).astype(np.float32)
        segments, _ = _cancel_model.transcribe(
            dummy_audio, language="pt", initial_prompt=_CANCEL_CHECK_PROMPT, beam_size=1
        )
        list(segments)
        cancel_log.info("%s modelo tiny pronto em %.2fs", _tag("AQUECIMENTO"), time.monotonic() - start)
    except Exception:
        log.exception("Falha ao aquecer o modelo de cancelamento (tiny)")

_warmup_cancel_model()

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

def _check_partial_for_cancel(audio_data: np.ndarray) -> bool:
    start = time.monotonic()
    segments, _ = _cancel_model.transcribe(
        audio_data,
        language="pt",
        condition_on_previous_text=False,
        initial_prompt=_CANCEL_CHECK_PROMPT,
        beam_size=1,
    )
    text = " ".join(segment.text for segment in segments).strip().lower()
    elapsed = time.monotonic() - start
    cancel_log.info(
        "%s %5.2fs processando %5.2fs de áudio │ texto: %r",
        _tag("PARCIAL"), elapsed, len(audio_data) / SAMPLE_RATE, text,
    )
    return is_cancel_command(text)

def listen_with_cancel_check(
    duration: float | None = None, use_command_context: bool = False
) -> tuple[str, bool]:
    time.sleep(0.1)
    _play_beep()

    record_start = time.monotonic()
    audio_data, was_cancelled_early = record_audio_with_cancel_check(_check_partial_for_cancel)
    record_elapsed = time.monotonic() - record_start

    if was_cancelled_early:
        cancel_log.info("%s confirmado após %5.2fs de gravação", _tag("CANCELADO"), record_elapsed)
        return "", True

    if audio_data is None:
        log.debug("Nenhuma fala detectada, %.2fs desde o início da escuta.", record_elapsed)
        return "", False

    transcribe_kwargs = {"language": "pt", "vad_filter": True}
    if use_command_context:
        transcribe_kwargs["initial_prompt"] = _INITIAL_PROMPT

    transcribe_start = time.monotonic()
    segments, _ = _model.transcribe(
        audio_data,
        beam_size=5,
        condition_on_previous_text=False,
        **transcribe_kwargs,
    )

    text = " ".join(segment.text for segment in segments).strip()
    transcribe_elapsed = time.monotonic() - transcribe_start
    text = _correct_known_mishearings(text)

    cancel_log.info(
        "%s %5.2fs gravação + %5.2fs transcrição final │ texto: %r",
        _tag("TRANSCRITO"), record_elapsed, transcribe_elapsed, text,
    )
    return text, False

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
