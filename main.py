import sys
import os
import time
import subprocess
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

_EXTERNAL_CONSOLE_MARKER = "NIX_EXTERNAL_CONSOLE_CHILD"
_MIN_SECONDS_BETWEEN_RESTARTS = 5
_MAX_RESTART_BACKOFF = 60
_CONSOLE_CHOICE_TIMEOUT_SECONDS = 5 * 60


def _decide_external_console() -> bool:
    """True = a Nix deve rodar numa janela de cmd separada. Se já existir uma
    escolha salva no .env, usa ela direto. Senão, abre a telinha web pra
    perguntar (mesmo padrão da captura de nome de usuário)."""
    from app.web.console_choice_server import get_current_console_choice, capture_console_choice_blocking

    saved_choice = get_current_console_choice()
    if saved_choice is not None:
        return saved_choice

    return capture_console_choice_blocking(timeout=_CONSOLE_CHOICE_TIMEOUT_SECONDS)


def _relaunch_in_external_console() -> None:
    env = os.environ.copy()
    env[_EXTERNAL_CONSOLE_MARKER] = "1"  # evita reabrir janela em loop
    creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)  # 0 = no-op fora do Windows
    subprocess.Popen([sys.executable] + sys.argv, creationflags=creation_flags, env=env)

def run_forever() -> None:
    import asyncio
    from app.main import main
    from app.core.signals import RestartRequested

    backoff = _MIN_SECONDS_BETWEEN_RESTARTS

    while True:
        try:
            asyncio.run(main())
            break
        except KeyboardInterrupt:
            print("\nEncerrado manualmente (Ctrl+C).")
            break
        except RestartRequested:
            print("[RESTART] Reiniciando o Nix por comando de voz...")
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit(0)
        except Exception:
            print(f"[FATAL] O Nix quebrou fora do supervisor interno. Reiniciando em {backoff}s...")
            traceback.print_exc()
            time.sleep(backoff)
            backoff = min(backoff * 2, _MAX_RESTART_BACKOFF)

if __name__ == "__main__":
    if not os.environ.get(_EXTERNAL_CONSOLE_MARKER) and _decide_external_console():
        print("[NIX_EXTERNAL_CONSOLE] Abrindo a Nix numa janela separada, pode fechar esse terminal.")
        _relaunch_in_external_console()
        sys.exit(0)

    run_forever()
