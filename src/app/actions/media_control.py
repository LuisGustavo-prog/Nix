import pyautogui

def play_pause() -> str:
    pyautogui.press("playpause")
    return "Alternando reprodução."

def next_track() -> str:
    pyautogui.press("nexttrack")
    return "Pulando para a próxima faixa."

def previous_track() -> str:
    pyautogui.press("prevtrack")
    return "Voltando para a faixa anterior."

def stop() -> str:
    pyautogui.press("stop")
    return "Parando a reprodução."
