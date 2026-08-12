import threading
from pathlib import Path
import uvicorn
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from app.config import BASE_DIR
from app.core.utils.browser_launch import open_url_with_fallback

ENV_PATH = BASE_DIR / ".env"
ENV_KEY = "NIX_EXTERNAL_CONSOLE"
_PORT = 8002
_URL = f"http://127.0.0.1:{_PORT}"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_CARD_STYLE = (TEMPLATES_DIR / "shared_card.css").read_text(encoding="utf-8")
_HTML_FORM = (TEMPLATES_DIR / "console_choice_form.html").read_text(encoding="utf-8")
_HTML_SUCCESS = (TEMPLATES_DIR / "console_choice_success.html").read_text(encoding="utf-8")
_CHOICE_LABELS = {
    True: "A Nix vai abrir numa janela de cmd separada",
    False: "A Nix vai continuar rodando aqui, no terminal do VSCode",
}

def _read_env_lines() -> list[str]:
    if ENV_PATH.exists():
        return ENV_PATH.read_text(encoding="utf-8").splitlines()
    return []

def get_current_console_choice() -> bool | None:
    for line in _read_env_lines():
        if line.startswith(f"{ENV_KEY}="):
            value = line.split("=", 1)[1].strip().lower()
            if value in ("1", "true", "yes"):
                return True
            if value in ("0", "false", "no"):
                return False
    return None

def save_console_choice_to_env(use_external_console: bool) -> None:
    lines = _read_env_lines()
    new_line = f"{ENV_KEY}={'true' if use_external_console else 'false'}"
    for i, line in enumerate(lines):
        if line.startswith(f"{ENV_KEY}="):
            lines[i] = new_line
            break
    else:
        lines.append(new_line)
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

class _CaptureState:
    def __init__(self) -> None:
        self.choice: bool | None = None
        self.done = threading.Event()

_state = _CaptureState()
app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def get_form() -> str:
    return _HTML_FORM.format(style=_CARD_STYLE)

@app.post("/choose", response_class=HTMLResponse)
async def post_choice(choice: str = Form(...)) -> str:
    use_external_console = choice == "cmd"
    save_console_choice_to_env(use_external_console)

    _state.choice = use_external_console
    _state.done.set()

    return _HTML_SUCCESS.format(style=_CARD_STYLE, choice_label=_CHOICE_LABELS[use_external_console])

def _run_server() -> None:
    uvicorn.run(app, host="127.0.0.1", port=_PORT, log_level="error")

def _start_capture() -> None:
    _state.choice = None
    _state.done.clear()
    threading.Thread(target=_run_server, daemon=True).start()
    open_url_with_fallback(_URL)

def capture_console_choice_blocking(timeout: float | None = None) -> bool:
    _start_capture()
    _state.done.wait(timeout=timeout)
    if _state.choice is None:
        return False
    return _state.choice
