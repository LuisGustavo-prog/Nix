import asyncio
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

app = FastAPI()

# Caminho base apontando para a pasta 'logs'
BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = BASE_DIR / "logs"

# Mapeamento com os nomes exatos dos seus arquivos de log
LOG_FILES = {
    "app": LOGS_DIR / "nix.log",
    "commands": LOGS_DIR / "comandos.log",
    "cancel": LOGS_DIR / "cancelamento.log",
}


def read_last_lines(file_path: Path, max_lines: int = 100) -> str:
    """Lê as últimas linhas de um arquivo de log."""
    if not file_path.exists():
        return f"Ficheiro de log '{file_path.name}' ainda não existe."

    try:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(lines[-max_lines:])
    except Exception as e:
        return f"Erro ao ler o arquivo de log: {e}"


@app.get("/stream/{log_type}")
async def stream_log(log_type: str):
    """Endpoint SSE para streaming de dados em tempo real."""

    async def event_generator():
        log_file = LOG_FILES.get(log_type)
        if not log_file:
            yield "data: Tipo de log inválido\n\n"
            return

        last_content = ""
        while True:
            current_content = read_last_lines(log_file)
            if current_content != last_content:
                last_content = current_content
                # Escapa tags HTML simples para evitar quebras e formata quebras de linha
                formatted = (
                    current_content.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace("\n", "<br>")
                )
                yield f"data: {formatted}\n\n"
            await asyncio.sleep(0.5)

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
                --border-color: #1e293b;
                --accent-purple: #8b5cf6;
                --accent-green: #10b981;
                --accent-blue: #3b82f6;
                --accent-red: #f43f5e;
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

            /* Header Principal */
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

            /* Layout Grid */
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
            }

            /* Card do Terminal */
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
            }

            .main-icon { background: var(--accent-green); box-shadow: 0 0 8px var(--accent-green); }
            .cmd-icon { background: var(--accent-blue); box-shadow: 0 0 8px var(--accent-blue); }
            .cancel-icon { background: var(--accent-red); box-shadow: 0 0 8px var(--accent-red); }

            .file-tag {
                font-family: 'Fira Code', monospace;
                font-size: 11px;
                color: var(--text-muted);
                background: rgba(255, 255, 255, 0.05);
                padding: 3px 8px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }

            /* Janela do Terminal */
            .terminal {
                flex: 1;
                background-color: var(--bg-terminal);
                padding: 16px;
                font-family: 'Fira Code', monospace;
                font-size: 12.5px;
                line-height: 1.6;
                overflow-y: auto;
                color: #cbd5e1;
                white-space: pre-wrap;
                word-break: break-all;
            }

            /* Custom Scrollbar */
            .terminal::-webkit-scrollbar {
                width: 6px;
            }
            .terminal::-webkit-scrollbar-track {
                background: var(--bg-terminal);
            }
            .terminal::-webkit-scrollbar-thumb {
                background: #1e293b;
                border-radius: 3px;
            }
            .terminal::-webkit-scrollbar-thumb:hover {
                background: #334155;
            }

            /* Cores de status no texto dos logs */
            .main-terminal { color: #a7f3d0; }
            .commands-terminal { color: #bae6fd; }
            .cancel-terminal { color: #fecdd3; }
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
                    </div>
                    <span class="file-tag">nix.log</span>
                </div>
                <div id="main-log-box" class="terminal main-terminal">Aguardando dados...</div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-title">
                        <div class="icon cmd-icon"></div>
                        <span>Commands Log</span>
                    </div>
                    <span class="file-tag">comandos.log</span>
                </div>
                <div id="commands-log-box" class="terminal commands-terminal">Aguardando dados...</div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-title">
                        <div class="icon cancel-icon"></div>
                        <span>Cancel Check Log</span>
                    </div>
                    <span class="file-tag">cancelamento.log</span>
                </div>
                <div id="cancel-log-box" class="terminal cancel-terminal">Aguardando dados...</div>
            </div>
        </div>

        <script>
            function connectLogStream(logType, elementId) {
                const box = document.getElementById(elementId);
                const eventSource = new EventSource(`/stream/${logType}`);

                eventSource.onmessage = function(event) {
                    box.innerHTML = event.data;
                    box.scrollTop = box.scrollHeight;
                };

                eventSource.onerror = function() {
                    box.innerText = "Conexão perdida. Tentando reconectar...";
                };
            }

            // Inicia a escuta em tempo real para os três terminais
            connectLogStream('app', 'main-log-box');
            connectLogStream('commands', 'commands-log-box');
            connectLogStream('cancel', 'cancel-log-box');
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)