import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "nix.log"
COMMANDS_LOG_FILE = LOG_DIR / "comandos.log"
CANCEL_LOG_FILE = LOG_DIR / "cancelamento.log"
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 5
_NAME_WIDTH = 12
_LEVEL_WIDTH = 8
_LEVEL_ICONS = {
    "DEBUG": "·",
    "INFO": "ℹ",
    "WARNING": "▲",
    "ERROR": "✖",
    "CRITICAL": "☠",
}
_LEVEL_COLORS = {
    "DEBUG": "\033[2m",     
    "INFO": "\033[36m",      
    "WARNING": "\033[33m",   
    "ERROR": "\033[31m",      
    "CRITICAL": "\033[1;41m",  
}
_RESET = "\033[0m"

class NixLogFormatter(logging.Formatter):
    def __init__(self, use_color: bool = False) -> None:
        super().__init__(datefmt="%Y-%m-%d %H:%M:%S")
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, self.datefmt)
        icon = _LEVEL_ICONS.get(record.levelname, "•")
        level = f"{record.levelname:<{_LEVEL_WIDTH}}"

        short_name = record.name.removeprefix("nix.").removeprefix("nix") or "core"
        name = f"{short_name[:_NAME_WIDTH]:<{_NAME_WIDTH}}"

        line = f"{timestamp} │ {icon} {level} │ {name} │ {record.getMessage()}"

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        if record.stack_info:
            line += "\n" + self.formatStack(record.stack_info)

        if self.use_color:
            color = _LEVEL_COLORS.get(record.levelname, "")
            return f"{color}{line}{_RESET}"
        return line

_configured = False
_commands_configured = False
_cancel_configured = False

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    global _configured

    logger = logging.getLogger("nix")
    logger.setLevel(level)

    if _configured:
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(NixLogFormatter(use_color=False))
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(NixLogFormatter(use_color=True))
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

    formatter = logging.Formatter(fmt="%(message)s")

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

def setup_cancel_check_logger(level: int = logging.INFO) -> logging.Logger:
    global _cancel_configured

    logger = logging.getLogger("nix.cancelamento")
    logger.setLevel(level)
    logger.propagate = False

    if _cancel_configured:
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        CANCEL_LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    logger.addHandler(file_handler)

    _cancel_configured = True
    return logger

def get_cancel_check_logger() -> logging.Logger:
    return logging.getLogger("nix.cancelamento")
