import subprocess
import time
from pywinauto import Application
from pywinauto.findwindows import ElementNotFoundError

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
        return "Não consegui encontrar o botão da luz noturna na tela de configurações."
    except Exception:
        return "Ocorreu um erro ao tentar alternar a luz noturna."

    time.sleep(0.3)
    try:
        window.close()
    except Exception:
        pass

    return "Luz noturna alternada."
