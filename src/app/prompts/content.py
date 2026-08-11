"""Listas e mapeamentos de conteúdo usados pelas actions.

Diferente de system_prompts.py (que são instruções para os modelos de IA),
esse arquivo guarda dados "de conteúdo": músicas, palavras de pontuação
ditada, etc. Fica junto da família de prompts porque também é texto que
tende a mudar com frequência e não é lógica de programa.
"""

# --- composite.py (start_work_mode) ----------------------------------------

WORK_MUSIC_QUERIES = [
    "Michael Jackson Bad",
    "Michael Jackson Billie Jean",
    "https://music.youtube.com/watch?v=TTzD6gWV16s",
    "Combichrist - Never Surrender [HQ] [Devil May Cry Soundtrack]",
]

# --- stt.py (correção de erros conhecidos de transcrição) ------------------

STT_KNOWN_MISHEARINGS = {
    "niki": "nix",
    "nike": "nix",
    "nick": "nix",
    "nikes": "nix",
    "editado": "ditado",
    "ópera": "opera",
}

# --- dictation.py (dictate_text) --------------------------------------------

DICTATION_PUNCTUATION_MAP = {
    r"\bponto final\b": ".",
    r"\bvírgula\b": ",",
    r"\bponto e vírgula\b": ";",
    r"\bdois pontos\b": ":",
    r"\bponto de interrogação\b": "?",
    r"\bponto de exclamação\b": "!",
    r"\bnova linha\b": "\n",
    r"\bparágrafo\b": "\n\n",
}
