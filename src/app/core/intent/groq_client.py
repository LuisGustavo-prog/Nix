from groq import AsyncGroq
from app.config import settings

client = AsyncGroq(
    api_key=settings.GROQ_API_KEY,
    max_retries=0,
    timeout=8.0,
)

TOOL_CALLING_MODEL = "llama-3.3-70b-versatile"
CORRECTION_MODEL = "llama-3.1-8b-instant"

LOW_TOKEN_BUFFER = 300
RATE_LIMIT_COOLDOWN_SECONDS = 60.0

def read_remaining_tokens(headers) -> int | None:
    raw_value = headers.get("x-ratelimit-remaining-tokens")
    if raw_value is None:
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None
