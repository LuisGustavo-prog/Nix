import re
import time
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from app.core.audio import record_audio_smart, record_audio_with_cancel_check, SAMPLE_RATE
from app.core.logging_config import get_logger, get_cancel_check_logger

log = get_logger("stt")
cancel_log = get_cancel_check_logger()

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

# Modelo bem pequeno, só pra checar rapidamente se o usuário disse "cancelar
# comando" NO MEIO da gravação. Testamos o 'base' (mais preciso em teoria),
# mas na prática teve uma checagem que levou quase 4s, muito mais lento e
# imprevisível que o 'tiny' (sempre entre 0.3-0.5s nos testes). Voltando pro
# 'tiny', mas agora com um prompt de contexto focado, pra tentar melhorar a
# precisão sem abrir mão da velocidade/previsibilidade.
_cancel_model = WhisperModel(
    "tiny",
    device="cpu",
    compute_type="int8",
    cpu_threads=2,
)

# Contexto curto, só sobre a frase que realmente importa aqui, pra enviesar
# o modelo pequeno a reconhecer "cancelar comando" quando ela realmente for
# dita, em vez de tentar decifrar a frase inteira sem nenhuma pista.
_CANCEL_CHECK_PROMPT = "cancelar comando, cancela comando"

# Mesmo padrão usado no intent.py pra detectar o cancelamento na
# transcrição final. Duplicado aqui de propósito (evita import cruzado
# entre stt.py e intent.py), mas se mudar a frase de cancelamento, lembra
# de atualizar os dois lugares.
_CANCEL_PATTERN = re.compile(r"\bcancela(?:r)?\s+(?:o\s+)?comandos?\b", re.IGNORECASE)

def _warmup_cancel_model() -> None:
    """
    Roda uma transcrição de "aquecimento" assim que o Nix sobe, pra forçar
    o modelo tiny a passar pelo processo real de decodificação (não só o
    carregamento dos pesos) antes da primeira checagem de verdade.

    Importante: usamos RUÍDO, não silêncio puro. Testamos com silêncio antes
    e mesmo assim a primeira checagem real ficou bem mais lenta que as
    seguintes (~4s contra ~0.3s); a suspeita é que áudio silencioso faz o
    modelo sair cedo do processo de decodificação (por não ter "fala" pra
    decodificar), sem exercitar o caminho completo que uma fala de verdade
    percorre.
    """
    start = time.monotonic()
    try:
        rng = np.random.default_rng()
        dummy_audio = (rng.standard_normal(SAMPLE_RATE * 2) * 0.02).astype(np.float32)
        segments, _ = _cancel_model.transcribe(
            dummy_audio, language="pt", initial_prompt=_CANCEL_CHECK_PROMPT, beam_size=1
        )
        list(segments)
        cancel_log.info("Modelo de cancelamento (tiny) aquecido em %.2fs", time.monotonic() - start)
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
        "Checagem parcial (tiny): %.2fs de processamento pra %.2fs de áudio | texto: %r",
        elapsed, len(audio_data) / SAMPLE_RATE, text,
    )
    return bool(_CANCEL_PATTERN.search(text))


def listen_with_cancel_check(
    duration: float | None = None, use_command_context: bool = False
) -> tuple[str, bool]:
    """
    Igual ao listen(), mas verifica cancelamento durante a gravação (não só
    depois de transcrever tudo). Retorna (texto, foi_cancelado).
    Se foi_cancelado for True, o texto vem vazio e o comando nem chega a
    ser transcrito pelo modelo grande.
    """
    time.sleep(0.1)
    _play_beep()

    record_start = time.monotonic()
    audio_data, was_cancelled_early = record_audio_with_cancel_check(_check_partial_for_cancel)
    record_elapsed = time.monotonic() - record_start

    if was_cancelled_early:
        cancel_log.info("Cancelado durante a gravação, %.2fs desde o início da escuta.", record_elapsed)
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
        "Não cancelado: %.2fs de gravação + %.2fs de transcrição final (modelo grande) | texto: %r",
        record_elapsed, transcribe_elapsed, text,
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