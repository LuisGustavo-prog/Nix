import time
import numpy as np
import sounddevice as sd
from app.core.logging_config import get_logger

log = get_logger("audio")

SAMPLE_RATE = 16000

def record_audio_smart(
    silence_duration_to_stop: float = 2.0,  # Dá 2s de pausa na fala antes de parar
    max_wait_seconds: float = 8.0,          # Espera 8s para começares a falar
    max_speech_seconds: float = 20.0,       # Tempo máximo total do comando
) -> np.ndarray | None:
    chunk_duration = 0.1
    chunk_samples = int(SAMPLE_RATE * chunk_duration)

    audio_chunks = []
    has_started_speaking = False
    silence_timer = 0.0
    total_timer = 0.0

    # Limiar ultra-sensível fixo para não ignorar voz baixa
    silence_threshold = 0.003  

    log.debug("Aguardando fala...")

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        while True:
            chunk, _ = stream.read(chunk_samples)
            audio_chunks.append(chunk)

            # Volume médio do bloco atual
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

            # 1. Parar após detectar fala + 2s de silêncio contínuo
            if has_started_speaking and silence_timer >= silence_duration_to_stop:
                log.debug("Fim de fala detectado.")
                break

            # 2. Se ninguém falar nada em 8s, cancela
            if not has_started_speaking and total_timer >= max_wait_seconds:
                log.info("Nenhuma fala detectada dentro de %ss.", max_wait_seconds)
                return None

            # 3. Trava de segurança para não gravar infinitamente
            if has_started_speaking and total_timer >= max_speech_seconds:
                log.debug("Tempo limite de fala atingido.")
                break

    if not has_started_speaking or not audio_chunks:
        return None

    return np.concatenate(audio_chunks, axis=0).flatten()
