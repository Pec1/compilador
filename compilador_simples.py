"""
COMPILADOR SIMPLES - AV3 de Compiladores
Uso: python compilador_simples.py arquivo.java

O programa tem 4 etapas, uma em cada seção deste arquivo:
  1. ANÁLISE LÉXICA ....... analisar_lexico()     texto       -> lista de tokens
  2. TABELA DE SÍMBOLOS ... montar_tabela()       tokens      -> palavras reservadas e identificadores
  3. ANÁLISE SINTÁTICA .... analisar_sintaxe()    tokens      -> árvore (AST) de cada comando
  4. ANÁLISE SEMÂNTICA .... analisar_semantica()  árvores     -> erros de tipo e de variável não declarada
"""
import re
import sys
from collections import namedtuple


# =====================================================================
# 1. ANÁLISE LÉXICA: transforma o texto em uma lista de tokens
# =====================================================================

PALAVRAS_RESERVADAS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class", "const",
    "continue", "default", "do", "double", "else", "enum", "extends", "final", "finally", "float",
    "for", "goto", "if", "implements", "import", "instanceof", "int", "interface", "long", "native",
    "new", "package", "private", "protected", "public", "return", "short", "static", "strictfp",
    "super", "switch", "synchronized", "this", "throw", "throws", "transient", "try", "void",
    "volatile", "while", "true", "false", "null",
}
TIPOS_PRIMITIVOS = {"byte", "short", "char", "int", "long", "float", "double", "boolean"}
TIPOS = TIPOS_PRIMITIVOS | {"String"}
MODIFICADORES = {"public", "private", "protected", "static", "final"}
MODIFICADORES_DE_CAMPO = MODIFICADORES - {"final"}   # só campos de classe podem tê-los

# Cada tipo de token é descrito por uma expressão regular.
# A ORDEM IMPORTA: na posição atual, a primeira regra que casar vence.
# Por isso ">>>=" vem antes de ">", e "==" vem antes de "=".
REGRAS = [
    ("COMENTARIO",        r"//[^\n]*|/\*[\s\S]*?\*/"),
    ("COMENTARIO_ABERTO", r"/\*[\s\S]*"),                    # erro: /* sem */
    ("ESPACO",            r"\s+"),
    ("STRING",            r'"""[\s\S]*?"""|"(?:\\.|[^"\\\n])*"'),   # text block ou string
    ("STRING_ABERTA",     r'"[^"\n]*'),                      # erro: string sem fechar
    ("CHAR",              r"'(?:\\.|[^'\\\n])+'"),
    ("CHAR_ABERTO",       r"'[^'\n]*"),                      # erro: char sem fechar
    ("NUM",               r"0[xX][0-9a-fA-F_]+[lL]?|(?:\d[\d_]*(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?[fFdDlL]?"),
    ("ID",                r"(?:[^\W\d]|\$)(?:\w|\$)*"),
    ("OPERADOR",          r">>>=|<<=|>>=|>>>|\.\.\.|==|!=|<=|>=|&&|\|\||\+\+|--|[+\-*/%&|^]=|->|::|<<|>>"),
    ("OP_ATRIB",          r"="),
    ("OP_ARIT",           r"[+\-*/%]"),
    ("OPERADOR",          r"[<>!~&|^?:]"),
    ("DELIMITADOR",       r"[;,.(){}\[\]@]"),
]
REGRAS = [(tipo, re.compile(padrao)) for tipo, padrao in REGRAS]
ERROS_LEXICOS = {
    "COMENTARIO_ABERTO": "comentário '/*' não fechado",
    "STRING_ABERTA": "string não fechada",
    "CHAR_ABERTO": "caractere não fechado",
}

Token = namedtuple("Token", "tipo lexema linha coluna")


def analisar_lexico(codigo):
    tokens, erros = [], []
    pos, linha, coluna = 0, 1, 1
    while pos < len(codigo):
        # Tenta cada regra, na ordem, a partir da posição atual
        for tipo, regra in REGRAS:
            casou = regra.match(codigo, pos)
            if casou:
                texto = casou.group()
                break
        else:
            tipo, texto = "INVALIDO", codigo[pos]

        if tipo == "ID" and texto in PALAVRAS_RESERVADAS:
            tipo = "PALAVRA_RESERVADA"

        if tipo == "INVALIDO":
            erros.append(f"[ERRO LÉXICO] Linha {linha}, coluna {coluna}: caractere inválido '{texto}'.")
        elif tipo in ERROS_LEXICOS:
            erros.append(f"[ERRO LÉXICO] Linha {linha}, coluna {coluna}: {ERROS_LEXICOS[tipo]}.")
        elif tipo not in ("ESPACO", "COMENTARIO"):
            tokens.append(Token(tipo, texto, linha, coluna))

        # Avança o cursor e atualiza linha/coluna (a análise nunca para no erro)
        quebras = texto.count("\n")
        if quebras:
            linha += quebras
            coluna = len(texto) - texto.rfind("\n")
        else:
            coluna += len(texto)
        pos += len(texto)
    return tokens, erros


# =====================================================================
# 2. TABELA DE SÍMBOLOS: cada palavra reservada e identificador, uma vez,
#    na ordem em que aparece (o dicionário do Python preserva a ordem)
# =====================================================================

def montar_tabela(tokens):
    tabela = {}
    for t in tokens:
        if t.tipo in ("PALAVRA_RESERVADA", "ID") and t.lexema not in tabela:
            reservada = t.tipo == "PALAVRA_RESERVADA"
            tabela[t.lexema] = {
                "ordem": len(tabela) + 1,
                "categoria": "palavra reservada" if reservada else "identificador",
                "tipo": "tipo primitivo" if t.lexema in TIPOS_PRIMITIVOS else "-",
                "linha": t.linha,
            }
    return tabela


# =====================================================================
# 3. ANÁLISE SINTÁTICA: monta a AST com a gramática abaixo
#
#   <Declaracao> ::= <Tipo> <ID> ["=" <Expressao>] ("," <ID> ["=" <Expressao>])* ";"
#   <Atribuicao> ::= <ID> "=" <Expressao> ";"
#   <Expressao>  ::= <Termo> (("+" | "-") <Termo>)*
#   <Termo>      ::= <Fator> (("*" | "/" | "%") <Fator>)*
#   <Fator>      ::= <ID> | <NUM> | <STRING> | <CHAR> | true | false | null
#                  | "(" <Expressao> ")" | "-" <Fator>
#
# Comandos Java fora da gramática (class, if, for, chamadas...) são ignorados.
# =====================================================================

class No:
    """Nó da AST. Ex.: No("ID", "x") é impresso como "ID (x)"."""
    def __init__(self, tipo, valor=None, filhos=None, linha=0):
        self.tipo, self.valor, self.filhos, self.linha = tipo, valor, filhos or [], linha
        self.campo = False   # True para campo de classe (ex.: private int x;)

    def rotulo(self):
        return self.tipo if self.valor is None else f"{self.tipo} ({self.valor})"


class ErroSintatico(Exception):
    pass


class Parser:
    """Parser descendente recursivo: cada regra da gramática é um método."""
    def __init__(self, tokens):
        self.tokens, self.pos = tokens, 0

    def atual(self, deslocamento=0):
        i = self.pos + deslocamento
        return self.tokens[i] if i < len(self.tokens) else Token("FIM", "", 0, 0)

    def consumir(self, lexema=None, tipo=None):
        t = self.atual()
        if (lexema and t.lexema != lexema) or (tipo and t.tipo != tipo):
            raise ErroSintatico(f"esperado '{lexema or tipo}', encontrado '{t.lexema}'")
        self.pos += 1
        return t

    def comando(self):
        campo = self.atual().lexema in MODIFICADORES_DE_CAMPO
        while self.atual().lexema in MODIFICADORES:
            self.pos += 1
        if self.atual().lexema in TIPOS and self.atual(1).tipo == "ID":
            nos = self.declaracao()
        elif self.atual().tipo == "ID" and self.atual(1).lexema == "=":
            nos = [self.atribuicao()]
        else:
            raise ErroSintatico("comando fora da gramática")
        if self.pos != len(self.tokens):
            raise ErroSintatico("sobraram tokens no comando")
        for no in nos:
            no.campo = campo
        return nos

    def declaracao(self):
        tipo = self.consumir()
        nos = []
        while True:
            nome = self.consumir(tipo="ID")
            filhos = [No("TIPO", tipo.lexema), No("ID", nome.lexema)]
            if self.atual().lexema == "=":
                self.consumir("=")
                filhos += [No("OP_ATRIB", "="), self.expressao()]
            nos.append(No("Declaracao", filhos=filhos, linha=nome.linha))
            if self.atual().lexema != ",":
                break
            self.consumir(",")
        self.consumir(";")
        return nos

    def atribuicao(self):
        nome = self.consumir(tipo="ID")
        self.consumir("=")
        expr = self.expressao()
        self.consumir(";")
        return No("Atribuicao", filhos=[No("ID", nome.lexema), No("OP_ATRIB", "="), expr], linha=nome.linha)

    def expressao(self):
        no = self.termo()
        while self.atual().lexema in ("+", "-"):
            op = self.consumir()
            no = No("Expressao", op.lexema, [no, self.termo()], op.linha)
        return no

    def termo(self):
        no = self.fator()
        while self.atual().lexema in ("*", "/", "%"):
            op = self.consumir()
            no = No("Expressao", op.lexema, [no, self.fator()], op.linha)
        return no

    def fator(self):
        t = self.atual()
        if t.lexema == "-":
            self.consumir()
            return No("Unario", "-", [self.fator()], t.linha)
        if t.lexema == "(":
            self.consumir("(")
            no = self.expressao()
            self.consumir(")")
            return no
        if t.tipo in ("ID", "NUM", "STRING", "CHAR"):
            self.consumir()
            return No(t.tipo, t.lexema, linha=t.linha)
        if t.lexema in ("true", "false"):
            self.consumir()
            return No("BOOL", t.lexema, linha=t.linha)
        if t.lexema == "null":
            self.consumir()
            return No("NULL", "null", linha=t.linha)
        raise ErroSintatico(f"expressão inválida em '{t.lexema}'")


def dividir_comandos(tokens):
    """Separa os tokens em comandos: cada um termina em ';' (fora de parênteses), '{' ou '}'."""
    comandos, atual, parenteses = [], [], 0
    for t in tokens:
        if t.lexema == "}":
            if atual:
                comandos.append(atual)
            atual = []
            continue
        atual.append(t)
        parenteses += {"(": 1, ")": -1}.get(t.lexema, 0)
        if t.lexema == "{" or (t.lexema == ";" and parenteses <= 0):
            comandos.append(atual)
            atual, parenteses = [], 0
    if atual:
        comandos.append(atual)
    return comandos


def procurar_declaracoes(comando):
    """Dentro de um comando ignorado, acha variáveis declaradas (parâmetros, variável do for,
    'Scanner sc = new ...'): um ID logo após um tipo e seguido de = ; , ) ou :"""
    achadas = []
    for anterior, t, seguinte in zip(comando, comando[1:], comando[2:]):
        apos_tipo = anterior.lexema in TIPOS or anterior.tipo == "ID" or anterior.lexema in (">", "]")
        if t.tipo == "ID" and apos_tipo and seguinte.lexema in ("=", ";", ",", ")", ":"):
            achadas.append((t.lexema, anterior.lexema if anterior.lexema in TIPOS else "objeto"))
    return achadas


def analisar_sintaxe(tokens, tabela):
    """Devolve, em ordem, os comandos reconhecidos (AST) e os trechos ignorados."""
    itens = []
    for comando in dividir_comandos(tokens):
        try:
            for no in Parser(comando).comando():
                itens.append(("comando", no))
                if no.tipo == "Declaracao":
                    tipo, nome = no.filhos[0].valor, no.filhos[1].valor
                    if tabela[nome]["tipo"] == "-":
                        tabela[nome]["tipo"] = tipo
        except (ErroSintatico, RecursionError):
            texto = " ".join(t.lexema for t in comando)
            declaracoes = procurar_declaracoes(comando)
            for nome, tipo in declaracoes:
                if tabela[nome]["tipo"] == "-":
                    tabela[nome]["tipo"] = tipo
            campo = comando[0].lexema in MODIFICADORES_DE_CAMPO
            itens.append(("ignorado", (comando[0].linha, texto, declaracoes, campo)))
    return itens


def desenhar_arvore(no):
    """Desenha um nó e seus filhos com ├── e └──."""
    linhas = [no.rotulo()]
    for i, filho in enumerate(no.filhos):
        ultimo = i == len(no.filhos) - 1
        sub = desenhar_arvore(filho)
        linhas.append(("└── " if ultimo else "├── ") + sub[0])
        linhas += [("    " if ultimo else "│   ") + s for s in sub[1:]]
    return linhas


# =====================================================================
# 4. ANÁLISE SEMÂNTICA: percorre as árvores na ordem do código
#    - variável usada sem ter sido declarada antes
#    - tipo da expressão incompatível com o tipo da variável
# =====================================================================

ORDEM_NUMERICA = ["byte", "short", "char", "int", "long", "float", "double"]


def tipo_do_numero(lexema):
    texto = lexema.lower()
    if texto.endswith("l"):
        return "long"
    if texto.startswith("0x"):
        return "int"
    if texto.endswith("f"):
        return "float"
    if texto.endswith("d") or "." in texto or "e" in texto:
        return "double"
    return "int"


def tipo_da_expressao(no, declaradas):
    if no.tipo == "NUM":
        return tipo_do_numero(no.valor)
    if no.tipo in ("STRING", "CHAR", "BOOL", "NULL"):
        return {"STRING": "String", "CHAR": "char", "BOOL": "boolean", "NULL": "null"}[no.tipo]
    if no.tipo == "ID":
        return declaradas.get(no.valor)
    if no.tipo == "Unario":
        return tipo_da_expressao(no.filhos[0], declaradas)
    if no.tipo == "Expressao":
        esq = tipo_da_expressao(no.filhos[0], declaradas)
        dir = tipo_da_expressao(no.filhos[1], declaradas)
        if no.valor == "+" and "String" in (esq, dir):
            return "String"                     # "a" + 1 é concatenação
        if esq in ORDEM_NUMERICA and dir in ORDEM_NUMERICA:
            maior = max(esq, dir, key=ORDEM_NUMERICA.index)
            return maior if ORDEM_NUMERICA.index(maior) > ORDEM_NUMERICA.index("int") else "int"
    return None


def compativel(destino, origem, expressao):
    if origem is None or destino not in TIPOS or origem == destino:
        return True
    if expressao.tipo == "NUM" and origem == "int" and destino in ("byte", "short", "char"):
        return True                             # char c = 65; é permitido
    if origem == "null":
        return destino not in TIPOS_PRIMITIVOS
    if destino in ORDEM_NUMERICA and origem in ORDEM_NUMERICA:
        return ORDEM_NUMERICA.index(origem) <= ORDEM_NUMERICA.index(destino)   # int -> double ok
    return False


def verificar_uso(no, declaradas, erros):
    """Procura, dentro da expressão, variáveis que ainda não foram declaradas."""
    if no.tipo == "ID" and no.valor not in declaradas:
        erros.append(f"[ERRO SEMÂNTICO] Variável '{no.valor}' utilizada na linha {no.linha} "
                     f"não foi declarada previamente.")
    for filho in no.filhos:
        verificar_uso(filho, declaradas, erros)


def analisar_semantica(itens):
    declaradas = {}   # nome -> tipo
    erros = []

    # Campos da classe valem no arquivo todo, mesmo se declarados depois do método que os usa
    for tipo_item, conteudo in itens:
        if tipo_item == "comando" and conteudo.campo and conteudo.tipo == "Declaracao":
            declaradas[conteudo.filhos[1].valor] = conteudo.filhos[0].valor
        elif tipo_item == "ignorado" and conteudo[3]:
            declaradas.update(conteudo[2])

    for tipo_item, conteudo in itens:
        if tipo_item == "ignorado":
            for nome, tipo in conteudo[2]:
                declaradas[nome] = tipo
            continue

        no = conteudo
        if no.tipo == "Declaracao":
            tipo, nome = no.filhos[0].valor, no.filhos[1].valor
            expr = no.filhos[3] if len(no.filhos) == 4 else None
        else:  # Atribuicao
            nome, expr = no.filhos[0].valor, no.filhos[2]
            no.filhos[0].linha = no.linha
            verificar_uso(no.filhos[0], declaradas, erros)
            tipo = declaradas.get(nome)

        if expr is not None:
            verificar_uso(expr, declaradas, erros)
            tipo_expr = tipo_da_expressao(expr, declaradas)
            if tipo and not compativel(tipo, tipo_expr, expr):
                erros.append(f"[ERRO SEMÂNTICO] Incompatibilidade de tipos na linha {no.linha}: "
                             f"Não é possível atribuir {tipo_expr} a um tipo {tipo}.")
        if no.tipo == "Declaracao":
            declaradas[nome] = tipo
    return erros


# =====================================================================
# PROGRAMA PRINCIPAL: lê o arquivo, roda as 4 etapas e imprime cada seção
# =====================================================================

def titulo(texto):
    print("\n" + "=" * 70 + "\n " + texto + "\n" + "=" * 70)


def ler_arquivo(caminho):
    dados = open(caminho, "rb").read()
    try:
        return dados.decode("utf-8-sig")
    except UnicodeDecodeError:
        return dados.decode("cp1252", errors="replace")   # arquivo salvo como ANSI no Windows


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) != 2:
        print("Uso: python compilador_simples.py arquivo.java")
        return
    try:
        codigo = ler_arquivo(sys.argv[1])
    except OSError:
        print(f"[ERRO DE ENTRADA] Não foi possível abrir o arquivo '{sys.argv[1]}'.")
        return

    tokens, erros_lexicos = analisar_lexico(codigo)       # 1
    tabela = montar_tabela(tokens)                         # 2
    itens = analisar_sintaxe(tokens, tabela)               # 3
    erros_semanticos = analisar_semantica(itens)           # 4

    titulo(f"1. TOKENS ({len(tokens)})")
    print(f"{'#':>4}  {'Linha':<6}{'Coluna':<8}{'Tipo':<19}Lexema")
    for i, t in enumerate(tokens, 1):
        print(f"{i:>4}  {t.linha:<6}{t.coluna:<8}{t.tipo:<19}{t.lexema}")

    titulo(f"2. TABELA DE SÍMBOLOS ({len(tabela)})")
    print(f"{'Ordem':<7}{'Lexema':<16}{'Categoria':<20}{'Tipo':<16}Linha")
    for nome, s in tabela.items():
        print(f"{s['ordem']:<7}{nome:<16}{s['categoria']:<20}{s['tipo']:<16}{s['linha']}")

    titulo(f"3. ERROS LÉXICOS ({len(erros_lexicos)})")
    print("\n".join(erros_lexicos) or "Nenhum erro léxico.")

    titulo("4. ANÁLISE SINTÁTICA - AST")
    for tipo_item, conteudo in itens:
        if tipo_item == "comando":
            print(f"\n[linha {conteudo.linha}]")
            print("\n".join(desenhar_arvore(conteudo)))
    ignorados = [c for t, c in itens if t == "ignorado"]
    if ignorados:
        print(f"\nTrechos fora da gramática (ignorados): {len(ignorados)}")
        for linha, texto, _, _ in ignorados:
            print(f"   linha {linha:>3}: {texto[:55]}")

    titulo(f"5. ERROS SEMÂNTICOS ({len(erros_semanticos)})")
    print("\n".join(erros_semanticos) or "Nenhum erro semântico.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print(f"[ERRO INESPERADO] {erro}")
