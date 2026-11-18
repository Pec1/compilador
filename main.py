"""
PROGRAMA PRINCIPAL:  python main.py arquivo.java
Lê o arquivo .java, chama as etapas em ordem (léxico -> tabela de símbolos -> sintático ->
semântico) e imprime as 5 seções do barema. Nunca mostra traceback: entrada inválida ou
falha inesperada viram mensagens amigáveis.
"""
import sys

from lexico import analisar_lexico
from tabela_simbolos import montar_tabela, imprimir_tabela
from sintatico import analisar_sintaxe, imprimir_arvore
from semantico import analisar_semantica


def titulo(texto):
    print("\n" + "=" * 70 + "\n " + texto + "\n" + "=" * 70)


def ler_arquivo(caminho):
    with open(caminho, "rb") as arquivo:
        dados = arquivo.read()
    try:
        return dados.decode("utf-8-sig")              # UTF-8, com ou sem BOM
    except UnicodeDecodeError:
        return dados.decode("latin-1")                # arquivo salvo como ANSI no Windows


def main():
    if hasattr(sys.stdout, "reconfigure"):            # acentos e ├── no console do Windows
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) != 2:
        print("[ERRO DE ENTRADA] Informe o arquivo fonte. Uso: python main.py arquivo.java")
        return 1
    caminho = sys.argv[1]
    try:
        codigo = ler_arquivo(caminho)
    except FileNotFoundError:
        print(f"[ERRO DE ENTRADA] Arquivo não encontrado: '{caminho}'.")
        return 1
    except OSError:
        print(f"[ERRO DE ENTRADA] Não foi possível abrir '{caminho}' (é uma pasta ou não há permissão?).")
        return 1

    tokens, erros_lexicos = analisar_lexico(codigo)    # ETAPA 1: texto -> tokens
    tabela = montar_tabela(tokens)                     #           tokens -> tabela de símbolos
    itens, erros_sintaticos = analisar_sintaxe(tokens) # ETAPA 2: tokens -> ASTs
    erros_semanticos = analisar_semantica(itens)       # ETAPA 3: ASTs -> erros de tipo/declaração

    titulo(f"1. TOKENS ({len(tokens) - 1})")
    print(f"{'#':>4}  {'Linha':<6}{'Coluna':<8}{'Tipo':<19}Lexema")
    for n, t in enumerate(tokens[:-1], start=1):       # tokens[:-1]: sem o marcador FIM
        lexema = t.lexema if len(t.lexema) <= 40 else t.lexema[:37] + "..."
        print(f"{n:>4}  {t.linha:<6}{t.coluna:<8}{t.tipo:<19}{lexema.replace(chr(10), ' ')}")

    titulo(f"2. TABELA DE SÍMBOLOS ({len(tabela)}, em ordem de inserção)")
    imprimir_tabela(tabela)

    titulo(f"3. ERROS LÉXICOS ({len(erros_lexicos)})")
    print("\n".join(erros_lexicos) or "Nenhum erro léxico.")

    titulo("4. ÁRVORE SINTÁTICA (AST)")
    comandos = [ast for tipo_item, ast, _ in itens if tipo_item == "comando"]
    for n, ast in enumerate(comandos, start=1):
        print(f"\n--- Comando {n} (linha {ast['linha']}) ---")
        print(ast["classe"])
        print("\n".join(imprimir_arvore(ast)))
    pulados = len(itens) - len(comandos)
    print(f"\n{len(comandos)} comando(s) da gramática; {pulados} trecho(s) Java fora da gramática "
          f"(class, if, for, chamadas...) pulado(s) sem erro.")
    print(f"\nErros sintáticos ({len(erros_sintaticos)}):")
    print("\n".join(erros_sintaticos) or "Nenhum erro sintático.")

    titulo(f"5. ERROS SEMÂNTICOS ({len(erros_semanticos)})")
    print("\n".join(erros_semanticos) or "Nenhum erro semântico.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as erro:                          # nunca mostrar traceback na apresentação
        print(f"[ERRO INESPERADO] {erro}")
        sys.exit(1)
