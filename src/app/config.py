import os
from dotenv import load_dotenv
from app.core.paths import ENV_FILE, PROJECT_ROOT

BASE_DIR = PROJECT_ROOT 

load_dotenv(ENV_FILE)

class ConfigError(Exception):
    pass

def _get_required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ConfigError(
            f"Variável obrigatória '{key}' não encontrada no .env. "
            f"Confira o .env.example."
        )
    return value

def _get_optional(key: str, default: str = "") -> str:
    return os.getenv(key, default)
class Settings:
    GROQ_API_KEY: str = _get_required("GROQ_API_KEY")
    YOUTUBE_API_KEY: str = _get_optional("YOUTUBE_API_KEY")
    NIX_USERNAME: str = _get_optional("NIX_USERNAME", "")

    def require(self, *keys: str) -> None:
        missing = [key for key in keys if not getattr(self, key, None)]
        if missing:
            raise ConfigError(
                f"As variáveis {', '.join(missing)} são necessárias para essa "
                f"funcionalidade, mas não foram encontradas no .env. "
                f"Confira o .env.example."
            )

settings = Settings()
