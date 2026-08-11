"""Caminhos importantes do projeto, calculados uma única vez.

Antes, cada módulo (config.py, logging_config.py, setup.py) recalculava seu
próprio BASE_DIR contando quantos ".parent" eram necessários a partir da
própria localização. Isso funciona, mas é frágil: se a profundidade de
pastas de algum desses arquivos mudar, o cálculo quebra silenciosamente e
de um jeito diferente em cada lugar. Centralizando aqui, só existe um
ponto de verdade.
"""
from pathlib import Path

# Este arquivo mora em <PROJECT_ROOT>/src/app/core/paths.py
SRC_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = SRC_DIR.parent

LOGS_DIR = SRC_DIR / "logs"
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE_FILE = PROJECT_ROOT / ".env.example"
