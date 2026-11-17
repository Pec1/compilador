"""
ETAPA 1 - ANÁLISE LÉXICA (barema: Lista de Tokens e Assertividade Léxica)
Recebe o código fonte (texto) e devolve a lista de tokens (tipo, lexema, linha, coluna)
e a lista de erros léxicos. Cada tipo de token é uma expressão regular; um laço tenta as
regras em ordem na posição atual, guarda o token e avança. Erro não para a análise.
"""
import re
from collections import namedtuple

Token = namedtuple("Token", "tipo lexema linha coluna")

# As 51 palavras reservadas do Java + os literais reservados true, false e null
PALAVRAS_RESERVADAS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class", "const",
    "continue", "default", "do", "double", "else", "enum", "extends", "final", "finally", "float",
    "for", "goto", "if", "implements", "import", "instanceof", "int", "interface", "long", "native",
    "new", "package", "private", "protected", "public", "return", "short", "static", "strictfp",
    "super", "switch", "synchronized", "this", "throw", "throws", "transient", "try", "void",
    "volatile", "while", "_", "true", "false", "null",
}

# Operadores do MAIOR para o MENOR: o regex tenta da esquerda para a direita e fica com o
# primeiro que casar. Se ">" viesse antes, ">>>=" viraria quatro tokens.
OPERADORES = [">>>=", "<<=", ">>=", ">>>", "...", "->", "::", "++", "--", "&&", "||", "==", "!=",
              "<=", ">=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<", ">>",
              "=", "+", "-", "*", "/", "%", "<", ">", "!", "~", "&", "|", "^", "?", ":", "@"]

# A ORDEM DAS REGRAS IMPORTA: na posição atual vence a primeira que casar.
#  - comentário antes de operador (senão "//" viraria duas divisões);
#  - text block antes de string (senão """ viraria "" + ");
#  - número antes de operador/delimitador (senão ".5" viraria "." + "5");
#  - as regras *_ABERTO só casam quando a versão correta não casou: são os erros.
REGRAS = [
    ("COMENTARIO",        r"//[^\n]*|/\*[\s\S]*?\*/"),
    ("COMENTARIO_ABERTO", r"/\*[\s\S]*"),
    ("ESPACO",            r"\s+"),
    ("STRING",            r'"""[\s\S]*?(?<!\\)"""|"(?:\\.|[^"\\\n])*"'),
    ("STRING_ABERTA",     r'"[^"\n]*'),
    ("CHAR",              r"'(?:\\u[0-9a-fA-F]{4}|\\.|[^'\\\n])'"),
    ("CHAR_ABERTO",       r"'[^'\n]*'?"),
    ("NUMERO",            r"0[xX][0-9a-fA-F_]*\.?[0-9a-fA-F_]*[pP][+-]?\d+[fFdD]?"   # hexa float: 0x1.8p1
                          r"|0[xX][0-9a-fA-F_]+[lL]?|0[bB][01_]+[lL]?"
                          r"|(?:\d[\d_]*(?:\.(?:\d[\d_]*)?)?|\.\d[\d_]*)(?:[eE][+-]?\d+)?[fFdDlL]?"),
    ("OPERADOR",          "|".join(re.escape(op) for op in OPERADORES)),
    ("DELIMITADOR",       r"[;,.(){}\[\]]"),
    ("IDENTIFICADOR",     r"(?:[^\W\d]|\$)(?:\w|\$)*"),   # \w aceita acentos: ação, número
]
REGRAS = [(tipo, re.compile(padrao)) for tipo, padrao in REGRAS]

ERROS = {
    "COMENTARIO_ABERTO": "comentário '/*' não fechado",
    "STRING_ABERTA": "string não fechada",
    "CHAR_ABERTO": "caractere inválido ou não fechado",
}


def analisar_lexico(codigo):
    tokens, erros = [], []
    pos, linha, coluna = 0, 1, 1
    while pos < len(codigo):
        for tipo, regra in REGRAS:
            casou = regra.match(codigo, pos)
            if casou:
                texto = casou.group()
                break
        else:
            tipo, texto = "INVALIDO", codigo[pos]   # nenhuma regra casou

        if tipo == "IDENTIFICADOR" and texto in PALAVRAS_RESERVADAS:
            tipo = "PALAVRA_RESERVADA"

        if tipo == "INVALIDO":
            erros.append(f"[ERRO LÉXICO] Linha {linha}, coluna {coluna}: caractere inválido '{texto}'.")
        elif tipo in ERROS:
            erros.append(f"[ERRO LÉXICO] Linha {linha}, coluna {coluna}: {ERROS[tipo]}.")
        elif tipo not in ("ESPACO", "COMENTARIO"):
            tokens.append(Token(tipo, texto, linha, coluna))

        # Avança e atualiza linha/coluna. Se o trecho tinha quebras de linha (comentário,
        # text block), a coluna recomeça depois da última quebra.
        quebras = texto.count("\n")
        if quebras:
            linha += quebras
            coluna = len(texto) - texto.rfind("\n")
        else:
            coluna += len(texto)
        pos += len(texto)

    tokens.append(Token("FIM", "", linha, coluna))
    return tokens, erros
