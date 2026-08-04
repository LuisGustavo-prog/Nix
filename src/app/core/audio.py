import time
import numpy as np
import sounddevice as sd
from app.core.logging_config import get_logger

log = get_logger("audio")

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
