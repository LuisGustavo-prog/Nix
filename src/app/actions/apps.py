import os
import subprocess
import winreg
from pathlib import Path
from difflib import get_close_matches
import psutil
import win32com.client

START_MENU_DIRS = [
    Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs",
    Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs"),
]
KNOWN_APP_DIRS = {
    "spotify": Path.home() / "AppData/Roaming/Spotify",
}

def _normalize(name: str) -> str:
    return name.strip().lower().replace(" ", "")

def _fuzzy_lookup(app_name: str, alias_map: dict[str, str], cutoff: float = 0.75) -> str | None:
    normalized_input = _normalize(app_name)
    normalized_map = {_normalize(key): value for key, value in alias_map.items()}

    if normalized_input in normalized_map:
        return normalized_map[normalized_input]

    matches = get_close_matches(normalized_input, normalized_map.keys(), n=1, cutoff=cutoff)
    if matches:
        return normalized_map[matches[0]]

    return None

def _find_in_app_paths_registry(exe_name: str) -> str | None:
    if not exe_name.endswith(".exe"):
        exe_name += ".exe"

    key_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{exe_name}"

    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, key_path) as key:
                value = winreg.QueryValue(key, None)
                return value.strip('"') if value else None
        except FileNotFoundError:
            continue
    return None

def _find_in_start_menu(app_name: str) -> str | None:
    normalized = _normalize(app_name)
    shortcuts: dict[str, Path] = {}

    for base_dir in START_MENU_DIRS:
        if not base_dir.exists():
            continue
        for lnk in base_dir.rglob("*.lnk"):
            shortcuts[_normalize(lnk.stem)] = lnk

    if normalized in shortcuts:
        return str(shortcuts[normalized])

    matches = get_close_matches(normalized, shortcuts.keys(), n=1, cutoff=0.6)
    if matches:
        return str(shortcuts[matches[0]])

    return None

def _find_in_known_dirs(exe_name: str, normalized_name: str) -> str | None:
    base_dir = KNOWN_APP_DIRS.get(normalized_name)
    if base_dir is None or not base_dir.exists():
        return None

    for path in base_dir.rglob(exe_name):
        return str(path)
    return None

def _find_in_common_folders(exe_name: str) -> str | None:
    if not exe_name.endswith(".exe"):
        exe_name += ".exe"

    common_dirs = [
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
        Path.home() / "AppData/Local/Programs",
    ]

    for base_dir in common_dirs:
        if not base_dir.exists():
            continue
        for path in base_dir.rglob(exe_name):
            return str(path)
    return None

def resolve_app_path(app_name: str) -> str | None:
    normalized = _normalize(app_name)
    exe_name = normalized if normalized.endswith(".exe") else normalized + ".exe"

    path = _find_in_start_menu(app_name)
    if path:
        return path

    path = _find_in_app_paths_registry(normalized)
    if path:
        return path

    path = _find_in_known_dirs(exe_name, normalized)
    if path:
        return path

    path = _find_in_common_folders(normalized)
    if path:
        return path

    return None

def _launch(path: str) -> None:
    if path.lower().endswith(".lnk"):
        os.startfile(path)
    else:
        subprocess.Popen(path)

_SETTINGS_URI_APPS = {
    "configurações": "ms-settings:",
    "configuração": "ms-settings:",
    "configuracoes": "ms-settings:",
    "configuracao": "ms-settings:",
    "settings": "ms-settings:",
}

def open_app(app_name: str) -> str:
    matched_uri = _fuzzy_lookup(app_name, _SETTINGS_URI_APPS)
    if matched_uri:
        os.startfile(matched_uri)
        return f"Abrindo {app_name}."

    system_apps = {
        "bloco de notas": "notepad",
        "notepad": "notepad",
        "calculadora": "calc",
        "paint": "mspaint",
        "gerenciador de tarefas": "taskmgr",
        "taskmgr": "taskmgr",
        "prompt de comando": "cmd",
        "cmd": "cmd",
        "powershell": "powershell",
        "editor de registro": "regedit",
        "regedit": "regedit",
        "painel de controle": "control",
        "explorador de arquivos": "explorer",
    }

    matched_command = _fuzzy_lookup(app_name, system_apps)
    if matched_command:
        subprocess.Popen(matched_command)
        return f"Abrindo {app_name}."

    path = resolve_app_path(app_name)
    if path is None:
        return f"Não consegui encontrar o aplicativo {app_name}."

    try:
        _launch(path)
    except Exception:
        return f"Não consegui abrir {app_name}. Talvez ele precise de permissão de administrador."

    return f"Abrindo {app_name}."

_CLOSE_APP_ALIASES = {
    "bloco de notas": "notepad.exe",
    "notepad": "notepad.exe",
    "calculadora": "calculatorapp.exe",
    "calc": "calculatorapp.exe",
    "paint": "mspaint.exe",
    "gerenciador de tarefas": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "prompt de comando": "cmd.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "editor de registro": "regedit.exe",
    "regedit": "regedit.exe",
    "configurações": "systemsettings.exe",
    "configuração": "systemsettings.exe",
    "configuracoes": "systemsettings.exe",
    "configuracao": "systemsettings.exe",
}

def close_app(app_name: str) -> str:
    target = _fuzzy_lookup(app_name, _CLOSE_APP_ALIASES) or app_name.strip().lower()
    closed_any = False

    try:
        for proc in psutil.process_iter(["pid", "name"]):
            proc_name = (proc.info["name"] or "").lower()
            if target in proc_name:
                try:
                    proc.terminate()
                    closed_any = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
    except Exception:
        return f"Ocorreu um problema ao tentar fechar {app_name}."

    if closed_any:
        return f"Fechando {app_name}."

    return f"Não encontrei {app_name} rodando no momento."