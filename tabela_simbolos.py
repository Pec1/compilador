"""
TABELA DE SÍMBOLOS (barema: Tabela de Símbolos)
Recebe a lista de tokens e devolve uma lista de dicionários na ORDEM DE INSERÇÃO:
ordem, lexema, categoria (palavra reservada / identificador), tipo e linha.
Cada palavra entra uma única vez, na primeira vez em que aparece no código.
"""
TIPOS_PRIMITIVOS = {"byte", "short", "char", "int", "long", "float", "double", "boolean"}
DECLARA_TIPO = {"class": "classe", "interface": "interface", "enum": "enum"}


def tipo_antes(tokens, i):
    """Texto do tipo escrito logo antes do token i, ou None.
    int x -> "int" | String nome -> "String" | int[] v -> "int[]" | List<String> l -> "List<String>"
    | class Pessoa -> "classe"."""
    if i == 0:
        return None
    anterior = tokens[i - 1]
    if anterior.lexema in TIPOS_PRIMITIVOS or anterior.lexema == "void":
        return anterior.lexema
    if anterior.lexema in DECLARA_TIPO:
        return DECLARA_TIPO[anterior.lexema]
    if anterior.tipo == "IDENTIFICADOR" and (i < 2 or tokens[i - 2].lexema != "."):
        return anterior.lexema                         # tipo de classe: Scanner sc
    if anterior.lexema == ",":
        # int x, a  /  int x = 1, a: volta até a variável anterior da mesma declaração.
        # Parar em '(' ou '<' evita confundir f(a, b) e Map<K, V> com declarações.
        nivel = 0
        for j in range(i - 2, -1, -1):
            lexema = tokens[j].lexema
            if lexema in (")", "]", "}"):
                nivel += 1
            elif lexema in ("(", "[", "{"):
                if nivel == 0:
                    return None
                nivel -= 1
            elif nivel == 0 and lexema in (";", "<"):
                return None
            elif nivel == 0 and tokens[j].tipo == "IDENTIFICADOR" and tokens[j + 1].lexema in ("=", ","):
                return tipo_antes(tokens, j)
        return None
    if anterior.lexema == "]" and i >= 3 and tokens[i - 2].lexema == "[":
        base = tipo_antes(tokens, i - 2)               # int[] v  ->  tipo de "int" + "[]"
        return base + "[]" if base else None
    if anterior.lexema and set(anterior.lexema) == {">"}:
        # List<String> l: volta contando < e > até o '<' que abre o genérico
        nivel, j = 0, i - 1
        while j > 0:
            t = tokens[j]
            dentro_de_generico = (t.tipo == "IDENTIFICADOR" or t.lexema in ("extends", "super")
                                  or (set(t.lexema) <= set("<>,.?[]&") and t.lexema != "&&"))
            if not dentro_de_generico:
                return None                            # era comparação: if (a < b && c > d)
            nivel += t.lexema.count(">") - t.lexema.count("<")
            if nivel == 0:
                break
            j -= 1
        if j > 0 and tokens[j - 1].tipo == "IDENTIFICADOR":
            return "".join(t.lexema for t in tokens[j - 1:i]).replace(",", ", ")
    return None


def montar_tabela(tokens):
    tabela, por_nome = [], {}
    for i, t in enumerate(tokens):
        if t.tipo not in ("PALAVRA_RESERVADA", "IDENTIFICADOR"):
            continue
        if t.lexema not in por_nome:                   # só a primeira ocorrência é inserida
            reservada = t.tipo == "PALAVRA_RESERVADA"
            simbolo = {"ordem": len(tabela) + 1, "lexema": t.lexema,
                       "categoria": "palavra reservada" if reservada else "identificador",
                       "tipo": "tipo primitivo" if t.lexema in TIPOS_PRIMITIVOS
                       else "literal" if t.lexema in ("true", "false", "null") else "-",
                       "linha": t.linha}
            tabela.append(simbolo)
            por_nome[t.lexema] = simbolo
        # O tipo de um identificador é preenchido quando ele aparece logo depois de um tipo
        simbolo = por_nome[t.lexema]
        if t.tipo == "IDENTIFICADOR" and simbolo["tipo"] == "-":
            tipo = tipo_antes(tokens, i)
            if tipo:
                eh_metodo = tokens[i + 1].lexema == "(" and tipo not in DECLARA_TIPO.values()
                simbolo["tipo"] = f"método ({tipo})" if eh_metodo else tipo
    return tabela


def imprimir_tabela(tabela):
    larg_lexema = max([len(s["lexema"]) for s in tabela] + [6]) + 2
    larg_tipo = max([len(s["tipo"]) for s in tabela] + [4]) + 2
    print(f"{'Ordem':<7}{'Lexema':<{larg_lexema}}{'Categoria':<20}{'Tipo':<{larg_tipo}}Linha")
    for s in tabela:
        print(f"{s['ordem']:<7}{s['lexema']:<{larg_lexema}}{s['categoria']:<20}{s['tipo']:<{larg_tipo}}{s['linha']}")
