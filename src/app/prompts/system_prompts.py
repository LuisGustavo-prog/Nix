STT_INITIAL_PROMPT = (
    "Comandos de voz para o assistente Nix, em português, com nomes de "
    "músicas e artistas que podem estar em inglês, ex: toca Bohemian "
    "Rhapsody do Queen no YouTube, abrir aplicativos, pesquisar vídeos "
    "no YouTube, controlar volume, fechar programas, controlar a música: "
    "pausa a música, volte a música, próxima música, continua a música."
)

STT_TRIGGER_CHECK_PROMPT = "cancelar comando, finalizar comando"

CORRECTION_SYSTEM_PROMPT = (
    "Você corrige erros óbvios de transcrição de voz em português "
    "brasileiro, sem mudar o sentido da frase nem adicionar informação "
    "nova. Responda só com a frase corrigida, sem aspas, sem explicações."
)

TOOL_CALLING_SYSTEM_PROMPT = (
    "Você é o Nix, assistente de voz pessoal. Chame a ferramenta certa "
    "para o comando do usuário. Se nenhuma tool corresponder, responda "
    "em texto, breve."
)
