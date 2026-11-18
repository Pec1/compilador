"""
ETAPA 2 - ANÁLISE SINTÁTICA (barema: Sintática + AST)
Recebe a lista de tokens e devolve os "itens" do programa, na ordem: cada comando que casa
com a gramática vira uma AST; o resto (class, if, for, chamadas...) é pulado sem erro.
Parser descendente recursivo: uma função por regra da gramática.
"""
from tabela_simbolos import tipo_antes, TIPOS_PRIMITIVOS

TIPOS = TIPOS_PRIMITIVOS | {"String"}
MODIFICADORES = {"public", "private", "protected", "static", "final"}

class ErroSintatico(Exception):
    """Levantado quando os tokens não casam com a gramática; o trecho é então pulado."""

def no(classe, valor=None, filhos=(), linha=0):
    """Um nó da AST. no("ID", "x") é impresso como "ID (x)"."""
    return {"classe": classe, "valor": valor, "filhos": list(filhos), "linha": linha}

def esperar(tokens, i, lexema=None, tipo=None):
    t = tokens[i]
    if (lexema and t.lexema != lexema) or (tipo and t.tipo != tipo):
        raise ErroSintatico(f"esperado '{lexema or tipo}', encontrado '{t.lexema}'")
    return t, i + 1

# <Comando> ::= <Declaracao> | <Atribuicao>
def comando(tokens, i, erros):
    while tokens[i].lexema in MODIFICADORES:          # private static int x = 1;
        i += 1
    if tokens[i].lexema in TIPOS and tokens[i + 1].tipo == "IDENTIFICADOR":
        return declaracao(tokens, i, erros)
    if tokens[i].tipo == "IDENTIFICADOR" and tokens[i + 1].lexema == "=":
        return atribuicao(tokens, i, erros)
    raise ErroSintatico("fora da gramática")

# <Declaracao> ::= <Tipo> ID ["=" <Expressao>] ("," ID ["=" <Expressao>])* ";"
# (a lista com "," é necessária para o "int x, a;" do Barema.java; cada variável vira um nó)
def declaracao(tokens, i, erros):
    tipo, i = tokens[i], i + 1
    nos = []
    while True:
        nome, i = esperar(tokens, i, tipo="IDENTIFICADOR")
        filhos = [no("TIPO", tipo.lexema), no("ID", nome.lexema)]
        if tokens[i].lexema == "=":
            expr, i = expressao(tokens, i + 1)
            filhos += [no("OP_ATRIB", "="), expr]
        nos.append(no("Declaracao", filhos=filhos, linha=nome.linha))
        if tokens[i].lexema != ",":
            break
        i += 1
    i = fim_do_comando(tokens, i, erros)
    return nos, i

# <Atribuicao> ::= ID "=" <Expressao> ";"
def atribuicao(tokens, i, erros):
    nome, i = esperar(tokens, i, tipo="IDENTIFICADOR")
    _, i = esperar(tokens, i, "=")
    expr, i = expressao(tokens, i)
    i = fim_do_comando(tokens, i, erros)
    filhos = [no("ID", nome.lexema, linha=nome.linha), no("OP_ATRIB", "="), expr]
    return [no("Atribuicao", filhos=filhos, linha=nome.linha)], i

# O ";" que fecha <Declaracao>/<Atribuicao>. Se ele falta mas o comando claramente acabou
# (o próximo token está numa linha nova, ou é '}'), é um ERRO SINTÁTICO: registramos e
# seguimos como se o ';' estivesse lá, para não perder o comando nem os seguintes.
# Se falta no meio da linha (ex.: "String s = sc.nextLine();"), o trecho é só Java fora da
# gramática e é pulado sem erro, como antes.
def fim_do_comando(tokens, i, erros):
    t, anterior = tokens[i], tokens[i - 1]
    if t.lexema == ";":
        return i + 1
    if t.tipo == "FIM" or t.lexema == "}" or t.linha > anterior.linha:
        erros.append(f"[ERRO SINTÁTICO] Linha {anterior.linha}, coluna "
                     f"{anterior.coluna + len(anterior.lexema)}: esperado ';' após '{anterior.lexema}'.")
        return i
    raise ErroSintatico(f"esperado ';', encontrado '{t.lexema}'")

# <Expressao> ::= <Termo> (("+"|"-") <Termo>)*
# Expressao chama Termo, que chama Fator: por isso * e / ficam mais fundo na árvore
# e são calculados antes de + e - (precedência).
def expressao(tokens, i):
    esquerda, i = termo(tokens, i)
    while tokens[i].lexema in ("+", "-"):
        op = tokens[i]
        direita, i = termo(tokens, i + 1)
        esquerda = no("Expressao", op.lexema, [esquerda, direita], op.linha)
    return esquerda, i

# <Termo> ::= <Fator> (("*"|"/") <Fator>)*
def termo(tokens, i):
    esquerda, i = fator(tokens, i)
    while tokens[i].lexema in ("*", "/"):
        op = tokens[i]
        direita, i = fator(tokens, i + 1)
        esquerda = no("Expressao", op.lexema, [esquerda, direita], op.linha)
    return esquerda, i

# <Fator> ::= ID | NUMERO | STRING | "(" <Expressao> ")"
def fator(tokens, i):
    t = tokens[i]
    if t.tipo == "IDENTIFICADOR":
        return no("ID", t.lexema, linha=t.linha), i + 1
    if t.tipo in ("NUMERO", "STRING"):                # NUM é o rótulo usado no barema
        return no("NUM" if t.tipo == "NUMERO" else "STRING", t.lexema, linha=t.linha), i + 1
    if t.lexema == "(":
        expr, i = expressao(tokens, i + 1)
        _, i = esperar(tokens, i, ")")
        return expr, i
    raise ErroSintatico(f"expressão inválida em '{t.lexema}'")

# RECUPERAÇÃO: o que não casa com <Comando> é pulado até ';' (consumido), '{' ou '}', sem
# contar o ';' dentro de "for (...;...)". Também para numa linha nova que começa com tipo
# (int, double...): o ';' anterior se perdeu (ex.: string não fechada) e a declaração é salva.
def pular(tokens, i):
    inicio, parenteses = i, 0
    while tokens[i].tipo != "FIM":
        lexema = tokens[i].lexema
        linha_nova_com_tipo = i > inicio and lexema in TIPOS_PRIMITIVOS and tokens[i].linha > tokens[i - 1].linha
        if parenteses == 0 and (lexema in ("{", "}") or linha_nova_com_tipo):
            return i
        parenteses += {"(": 1, ")": -1}.get(lexema, 0)
        i += 1
        if parenteses <= 0 and lexema == ";":
            return i
    return i

def declaracoes_no_trecho(tokens, inicio, fim):
    """Variáveis declaradas num trecho pulado (parâmetros, variável do for, Scanner sc = ...):
    um identificador logo depois de um tipo e seguido de = ; , ) ou :"""
    achadas = {}
    for i in range(inicio, fim):
        t = tokens[i]
        if t.tipo == "IDENTIFICADOR" and tokens[i + 1].lexema in ("=", ";", ",", ")", ":"):
            tipo = tipo_antes(tokens, i)
            if tipo and tipo != "void":
                achadas[t.lexema] = tipo
    return achadas

def analisar_sintaxe(tokens):
    """Devolve (itens, erros). Cada item é ("comando", ast, nivel) ou ("pulado", declaracoes, nivel);
    'nivel' é quantas chaves estão abertas (1 = corpo da classe, ou seja, um atributo)."""
    itens, erros, i, nivel = [], [], 0, 0
    while tokens[i].tipo != "FIM":
        lexema = tokens[i].lexema
        if lexema in ("{", "}", ";"):
            nivel += {"{": 1, "}": -1}.get(lexema, 0)
            i += 1
            continue
        try:
            erros_antes = len(erros)
            nos, i = comando(tokens, i, erros)
            itens += [("comando", ast, nivel) for ast in nos]
        except (ErroSintatico, RecursionError):
            del erros[erros_antes:]                     # trecho descartado: seus erros também
            fim = max(pular(tokens, i), i + 1)          # garante que o laço sempre avança
            itens.append(("pulado", declaracoes_no_trecho(tokens, i, fim), nivel))
            i = fim
    return itens, erros

def imprimir_arvore(ast, prefixo=""):
    """Caminhamento em profundidade: imprime o nó e, recursivamente, cada filho.
    O último filho recebe '└── ' e seus descendentes são recuados com espaços;
    os outros recebem '├── ' e seus descendentes continuam a linha com '│   '."""
    linhas = []
    for n, filho in enumerate(ast["filhos"]):
        ultimo = n == len(ast["filhos"]) - 1
        valor = "" if filho["valor"] is None else f" ({filho['valor']})"
        linhas.append(prefixo + ("└── " if ultimo else "├── ") + filho["classe"] + valor)
        linhas += imprimir_arvore(filho, prefixo + ("    " if ultimo else "│   "))
    return linhas
