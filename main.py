import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import asyncio
from app.main import main

_MIN_SECONDS_BETWEEN_RESTARTS = 5
_MAX_RESTART_BACKOFF = 60

def run_forever() -> None:
    backoff = _MIN_SECONDS_BETWEEN_RESTARTS

    while True:
        try:
            asyncio.run(main())
            break 
        except KeyboardInterrupt:
            print("\nEncerrado manualmente (Ctrl+C).")
            break
        except Exception:
            print(f"[FATAL] O Nix quebrou fora do supervisor interno. Reiniciando em {backoff}s...")
            traceback.print_exc()
            time.sleep(backoff)
            backoff = min(backoff * 2, _MAX_RESTART_BACKOFF)

if __name__ == "__main__":
    run_forever()
    