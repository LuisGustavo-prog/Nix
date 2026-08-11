import os
import numpy as np
import sounddevice as sd
import openwakeword.utils
from openwakeword.model import Model

WAKE_WORD_MODEL = "hey_jarvis"
DETECTION_THRESHOLD = 0.6
SAMPLE_RATE = 16000
CHUNK_SIZE = 1280  

def _ensure_models_downloaded(model_name: str) -> None:
    models_dir = os.path.join(
        os.path.dirname(openwakeword.utils.__file__), "resources", "models"
    )

    model_exists = os.path.isdir(models_dir) and any(
        f.startswith(model_name) for f in os.listdir(models_dir)
    )

    if not model_exists:
        print(f"Modelo '{model_name}' não encontrado. Baixando automaticamente...")
        openwakeword.utils.download_models()
        print("Download concluído.")
class WakeWordDetector:
    def __init__(self, model_name: str = WAKE_WORD_MODEL, threshold: float = DETECTION_THRESHOLD):
        _ensure_models_downloaded(model_name)

        self.model_name = model_name
        self.threshold = threshold
        self.model = Model(wakeword_models=[model_name])

    def listen_for_wake_word(self) -> None:
        print(f"Aguardando a palavra de ativação ('{self.model_name}')...")

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=CHUNK_SIZE,
        ) as stream:
            while True:
                audio_chunk, _ = stream.read(CHUNK_SIZE)
                audio_data = np.frombuffer(audio_chunk, dtype=np.int16)

                prediction = self.model.predict(audio_data)
                score = prediction[self.model_name]

                if score >= self.threshold:
                    print(f"Wake word detectada! (score: {score:.2f})")
                    self.model.reset()
                    return
