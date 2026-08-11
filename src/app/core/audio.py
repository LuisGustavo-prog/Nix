import time
import threading
import numpy as np
import sounddevice as sd
from app.core.logging_config import get_logger, get_cancel_check_logger

log = get_logger("audio")
cancel_log = get_cancel_check_logger()
_TAG_WIDTH = 11

def _tag(label: str) -> str:
    return f"[{label:<{_TAG_WIDTH}}]"

SAMPLE_RATE = 16000

def record_audio_smart(
    silence_duration_to_stop: float = 2.0, 
    max_wait_seconds: float = 8.0,
    max_speech_seconds: float = 20.0,
) -> np.ndarray | None:
    chunk_duration = 0.1
    chunk_samples = int(SAMPLE_RATE * chunk_duration)

    audio_chunks = []
    has_started_speaking = False
    silence_timer = 0.0
    total_timer = 0.0

    silence_threshold = 0.003  

    log.debug("Aguardando fala...")

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        while True:
            chunk, _ = stream.read(chunk_samples)
            audio_chunks.append(chunk)

            rms = np.sqrt(np.mean(chunk**2))
            total_timer += chunk_duration

            if rms > silence_threshold:
                if not has_started_speaking:
                    has_started_speaking = True
                    log.debug("Fala detectada! Gravando...")
                silence_timer = 0.0
            else:
                if has_started_speaking:
                    silence_timer += chunk_duration

            if has_started_speaking and silence_timer >= silence_duration_to_stop:
                log.debug("Fim de fala detectado.")
                break

            if not has_started_speaking and total_timer >= max_wait_seconds:
                log.info("Nenhuma fala detectada dentro de %ss.", max_wait_seconds)
                return None

            if has_started_speaking and total_timer >= max_speech_seconds:
                log.debug("Tempo limite de fala atingido.")
                break

    if not has_started_speaking or not audio_chunks:
        return None

    return np.concatenate(audio_chunks, axis=0).flatten()

def record_audio_with_trigger_check(
    on_partial_check,
    silence_duration_to_stop: float = 2.0,
    max_wait_seconds: float = 8.0,
    max_speech_seconds: float = 20.0,
    check_interval_seconds: float = 0.8,
    pause_check_threshold: float = 0.4,
) -> tuple[np.ndarray | None, str | None]:
    chunk_duration = 0.1
    chunk_samples = int(SAMPLE_RATE * chunk_duration)

    audio_chunks = []
    has_started_speaking = False
    silence_timer = 0.0
    total_timer = 0.0
    time_since_last_check = 0.0
    already_checked_this_pause = False
    checks_dispatched = 0

    silence_threshold = 0.003

    _trigger_check_window_seconds = 4.0
    trigger_check_window_chunks = int(_trigger_check_window_seconds / chunk_duration)

    function_start = time.monotonic()
    speech_started_at = None

    trigger_event = threading.Event()
    detected_trigger: list[str | None] = [None]
    check_running = threading.Event()

    def _run_check(audio_snapshot: np.ndarray, dispatched_at: float, check_number: int) -> None:
        try:
            result = on_partial_check(audio_snapshot)
            if result:
                detected_trigger[0] = result
                trigger_event.set()
        except Exception:
            log.exception("Falha ao checar gatilho parcial, ignorando.")
        finally:
            cancel_log.info(
                "%s #%-3d disparada em %5.2fs desde a fala │ resultado em %5.2fs",
                _tag("CHECK"),
                check_number,
                dispatched_at - (speech_started_at or function_start),
                time.monotonic() - dispatched_at,
            )
            check_running.clear()

    log.debug("Aguardando fala (com checagem de gatilhos)...")

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        while True:
            chunk, _ = stream.read(chunk_samples)
            audio_chunks.append(chunk)

            if trigger_event.is_set():
                elapsed = time.monotonic() - (speech_started_at or function_start)
                cancel_log.info(
                    "%s gatilho=%s, %5.2fs desde o início da fala",
                    _tag("GATILHO"), detected_trigger[0], elapsed,
                )
                return np.concatenate(audio_chunks, axis=0).flatten(), detected_trigger[0]

            rms = np.sqrt(np.mean(chunk**2))
            total_timer += chunk_duration

            if rms > silence_threshold:
                if not has_started_speaking:
                    has_started_speaking = True
                    speech_started_at = time.monotonic()
                    log.debug("Fala detectada! Gravando...")
                silence_timer = 0.0
                time_since_last_check += chunk_duration
                already_checked_this_pause = False
            else:
                if has_started_speaking:
                    silence_timer += chunk_duration

            should_check = False
            if has_started_speaking and not check_running.is_set():
                if time_since_last_check >= check_interval_seconds:
                    should_check = True
                elif silence_timer >= pause_check_threshold and not already_checked_this_pause:
                    should_check = True
                    already_checked_this_pause = True

            if should_check:
                time_since_last_check = 0.0
                check_running.set()
                checks_dispatched += 1
                snapshot = np.concatenate(audio_chunks[-trigger_check_window_chunks:], axis=0).flatten()
                threading.Thread(
                    target=_run_check,
                    args=(snapshot, time.monotonic(), checks_dispatched),
                    daemon=True,
                ).start()

            if has_started_speaking and silence_timer >= silence_duration_to_stop and not check_running.is_set():
                log.debug("Fim de fala detectado.")
                break

            if not has_started_speaking and total_timer >= max_wait_seconds:
                log.info("Nenhuma fala detectada dentro de %ss.", max_wait_seconds)
                return None, None

            if has_started_speaking and total_timer >= max_speech_seconds:
                log.debug("Tempo limite de fala atingido.")
                break

    if not has_started_speaking or not audio_chunks:
        return None, None

    cancel_log.info(
        "%s %d checagens parciais │ %5.2fs desde o início da fala",
        _tag("FINALIZADO"), checks_dispatched, time.monotonic() - (speech_started_at or function_start),
    )
    return np.concatenate(audio_chunks, axis=0).flatten(), None
