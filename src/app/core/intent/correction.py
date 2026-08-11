import time
from groq import RateLimitError
from app.core.intent.groq_client import (
    CORRECTION_MODEL,
    LOW_TOKEN_BUFFER,
    RATE_LIMIT_COOLDOWN_SECONDS,
    client,
    read_remaining_tokens,
)
from app.prompts.system_prompts import CORRECTION_SYSTEM_PROMPT

_cooldown_until = 0.0
_tokens_remaining: int | None = None

async def correct_transcription(user_text: str) -> str:
    global _cooldown_until, _tokens_remaining

    if time.monotonic() < _cooldown_until:
        return user_text

    if _tokens_remaining is not None and _tokens_remaining < LOW_TOKEN_BUFFER:
        return user_text

    try:
        raw_response = await client.chat.completions.with_raw_response.create(
            model=CORRECTION_MODEL,
            messages=[
                {"role": "system", "content": CORRECTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            max_tokens=60,
            temperature=0,
        )
        remaining = read_remaining_tokens(raw_response.headers)
        if remaining is not None:
            _tokens_remaining = remaining

        response = await raw_response.parse()
        corrected = response.choices[0].message.content
        return corrected.strip() if corrected else user_text
    except RateLimitError:
        _cooldown_until = time.monotonic() + RATE_LIMIT_COOLDOWN_SECONDS
        return user_text
    except Exception:
        return user_text
