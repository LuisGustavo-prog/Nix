import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"

sys.path.insert(0, str(BASE_DIR / "src"))

from app.web.username_server import (
    capture_username_blocking,
    get_current_username,
)

_CAPTURE_TIMEOUT_SECONDS = 5 * 60

def check_env_example() -> None:
    print("\n[2/2] Verificando .env.example...")
    if not ENV_EXAMPLE_PATH.exists():
        print("      -> Aviso: .env.example não encontrado na raiz do projeto.")
        print("         Isso é só um modelo de referência, não impede o setup,")
        print("         mas confirme se seu .env tem todas as chaves necessárias.")
    else:
        print("      -> OK, encontrado.")

def main() -> int:
    print("=" * 50)
    print("  Configuração inicial do Nix")
    print("=" * 50)

    current_username = get_current_username()

    if current_username:
        print(f"\n[1/2] Já existe um username configurado: '{current_username}'.")
    else:
        print("\n[1/2] Nenhum username configurado ainda.")

    print("      -> Abrindo a página de configuração no navegador...")
    print("      -> Se não abrir sozinho, acesse http://127.0.0.1:8001 manualmente.")

    raw_name, username = capture_username_blocking(timeout=_CAPTURE_TIMEOUT_SECONDS)

    if username == "usuario" and not current_username:
        print("\n      -> Não recebi nenhuma resposta a tempo pela página.")
        print("         Rode o setup de novo quando quiser tentar.")
        return 1

    check_env_example()

    print(f"\n✅ Username configurado como: {username} (nome: {raw_name})")
    print(
        "   (Lembre-se de preencher as chaves de API no .env manualmente, "
        "seguindo o .env.example)"
    )
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nSetup cancelado.")
        sys.exit(1)
