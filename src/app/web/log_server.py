import asyncio
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = BASE_DIR / "logs"

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
    html_content = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Nix Core System Logs</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">

        <style>
            :root {
                --bg-main: #090d16;
                --bg-card: #0f172a;
                --bg-terminal: #030712;
                --bg-input: #0b1120;
                --border-color: #1e293b;
                --accent-purple: #8b5cf6;
                --accent-green: #10b981;
                --accent-blue: #3b82f6;
                --accent-red: #f43f5e;
                --accent-amber: #f59e0b;
                --text-main: #f8fafc;
                --text-muted: #64748b;
            }

            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }

            body {
                background-color: var(--bg-main);
                color: var(--text-main);
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                padding: 24px;
                min-height: 100vh;
            }

            header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 24px;
                padding-bottom: 16px;
                border-bottom: 1px solid var(--border-color);
            }

            .brand {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .brand-logo {
                width: 38px;
                height: 38px;
                background: linear-gradient(135deg, var(--accent-purple), #6366f1);
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
                font-size: 20px;
                box-shadow: 0 0 15px rgba(139, 92, 246, 0.4);
            }

            .brand-title h1 {
                font-size: 20px;
                font-weight: 700;
                letter-spacing: -0.5px;
            }

            .brand-title p {
                font-size: 13px;
                color: var(--text-muted);
            }

            .status-badge {
                display: flex;
                align-items: center;
                gap: 8px;
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.2);
                color: var(--accent-green);
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
            }

            .pulse-dot {
                width: 8px;
                height: 8px;
                background-color: var(--accent-green);
                border-radius: 50%;
                box-shadow: 0 0 8px var(--accent-green);
                animation: pulse 1.5s infinite;
            }

            @keyframes pulse {
                0% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.4; transform: scale(0.8); }
                100% { opacity: 1; transform: scale(1); }
            }

            .grid-container {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
                height: calc(100vh - 120px);
            }

            @media (max-width: 1200px) {
                .grid-container {
                    grid-template-columns: 1fr;
                    height: auto;
                }
                .terminal { height: 340px; }
            }

            .card {
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
                transition: border-color 0.2s ease;
            }

            .card:hover {
                border-color: rgba(255, 255, 255, 0.15);
            }

            .card-header {
                padding: 14px 16px;
                background: rgba(15, 23, 42, 0.8);
                border-bottom: 1px solid var(--border-color);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .card-title {
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 14px;
                font-weight: 600;
            }

            .card-title .icon {
                width: 10px;
                height: 10px;
                border-radius: 50%;
                flex-shrink: 0;
            }

            .main-icon { background: var(--accent-green); box-shadow: 0 0 8px var(--accent-green); }
            .cmd-icon { background: var(--accent-blue); box-shadow: 0 0 8px var(--accent-blue); }
            .cancel-icon { background: var(--accent-red); box-shadow: 0 0 8px var(--accent-red); }

            .status-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: var(--text-muted);
                transition: background 0.2s ease;
            }
            .status-dot.status-live { background: var(--accent-green); box-shadow: 0 0 6px var(--accent-green); }
            .status-dot.status-error { background: var(--accent-red); box-shadow: 0 0 6px var(--accent-red); animation: pulse 1.2s infinite; }

            .file-tag {
                font-family: 'Fira Code', monospace;
                font-size: 11px;
                color: var(--text-muted);
                background: rgba(255, 255, 255, 0.05);
                padding: 3px 8px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }

            .card-controls {
                display: flex;
                gap: 8px;
                padding: 10px 16px;
                border-bottom: 1px solid var(--border-color);
                background: rgba(3, 7, 18, 0.4);
            }

            .card-controls input[type="text"] {
                flex: 1;
                min-width: 0;
                background: var(--bg-input);
                border: 1px solid var(--border-color);
                border-radius: 6px;
                color: var(--text-main);
                font-family: 'Fira Code', monospace;
                font-size: 12px;
                padding: 6px 10px;
            }

            .card-controls input[type="text"]:focus {
                outline: none;
                border-color: var(--accent-purple);
            }

            .card-controls button {
                background: var(--bg-input);
                border: 1px solid var(--border-color);
                border-radius: 6px;
                color: var(--text-muted);
                font-family: 'Inter', sans-serif;
                font-size: 12px;
                font-weight: 600;
                padding: 6px 10px;
                cursor: pointer;
                white-space: nowrap;
            }

            .card-controls button:hover {
                border-color: rgba(255, 255, 255, 0.2);
                color: var(--text-main);
            }

            .card-controls button.following {
                color: var(--accent-green);
                border-color: rgba(16, 185, 129, 0.3);
            }

            .terminal {
                flex: 1;
                background-color: var(--bg-terminal);
                padding: 12px 16px;
                font-family: 'Fira Code', monospace;
                font-size: 12.5px;
                line-height: 1.6;
                overflow-y: auto;
                color: #cbd5e1;
                white-space: pre-wrap;
                word-break: break-all;
            }

            .terminal::-webkit-scrollbar { width: 6px; }
            .terminal::-webkit-scrollbar-track { background: var(--bg-terminal); }
            .terminal::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
            .terminal::-webkit-scrollbar-thumb:hover { background: #334155; }

            .log-line { padding: 1px 0; }
            .log-line.hidden-by-filter { display: none; }

            .main-terminal .log-line { color: #a7f3d0; }
            .commands-terminal .log-line { color: #bae6fd; }
            .cancel-terminal .log-line { color: #fecdd3; }

            .log-line.lvl-warn {
                color: #fde68a;
                border-left: 3px solid var(--accent-amber);
                padding-left: 8px;
                margin-left: -8px;
            }
            .log-line.lvl-error {
                color: #fecaca;
                border-left: 3px solid var(--accent-red);
                padding-left: 8px;
                margin-left: -8px;
            }
            .log-line.lvl-crit {
                color: #fecaca;
                background: rgba(244, 63, 94, 0.12);
                border-left: 3px solid var(--accent-red);
                padding-left: 8px;
                margin-left: -8px;
                font-weight: 600;
            }
            .log-line.lvl-debug { opacity: 0.55; }

            .empty-hint {
                color: var(--text-muted);
                font-style: italic;
            }

            .line-count {
                font-size: 11px;
                color: var(--text-muted);
                padding: 6px 16px 0;
            }
        </style>
    </head>
    <body>

        <header>
            <div class="brand">
                <div class="brand-logo">⚡</div>
                <div class="brand-title">
                    <h1>Nix Dashboard</h1>
                    <p>Monitoramento de logs de sistema e comandos de voz</p>
                </div>
            </div>
            <div class="status-badge">
                <div class="pulse-dot"></div>
                <span>LIVE STREAMING</span>
            </div>
        </header>

        <div class="grid-container">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">
                        <div class="icon main-icon"></div>
                        <span>Main System Log</span>
                        <div class="status-dot" id="main-status-dot"></div>
                    </div>
                    <span class="file-tag">nix.log</span>
                </div>
                <div class="card-controls">
                    <input type="text" id="main-search" placeholder="Filtrar...">
                    <button id="main-follow-btn"></button>
                    <button id="main-clear-btn">Limpar</button>
                </div>
                <div class="line-count" id="main-count">0 linhas</div>
                <div id="main-log-box" class="terminal main-terminal"><span class="empty-hint">Aguardando dados...</span></div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-title">
                        <div class="icon cmd-icon"></div>
                        <span>Commands Log</span>
                        <div class="status-dot" id="commands-status-dot"></div>
                    </div>
                    <span class="file-tag">comandos.log</span>
                </div>
                <div class="card-controls">
                    <input type="text" id="commands-search" placeholder="Filtrar...">
                    <button id="commands-follow-btn"></button>
                    <button id="commands-clear-btn">Limpar</button>
                </div>
                <div class="line-count" id="commands-count">0 linhas</div>
                <div id="commands-log-box" class="terminal commands-terminal"><span class="empty-hint">Aguardando dados...</span></div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-title">
                        <div class="icon cancel-icon"></div>
                        <span>Cancel Check Log</span>
                        <div class="status-dot" id="cancel-status-dot"></div>
                    </div>
                    <span class="file-tag">cancelamento.log</span>
                </div>
                <div class="card-controls">
                    <input type="text" id="cancel-search" placeholder="Filtrar...">
                    <button id="cancel-follow-btn"></button>
                    <button id="cancel-clear-btn">Limpar</button>
                </div>
                <div class="line-count" id="cancel-count">0 linhas</div>
                <div id="cancel-log-box" class="terminal cancel-terminal"><span class="empty-hint">Aguardando dados...</span></div>
            </div>
        </div>

        <script>
            const LINE_SEP = '\\u241E';
            const MAX_LINES = 1500;

            function levelClass(panelKind, rawText) {
                if (panelKind === 'main') {
                    if (rawText.includes('☠')) return 'lvl-crit';
                    if (rawText.includes('✖')) return 'lvl-error';
                    if (rawText.includes('▲')) return 'lvl-warn';
                    if (rawText.includes('·')) return 'lvl-debug';
                    return '';
                }
                if (panelKind === 'commands') {
                    if (rawText.includes('FALLBACK_FAILED') || rawText.includes('RATE_LIMIT') || rawText.includes('UNKNOWN_TOOL')) {
                        return 'lvl-warn';
                    }
                    return '';
                }
                if (panelKind === 'cancel') {
                    if (rawText.includes('CANCELADO')) return 'lvl-warn';
                    return '';
                }
                return '';
            }

            function createLogPanel(streamType, panelKind, ids) {
                const box = document.getElementById(ids.box);
                const statusDot = document.getElementById(ids.status);
                const searchInput = document.getElementById(ids.search);
                const followBtn = document.getElementById(ids.follow);
                const clearBtn = document.getElementById(ids.clear);
                const countEl = document.getElementById(ids.count);

                let lines = [];
                let following = true;
                let hasContent = false;

                function isNearBottom() {
                    return box.scrollHeight - box.scrollTop - box.clientHeight < 40;
                }

                function scrollToBottom() {
                    box.scrollTop = box.scrollHeight;
                }

                function updateFollowButton() {
                    followBtn.textContent = following ? '⏸ Seguindo' : '▶ Pausado';
                    followBtn.classList.toggle('following', following);
                }

                function applyFilter() {
                    const term = searchInput.value.trim().toLowerCase();
                    let visibleCount = 0;
                    for (const item of lines) {
                        const visible = term === '' || item.text.toLowerCase().includes(term);
                        item.el.classList.toggle('hidden-by-filter', !visible);
                        if (visible) visibleCount += 1;
                    }
                    countEl.textContent = term === ''
                        ? `${lines.length} linhas`
                        : `${visibleCount} de ${lines.length} linhas`;
                }

                function clearEmptyHint() {
                    if (!hasContent) {
                        box.innerHTML = '';
                        hasContent = true;
                    }
                }

                function addLines(rawLines) {
                    if (rawLines.length === 0) return;
                    clearEmptyHint();

                    for (const raw of rawLines) {
                        const div = document.createElement('div');
                        const cls = levelClass(panelKind, raw);
                        div.className = 'log-line' + (cls ? ' ' + cls : '');
                        div.innerHTML = raw;
                        box.appendChild(div);
                        lines.push({ el: div, text: div.textContent });
                    }

                    while (lines.length > MAX_LINES) {
                        const old = lines.shift();
                        old.el.remove();
                    }

                    applyFilter();
                    if (following) scrollToBottom();
                }

                function resetLines() {
                    box.innerHTML = '<span class="empty-hint">Aguardando dados...</span>';
                    hasContent = false;
                    lines = [];
                    countEl.textContent = '0 linhas';
                }

                box.addEventListener('scroll', () => {
                    const nearBottom = isNearBottom();
                    if (following !== nearBottom) {
                        following = nearBottom;
                        updateFollowButton();
                    }
                });

                followBtn.addEventListener('click', () => {
                    following = !following;
                    updateFollowButton();
                    if (following) scrollToBottom();
                });

                clearBtn.addEventListener('click', resetLines);
                searchInput.addEventListener('input', applyFilter);

                updateFollowButton();

                const eventSource = new EventSource(`/stream/${streamType}`);

                eventSource.addEventListener('init', (event) => {
                    resetLines();
                    const rawLines = event.data.split(LINE_SEP).filter(l => l.length > 0);
                    addLines(rawLines);
                    statusDot.classList.remove('status-error');
                    statusDot.classList.add('status-live');
                });

                eventSource.addEventListener('append', (event) => {
                    const rawLines = event.data.split(LINE_SEP).filter(l => l.length > 0);
                    addLines(rawLines);
                    statusDot.classList.remove('status-error');
                    statusDot.classList.add('status-live');
                });

                eventSource.addEventListener('rotated', () => {
                    resetLines();
                });

                eventSource.onerror = () => {
                    // O navegador já reconecta sozinho, então só avisa
                    // visualmente sem apagar o histórico que já foi lido.
                    statusDot.classList.remove('status-live');
                    statusDot.classList.add('status-error');
                };
            }

            createLogPanel('app', 'main', {
                box: 'main-log-box', status: 'main-status-dot', search: 'main-search',
                follow: 'main-follow-btn', clear: 'main-clear-btn', count: 'main-count',
            });
            createLogPanel('commands', 'commands', {
                box: 'commands-log-box', status: 'commands-status-dot', search: 'commands-search',
                follow: 'commands-follow-btn', clear: 'commands-clear-btn', count: 'commands-count',
            });
            createLogPanel('cancel', 'cancel', {
                box: 'cancel-log-box', status: 'cancel-status-dot', search: 'cancel-search',
                follow: 'cancel-follow-btn', clear: 'cancel-clear-btn', count: 'cancel-count',
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
