import asyncio
import re
import subprocess
import threading
import unicodedata
import webbrowser

import uvicorn
import win32com.client
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from app.actions.apps import resolve_app_path
from app.config import BASE_DIR

ENV_PATH = BASE_DIR / ".env"
_PORT = 8001
_URL = f"http://127.0.0.1:{_PORT}"

_CARD_STYLE = """
    :root {
        --bg-main: #090d16;
        --bg-card: #0f172a;
        --border-color: #1e293b;
        --accent-purple: #8b5cf6;
        --accent-green: #10b981;
        --accent-red: #f43f5e;
        --text-main: #f8fafc;
        --text-muted: #64748b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        background-color: var(--bg-main);
        color: var(--text-main);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 24px;
    }
    .card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 32px;
        max-width: 380px;
        width: 100%;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        text-align: center;
    }
    .brand-logo {
        width: 48px;
        height: 48px;
        margin: 0 auto 16px;
        background: linear-gradient(135deg, var(--accent-purple), #6366f1);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        box-shadow: 0 0 15px rgba(139, 92, 246, 0.4);
    }
    h1 { font-size: 19px; font-weight: 700; margin-bottom: 8px; }
    p.subtitle { font-size: 14px; color: var(--text-muted); margin-bottom: 24px; }
    input[type=text] {
        width: 100%;
        padding: 12px 14px;
        background: var(--bg-main);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        color: var(--text-main);
        font-family: 'Inter', sans-serif;
        font-size: 15px;
        margin-bottom: 16px;
    }
    input[type=text]:focus { outline: none; border-color: var(--accent-purple); }
    button {
        width: 100%;
        padding: 12px 14px;
        background: var(--accent-purple);
        border: none;
        border-radius: 8px;
        color: var(--text-main);
        font-family: 'Inter', sans-serif;
        font-size: 15px;
        font-weight: 600;
        cursor: pointer;
    }
    button:hover { opacity: 0.9; }
    .error { color: var(--accent-red); font-size: 13px; margin-bottom: 16px; }
    .success-icon { color: var(--accent-green); font-size: 40px; margin-bottom: 12px; }
"""

_HTML_FORM = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nix — Configuração</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>{style}</style>
</head>
<body>
    <div class="card">
        <div class="brand-logo">⚡</div>
        <h1>{heading}</h1>
        <p class="subtitle">{subtitle}</p>
        {error_block}
        <form method="post" action="/set-username">
            <input type="text" name="nickname" placeholder="Seu nome ou apelido" autofocus required>
            <button type="submit">Salvar</button>
        </form>
    </div>
</body>
</html>"""

_HTML_SUCCESS = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nix — Configuração</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>{style}</style>
</head>
<body>
    <div class="card">
        <div class="success-icon">✓</div>
        <h1>Beleza, {raw_name}!</h1>
        <p class="subtitle">Nome salvo. Pode fechar essa aba e voltar pro Nix.</p>
    </div>
</body>
</html>"""


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

def _resolve_shortcut_target(lnk_path: str) -> str:
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(lnk_path)
    return shortcut.Targetpath

def _open_browser() -> None:
    opera_path = resolve_app_path("opera")

    if opera_path:
        if opera_path.lower().endswith(".lnk"):
            opera_path = _resolve_shortcut_target(opera_path)
        try:
            subprocess.Popen([opera_path, _URL])
            return
        except Exception:
            pass

    webbrowser.open(_URL)

def _run_server() -> None:
    uvicorn.run(app, host="127.0.0.1", port=_PORT, log_level="error")

def _start_capture() -> None:
    _state.raw_name = None
    _state.username = None
    _state.done.clear()
    threading.Thread(target=_run_server, daemon=True).start()
    _open_browser()

def capture_username_blocking(timeout: float | None = None) -> tuple[str, str]:
    _start_capture()
    _state.done.wait(timeout=timeout)
    return _state.raw_name or "usuario", _state.username or "usuario"

async def capture_username_async(timeout: float | None = None) -> tuple[str, str]:
    _start_capture()
    await asyncio.to_thread(_state.done.wait, timeout)
    return _state.raw_name or "usuario", _state.username or "usuario"
