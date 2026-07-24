import re
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

def sanitize_username(raw: str) -> str:
    normalized = unicodedata.normalize("NFKD", raw)
    without_accents = "".join(c for c in normalized if not unicodedata.combining(c))
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "", without_accents.lower().replace(" ", "_"))
    return cleaned

def read_existing_env() -> list[str]:
    if ENV_PATH.exists():
        return ENV_PATH.read_text(encoding="utf-8").splitlines()
    return []

def upsert_username(lines: list[str], username: str) -> list[str]:
    """Atualiza a linha NIX_USERNAME se já existir, ou adiciona no final."""
    new_line = f"NIX_USERNAME={username}"
    for i, line in enumerate(lines):
        if line.startswith("NIX_USERNAME="):
            lines[i] = new_line
            return lines
    lines.append(new_line)
    return lines

def main():
    print("=" * 50)
    print("  Configuração inicial do Nix")
    print("=" * 50)

    raw_name = input("\nComo você quer ser chamado (nickname)? ").strip()
    while not raw_name:
        raw_name = input("  -> Esse campo é obrigatório, tenta de novo: ").strip()

    username = sanitize_username(raw_name)
    print(f"  -> Username salvo como: {username}")

    lines = read_existing_env()
    lines = upsert_username(lines, username)

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n✅ Username configurado! Bem-vindo ao Nix, {raw_name}!")
    print("   (Lembre-se de preencher as chaves de API no .env manualmente, "
          "seguindo o .env.example)")

if __name__ == "__main__":
    main()
    