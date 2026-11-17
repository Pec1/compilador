"""
ETAPA 3 - ANÁLISE SEMÂNTICA (barema: Semântica)
Recebe os itens do sintático (ASTs e trechos pulados) e devolve a lista de erros:
variável usada sem declaração prévia e tipo incompatível na atribuição.
Percorre o programa na ordem do código, guardando as variáveis declaradas (nome -> tipo).
"""
# Do mais estreito para o mais largo: um valor pode ir para um tipo à sua direita sem cast
ORDEM_NUMERICA = ["byte", "short", "char", "int", "long", "float", "double"]
TIPOS_CONHECIDOS = set(ORDEM_NUMERICA) | {"boolean", "String"}


def tipo_do_numero(lexema):
    texto = lexema.lower()
    if texto.endswith("l"):
        return "long"
    if texto.startswith("0x") or texto.startswith("0b"):
        return "int"                                  # em hexa, 'f' e 'd' são dígitos
    if texto.endswith("f"):
        return "float"
    if texto.endswith("d") or "." in texto or "e" in texto:
        return "double"
    return "int"


def tipo_da_expressao(no, declaradas):
    """Infere o tipo de baixo para cima: folhas pelo formato, operações pelos operandos."""
    if no["classe"] == "NUM":
        return tipo_do_numero(no["valor"])
    if no["classe"] == "STRING":
        return "String"
    if no["classe"] == "ID":
        return declaradas.get(no["valor"])
    if no["classe"] == "Expressao":
        esq = tipo_da_expressao(no["filhos"][0], declaradas)
        dir_ = tipo_da_expressao(no["filhos"][1], declaradas)
        if no["valor"] == "+" and "String" in (esq, dir_):
            return "String"                           # "a" + 1 é concatenação
        if esq in ORDEM_NUMERICA and dir_ in ORDEM_NUMERICA:
            maior = max(esq, dir_, key=ORDEM_NUMERICA.index)
            return maior if ORDEM_NUMERICA.index(maior) > ORDEM_NUMERICA.index("int") else "int"
    return None


def compativel(destino, origem, expressao):
    """int -> double é permitido (alargamento); double -> int e String -> int não."""
    if origem is None or destino not in TIPOS_CONHECIDOS or origem == destino:
        return True                                   # tipo desconhecido: não acusa erro
    if destino in ("byte", "short", "char") and origem == "int" and expressao["classe"] == "NUM":
        return True                                   # constante cabe: char c = 65;
    if destino in ORDEM_NUMERICA and origem in ORDEM_NUMERICA:
        return ORDEM_NUMERICA.index(origem) <= ORDEM_NUMERICA.index(destino)
    return False


def verificar_uso(no, declaradas, erros):
    """Procura, dentro da expressão, variáveis que ainda não foram declaradas."""
    if no["classe"] == "ID" and no["valor"] not in declaradas:
        erros.append(f"[ERRO SEMÂNTICO] Variável '{no['valor']}' utilizada na linha {no['linha']} "
                     f"não foi declarada previamente.")
    for filho in no["filhos"]:
        verificar_uso(filho, declaradas, erros)


def analisar_semantica(itens):
    declaradas, erros = {}, []

    # Atributos da classe (nível 1) valem no arquivo todo, mesmo se declarados depois do método
    for tipo_item, conteudo, nivel in itens:
        if nivel == 1 and tipo_item == "pulado":
            declaradas.update(conteudo)
        elif nivel == 1 and conteudo["classe"] == "Declaracao":
            declaradas[conteudo["filhos"][1]["valor"]] = conteudo["filhos"][0]["valor"]

    for tipo_item, conteudo, nivel in itens:
        if tipo_item == "pulado":                     # parâmetros, variável do for...
            declaradas.update(conteudo)
            continue
        filhos = conteudo["filhos"]
        if conteudo["classe"] == "Declaracao":        # TIPO, ID [, OP_ATRIB, expressão]
            tipo, nome = filhos[0]["valor"], filhos[1]["valor"]
            expressao = filhos[3] if len(filhos) == 4 else None
        else:                                         # Atribuicao: ID, OP_ATRIB, expressão
            nome, expressao = filhos[0]["valor"], filhos[2]
            verificar_uso(filhos[0], declaradas, erros)
            tipo = declaradas.get(nome)

        if expressao is not None:
            verificar_uso(expressao, declaradas, erros)
            tipo_expr = tipo_da_expressao(expressao, declaradas)
            if tipo and not compativel(tipo, tipo_expr, expressao):
                erros.append(f"[ERRO SEMÂNTICO] Incompatibilidade de tipos na linha {conteudo['linha']}: "
                             f"Não é possível atribuir {tipo_expr} a um tipo {tipo}.")
        if conteudo["classe"] == "Declaracao":
            declaradas[nome] = tipo
    return erros
