import re
import sys
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"

def sanitize_username(raw: str) -> str:
    normalized = unicodedata.normalize("NFKD", raw)
    without_accents = "".join(c for c in normalized if not unicodedata.combining(c))
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", without_accents.lower().replace(" ", "_"))
    return cleaned

def read_existing_env() -> list[str]:
    if ENV_PATH.exists():
        return ENV_PATH.read_text(encoding="utf-8").splitlines()
    return []

def get_current_username(lines: list[str]) -> str | None:
    for line in lines:
        if line.startswith("NIX_USERNAME="):
            return line.split("=", 1)[1].strip()
    return None

def upsert_username(lines: list[str], username: str) -> list[str]:
    new_line = f"NIX_USERNAME={username}"
    for i, line in enumerate(lines):
        if line.startswith("NIX_USERNAME="):
            lines[i] = new_line
            return lines
    lines.append(new_line)
    return lines

def prompt_username() -> str:
    raw_name = input("\n[1/3] Como você quer ser chamado (nickname)? ").strip()
    while not raw_name:
        raw_name = input("      -> Esse campo é obrigatório, tenta de novo: ").strip()
    return raw_name

def confirm_overwrite(current_username: str) -> bool:
    answer = input(
        f"\n[1/3] Já existe um username configurado ('{current_username}'). "
        f"Quer trocar? [s/N] "
    ).strip().lower()
    return answer in ("s", "sim", "y", "yes")

def check_env_example() -> None:
    print("\n[2/3] Verificando .env.example...")
    if not ENV_EXAMPLE_PATH.exists():
        print("      -> Aviso: .env.example não encontrado na raiz do projeto.")
        print("         Isso é só um modelo de referência, não impede o setup,")
        print("         mas confirme se seu .env tem todas as chaves necessárias.")
    else:
        print("      -> OK, encontrado.")

def write_env(lines: list[str]) -> bool:
    print("\n[3/3] Salvando configuração...")
    try:
        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except PermissionError:
        print(f"      -> Erro: sem permissão para escrever em {ENV_PATH}.")
        print("         Feche qualquer programa que esteja usando o arquivo e tente de novo.")
        return False
    except OSError as e:
        print(f"      -> Erro ao salvar o .env: {e}")
        return False

    print(f"      -> Salvo em {ENV_PATH}")
    return True

def main() -> int:
    print("=" * 50)
    print("  Configuração inicial do Nix")
    print("=" * 50)

    lines = read_existing_env()
    current_username = get_current_username(lines)

    if current_username:
        if not confirm_overwrite(current_username):
            print(f"\nOk, mantendo o username atual: {current_username}")
            username = current_username
            raw_name = current_username
        else:
            raw_name = prompt_username()
            username = sanitize_username(raw_name)
    else:
        raw_name = prompt_username()
        username = sanitize_username(raw_name)

    print(f"      -> Username salvo como: {username}")

    check_env_example()

    lines = upsert_username(lines, username)
    if not write_env(lines):
        return 1

    print(f"\n✅ Username configurado! Bem-vindo ao Nix, {raw_name}!")
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
