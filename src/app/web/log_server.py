import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

from app.core.paths import LOGS_DIR

app = FastAPI()

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

LOG_FILES = {
    "app": LOGS_DIR / "nix.log",
    "commands": LOGS_DIR / "comandos.log",
    "cancel": LOGS_DIR / "cancelamento.log",
}

_LINE_SEP = "\u241E"
_INITIAL_LINES = 200


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _encode_lines(lines: list[str]) -> str:
    return _LINE_SEP.join(_escape_html(line) for line in lines)


def _read_last_lines(file_path: Path, max_lines: int = _INITIAL_LINES) -> list[str]:
    if not file_path.exists():
        return []
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return [f"[erro ao ler o log: {e}]"]
    return [line for line in text.splitlines()][-max_lines:]


@app.get("/stream/{log_type}")
async def stream_log(log_type: str):
    async def event_generator():
        log_file = LOG_FILES.get(log_type)
        if not log_file:
            yield "event: error\ndata: Tipo de log inválido\n\n"
            return

        while not log_file.exists():
            yield "event: waiting\ndata: aguardando o arquivo de log ser criado...\n\n"
            await asyncio.sleep(1)

        initial_lines = _read_last_lines(log_file)
        yield f"event: init\ndata: {_encode_lines(initial_lines)}\n\n"

        try:
            offset = log_file.stat().st_size
        except FileNotFoundError:
            offset = 0

        while True:
            await asyncio.sleep(0.5)

            try:
                current_size = log_file.stat().st_size
            except FileNotFoundError:
                continue

            if current_size < offset:
                offset = 0
                yield "event: rotated\ndata: log rotacionado\n\n"
                continue

            if current_size == offset:
                continue

            try:
                with log_file.open("r", encoding="utf-8", errors="ignore") as f:
                    f.seek(offset)
                    new_content = f.read()
                    offset = f.tell()
            except Exception:
                continue

            new_lines = [line for line in new_content.splitlines() if line.strip() != ""]
            if not new_lines:
                continue

            yield f"event: append\ndata: {_encode_lines(new_lines)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    html_content = (TEMPLATES_DIR / "log_dashboard.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html_content)
