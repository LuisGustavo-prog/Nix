WORK_MUSIC_QUERIES = [
    "Michael Jackson Bad",
    "Michael Jackson Billie Jean",
    "https://music.youtube.com/watch?v=TTzD6gWV16s",
    "Combichrist - Never Surrender [HQ] [Devil May Cry Soundtrack]",
    "https://music.youtube.com/watch?v=8NceNkPFbEw"
]

STT_KNOWN_MISHEARINGS = {
    "niki": "nix",
    "nike": "nix",
    "nick": "nix",
    "nikes": "nix",
    "editado": "ditado",
    "ópera": "opera",
}

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
