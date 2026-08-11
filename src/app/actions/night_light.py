import subprocess
import time
from pywinauto import Application
from pywinauto.findwindows import ElementNotFoundError
from app.core.logging_config import get_logger

log = get_logger("night_light")

_SETTINGS_URI = "ms-settings:nightlight"
_WAIT_FOR_WINDOW = 1.5
_BUTTON_TITLE_REGEX = r"(Ativar agora|Desativar agora)"

def toggle_night_light() -> str:
    subprocess.run(f"start {_SETTINGS_URI}", shell=True)
    time.sleep(_WAIT_FOR_WINDOW)

    try:
        app = Application(backend="uia").connect(title_re=".*Config.*")
        window = app.top_window()
        toggle_button = window.child_window(
            title_re=_BUTTON_TITLE_REGEX, control_type="Button"
        )
        toggle_button.click_input()
    except ElementNotFoundError:
        log.warning("Botão da luz noturna não encontrado na tela de configurações.")
        return "Não consegui encontrar o botão da luz noturna na tela de configurações."
    except Exception:
        log.exception("Erro ao tentar alternar a luz noturna")
        return "Ocorreu um erro ao tentar alternar a luz noturna."

    time.sleep(0.3)
    try:
        window.close()
    except Exception:
        log.debug("Não foi possível fechar a janela de configurações automaticamente.")

    return "Luz noturna alternada."
