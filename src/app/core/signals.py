class RestartRequested(Exception):
    """Levantada quando o usuário pede pra reiniciar o Nix por voz.

    Propaga até o supervisor externo (main.py da raiz), que reinicia o
    processo inteiro via subprocess.Popen + sys.exit, recarregando o
    código do zero.
    """

class ShutdownRequested(Exception):
    """Levantada quando o usuário pede pra encerrar o Nix por voz.

    É capturada dentro do loop principal (app/main.py) pra encerrar de
    forma limpa, sem acionar o supervisor de reinício.
    """
    