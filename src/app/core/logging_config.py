import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "nix.log"
COMMANDS_LOG_FILE = LOG_DIR / "comandos.log"
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 5

_configured = False
_commands_configured = False

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    global _configured

    logger = logging.getLogger("nix")
    logger.setLevel(level)

    if _configured:
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    _configured = True
    return logger

def get_logger(module_name: str) -> logging.Logger:
    return logging.getLogger(f"nix.{module_name}")


def setup_command_logger(level: int = logging.INFO) -> logging.Logger:
   
    global _commands_configured

    logger = logging.getLogger("nix.comandos")
    logger.setLevel(level)
    logger.propagate = False  

    if _commands_configured:
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        COMMANDS_LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    logger.addHandler(file_handler)

    _commands_configured = True
    return logger

def get_command_logger() -> logging.Logger:
    return logging.getLogger("nix.comandos")
