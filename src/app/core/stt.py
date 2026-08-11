import time
import unicodedata
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from app.core.audio import record_audio_smart, record_audio_with_trigger_check, SAMPLE_RATE
from app.core.logging_config import get_logger, get_cancel_check_logger
from app.core.cancel_match import is_cancel_command
from app.core.finish_match import is_finish_command, strip_trailing_finish_phrase
from app.prompts.content import STT_KNOWN_MISHEARINGS
from app.prompts.system_prompts import STT_INITIAL_PROMPT, STT_TRIGGER_CHECK_PROMPT

log = get_logger("stt")
cancel_log = get_cancel_check_logger()

_TAG_WIDTH = 11

def _tag(label: str) -> str:
    return f"[{label:<{_TAG_WIDTH}}]"

def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)

_KNOWN_CORRECTIONS_NORMALIZED = {_nfc(key): value for key, value in STT_KNOWN_MISHEARINGS.items()}

_model = WhisperModel(
    "large-v3-turbo",
    device="cpu",
    compute_type="int8",
)

_trigger_model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8",
)

def _warmup_trigger_model() -> None:
    start = time.monotonic()
    try:
        rng = np.random.default_rng()
        dummy_audio = (rng.standard_normal(SAMPLE_RATE * 2) * 0.02).astype(np.float32)
        segments, _ = _trigger_model.transcribe(
            dummy_audio, language="pt", initial_prompt=STT_TRIGGER_CHECK_PROMPT, beam_size=1,
            no_repeat_ngram_size=3, repetition_penalty=1.3,
        )
        list(segments)
        cancel_log.info("%s modelo base pronto em %.2fs", _tag("AQUECIMENTO"), time.monotonic() - start)
    except Exception:
        log.exception("Falha ao aquecer o modelo de checagem de gatilhos (base)")

_warmup_trigger_model()

def _play_beep(duration: float = 0.2, frequency: int = 880) -> None:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    tone = np.sin(frequency * t * 2 * np.pi) * 0.8
    sd.play(tone.astype(np.float32), SAMPLE_RATE)
    sd.wait()

def _correct_known_mishearings(text: str) -> str:
    words = text.split()
    corrected = [
        _KNOWN_CORRECTIONS_NORMALIZED.get(_nfc(word.lower().strip(",.!?")), word)
        for word in words
    ]
    return " ".join(corrected)

def _check_partial_for_trigger(audio_data: np.ndarray, allow_finish: bool) -> str | None:
    start = time.monotonic()
    segments, _ = _trigger_model.transcribe(
        audio_data,
        language="pt",
        condition_on_previous_text=False,
        initial_prompt=STT_TRIGGER_CHECK_PROMPT,
        beam_size=1,
        no_repeat_ngram_size=3,
        repetition_penalty=1.3,
    )
    text = " ".join(segment.text for segment in segments).strip().lower()
    elapsed = time.monotonic() - start
    cancel_log.info(
        "%s %5.2fs processando %5.2fs de áudio │ texto: %r",
        _tag("PARCIAL"), elapsed, len(audio_data) / SAMPLE_RATE, text,
    )

    if is_cancel_command(text):
        return "cancel"
    if allow_finish and is_finish_command(text):
        return "finish"
    return None

def _play_confirmation_beep() -> None:
    beep_duration = 0.15
    gap_duration = 0.08
    frequency = 1400

    def _tone(duration: float) -> np.ndarray:
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
        return np.sin(frequency * t * 2 * np.pi) * 0.8

    silence = np.zeros(int(SAMPLE_RATE * gap_duration), dtype=np.float32)
    waveform = np.concatenate([_tone(beep_duration), silence, _tone(beep_duration)]).astype(np.float32)

    sd.play(waveform, SAMPLE_RATE)
    sd.wait()

def listen_with_cancel_check(
    duration: float | None = None,
    use_command_context: bool = False,
    enable_finish_phrase: bool = False,
) -> tuple[str, bool]:
    time.sleep(0.1)
    _play_beep()

    record_start = time.monotonic()
    audio_data, trigger = record_audio_with_trigger_check(
        lambda snapshot: _check_partial_for_trigger(snapshot, allow_finish=enable_finish_phrase)
    )
    record_elapsed = time.monotonic() - record_start

    if trigger == "cancel":
        cancel_log.info("%s confirmado após %5.2fs de gravação", _tag("CANCELADO"), record_elapsed)
        return "", True

    if trigger == "finish":
        _play_confirmation_beep()
        cancel_log.info("%s bipe de confirmação tocado", _tag("FINALIZAR"))

    if audio_data is None:
        log.debug("Nenhuma fala detectada, %.2fs desde o início da escuta.", record_elapsed)
        return "", False

    transcribe_kwargs = {"language": "pt", "vad_filter": True}
    if use_command_context:
        transcribe_kwargs["initial_prompt"] = STT_INITIAL_PROMPT

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

    if trigger == "finish":
        text = strip_trailing_finish_phrase(text)

    cancel_log.info(
        "%s %5.2fs gravação + %5.2fs transcrição final │ texto: %r (gatilho: %s)",
        _tag("TRANSCRITO"), record_elapsed, transcribe_elapsed, text, trigger or "timeout",
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
        transcribe_kwargs["initial_prompt"] = STT_INITIAL_PROMPT

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
