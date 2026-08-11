import asyncio
import re
import threading
import unicodedata
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from app.config import BASE_DIR
from app.core.utils.browser_launch import open_url_with_fallback

ENV_PATH = BASE_DIR / ".env"
_PORT = 8001
_URL = f"http://127.0.0.1:{_PORT}"

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_CARD_STYLE = (TEMPLATES_DIR / "shared_card.css").read_text(encoding="utf-8")
_HTML_FORM = (TEMPLATES_DIR / "username_form.html").read_text(encoding="utf-8")
_HTML_SUCCESS = (TEMPLATES_DIR / "username_success.html").read_text(encoding="utf-8")


def sanitize_username(raw: str) -> str:
    normalized = unicodedata.normalize("NFKD", raw)
    without_accents = "".join(c for c in normalized if not unicodedata.combining(c))
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", without_accents.lower().replace(" ", "_"))
    return cleaned


def _read_env_lines() -> list[str]:
    if ENV_PATH.exists():
        return ENV_PATH.read_text(encoding="utf-8").splitlines()
    return []


def get_current_username() -> str | None:
    for line in _read_env_lines():
        if line.startswith("NIX_USERNAME="):
            value = line.split("=", 1)[1].strip()
            return value or None
    return None


def save_username_to_env(username: str) -> None:
    lines = _read_env_lines()
    new_line = f"NIX_USERNAME={username}"
    for i, line in enumerate(lines):
        if line.startswith("NIX_USERNAME="):
            lines[i] = new_line
            break
    else:
        lines.append(new_line)
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


class _CaptureState:
    def __init__(self) -> None:
        self.raw_name: str | None = None
        self.username: str | None = None
        self.done = threading.Event()


_state = _CaptureState()
app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def get_form() -> str:
    current = get_current_username()
    subtitle = (
        f"Já existe um nome configurado ('{current}'). Digite um novo pra trocar."
        if current
        else "Ainda não te conheço. Como você quer ser chamado?"
    )
    return _HTML_FORM.format(
        style=_CARD_STYLE,
        heading="Configuração do Nix",
        subtitle=subtitle,
        error_block="",
    )


@app.post("/set-username", response_class=HTMLResponse)
async def post_username(nickname: str = Form(...)) -> str:
    raw_name = nickname.strip()

    if not raw_name:
        return _HTML_FORM.format(
            style=_CARD_STYLE,
            heading="Configuração do Nix",
            subtitle="Como você quer ser chamado?",
            error_block='<p class="error">Digite um nome, por favor.</p>',
        )

    username = sanitize_username(raw_name)
    if not username:
        return _HTML_FORM.format(
            style=_CARD_STYLE,
            heading="Configuração do Nix",
            subtitle="Como você quer ser chamado?",
            error_block='<p class="error">Esse nome não tem nenhuma letra ou número válido, tenta outro.</p>',
        )

    save_username_to_env(username)

    _state.raw_name = raw_name
    _state.username = username
    _state.done.set()

    return _HTML_SUCCESS.format(style=_CARD_STYLE, raw_name=raw_name)


def _run_server() -> None:
    uvicorn.run(app, host="127.0.0.1", port=_PORT, log_level="error")


def _start_capture() -> None:
    _state.raw_name = None
    _state.username = None
    _state.done.clear()
    threading.Thread(target=_run_server, daemon=True).start()
    open_url_with_fallback(_URL)


def capture_username_blocking(timeout: float | None = None) -> tuple[str, str]:
    _start_capture()
    _state.done.wait(timeout=timeout)
    return _state.raw_name or "usuario", _state.username or "usuario"


async def capture_username_async(timeout: float | None = None) -> tuple[str, str]:
    _start_capture()
    await asyncio.to_thread(_state.done.wait, timeout)
    return _state.raw_name or "usuario", _state.username or "usuario"
