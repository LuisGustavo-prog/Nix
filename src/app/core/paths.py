from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = SRC_DIR.parent

LOGS_DIR = SRC_DIR / "logs"
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE_FILE = PROJECT_ROOT / ".env.example"
