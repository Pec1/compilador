import sys
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

if __name__ == "__main__" and not __package__:
    # Permite rodar também como "python src/main.py arquivo.java"
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "src"

from .tokens import Token
from .lexer import Lexer, LexicalError
from .parser import Parser, SyntacticError
from .symbol_table import SymbolTable
from .semantic import SemanticAnalyzer
from .ast_nodes import Program, set_ascii_tree

GRAMMAR = """\
<Comando>     ::= <Declaracao> | <Atribuicao>
<Declaracao>  ::= <Tipo> <ID> ["=" <Expressao>]
                  ("," <ID> ["=" <Expressao>])* ";"
<Atribuicao>  ::= <ID> "=" <Expressao> ";"
<Expressao>   ::= <Termo> (("+" | "-") <Termo>)*
<Termo>       ::= <Fator> (("*" | "/" | "%") <Fator>)*
<Fator>       ::= "-" <Fator> | ID | NUM | STRING | CHAR | BOOL | null
                | "(" <Expressao> ")\""""

WIDTH = 78


@dataclass
class AnalysisResult:
    """Resultado estruturado e unificado da execução do pipeline do compilador."""
    source: str
    tokens: List[Token] = field(default_factory=list)
    lexical_errors: List[LexicalError] = field(default_factory=list)
    symbol_table: Optional[SymbolTable] = None
    ast: Optional[Program] = None
    syntax_errors: List[SyntacticError] = field(default_factory=list)
    semantic_errors: List[str] = field(default_factory=list)
    success: bool = False

    @property
    def ignored(self):
        return [i for i in self.ast.ignored if not i.is_error] if self.ast else []

    @property
    def has_errors(self) -> bool:
        return bool(self.lexical_errors or self.syntax_errors or self.semantic_errors)


def analyze_source(source: str) -> AnalysisResult:
    """Executa o pipeline completo do compilador sobre uma string e retorna um AnalysisResult."""
    if source is None:
        source = ""
    result = AnalysisResult(source=source)

    # 1. Análise Léxica: tokens + erros léxicos (não interrompe a análise)
    lexer = Lexer(source)
    result.tokens = lexer.tokenize()
    result.lexical_errors = lexer.errors

    # 2. Tabela de Símbolos: construída na ordem de ocorrência dos tokens
    symbols = SymbolTable()
    symbols.build_from_tokens(result.tokens)
    result.symbol_table = symbols

    # 3. Análise Sintática: AST dos comandos da gramática; o resto é ignorado com aviso
    parser = Parser(result.tokens)
    result.ast = parser.parse()
    result.syntax_errors = parser.errors
    for name, type_name in parser.symbol_types.items():
        symbols.set_type(name, type_name)
    symbols.mark_api_classes()

    # 4. Análise Semântica
    analyzer = SemanticAnalyzer(symbols)
    try:
        result.semantic_errors = analyzer.analyze(result.ast)
    except RecursionError:
        result.semantic_errors = analyzer.errors + ["[ERRO SEMÂNTICO] Expressão aninhada demais para ser analisada."]

    result.success = not result.has_errors
    return result


def setup_console_encoding():
    """Garante suporte a UTF-8 no stdout/stderr no Windows sem falhas de codificação."""
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def decode_source(data: bytes):
    """Decodifica o arquivo: UTF-8 (com ou sem BOM) e, se falhar, Windows-1252 / Latin-1."""
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace"), "latin-1"


def read_source_file(path_str, with_encoding=False):
    """Lê o arquivo fonte de forma segura, tratando erros de entrada."""
    def out(content, error, encoding=None):
        return (content, error, encoding) if with_encoding else (content, error)

    if path_str is None or not str(path_str).strip():
        return out(None, "[ERRO DE ENTRADA] Caminho do arquivo não pode ser vazio.")
    try:
        path = Path(path_str)
        if not path.exists():
            return out(None, f"[ERRO DE ENTRADA] Arquivo não encontrado: '{path_str}'.\n"
                             f"Verifique o caminho. Pasta atual: {Path.cwd()}")
        if path.is_dir():
            return out(None, f"[ERRO DE ENTRADA] O caminho informado é um diretório, não um arquivo: '{path_str}'.")
        content, encoding = decode_source(path.read_bytes())
        return out(content, None, encoding)
    except PermissionError:
        return out(None, f"[ERRO DE ENTRADA] Permissão negada ao tentar ler o arquivo: '{path_str}'.")
    except OSError as e:
        return out(None, f"[ERRO DE ENTRADA] Erro ao acessar o arquivo '{path_str}': {e}.")


# -------------------------------------------------------------------
# Impressão do relatório em seções
# -------------------------------------------------------------------
def section(title):
    print()
    print("=" * WIDTH)
    print(f" {title}")
    print("=" * WIDTH)


def print_source(source):
    lines = source.splitlines()
    if not source.strip():
        print("(arquivo vazio)")
        return
    width = len(str(len(lines)))
    for n, text in enumerate(lines, start=1):
        print(f"{n:>{width}} | {text}")


def print_tokens(tokens):
    lex_w = min(max([len(t.lexeme) for t in tokens] + [6]), 40)
    print(f"{'#':>5}  {'Lin:Col':<9}{'Tipo':<17}{'Lexema':<{lex_w}}")
    print("-" * (5 + 2 + 9 + 17 + lex_w))
    for i, t in enumerate(tokens, start=1):
        lexeme = t.lexeme if t.lexeme else "<fim de arquivo>"
        if len(lexeme) > 40:
            lexeme = lexeme[:37] + "..."
        lexeme = lexeme.replace("\n", "\\n")
        print(f"{i:>5}  {f'{t.line}:{t.column}':<9}{t.type.name:<17}{lexeme}")


def format_ast(program, as_json=False):
    """Texto da seção de AST (usado pela linha de comando e pela interface gráfica)."""
    out = ["Gramática reconhecida (GLC restrita):"]
    out += ["   " + line for line in GRAMMAR.splitlines()]
    out.append("")
    commands = program.commands
    if as_json:
        out.append(json.dumps(program.to_dict(), ensure_ascii=False, indent=2))
    elif not commands:
        out.append("(nenhum comando da gramática encontrado)")
    else:
        out.append(f"Comandos reconhecidos: {len(commands)}")
        for n, cmd in enumerate(commands, start=1):
            out += ["", f"--- Comando {n} (linha {cmd.line}) ---", cmd.pretty()]
    return "\n".join(out)


def format_ignored(ignored):
    if not ignored:
        return ""
    out = ["", f"Trechos Java fora da gramática restrita (ignorados pelo parser): {len(ignored)}"]
    for item in ignored:
        text = item.text if len(item.text) <= 52 else item.text[:49] + "..."
        out.append(f"   linha {item.line:>3}: {text}")
    return "\n".join(out)


def run_file(path, as_json=False, show_source=True):
    """Executa o pipeline completo do compilador de forma controlada via CLI."""
    setup_console_encoding()
    source, error, encoding = read_source_file(path, with_encoding=True)
    if error:
        print(error)
        return 1

    result = analyze_source(source)

    print("=" * WIDTH)
    print(" COMPILADOR AV3 - Analisador Léxico, Sintático e Semântico de Java")
    print(f" Arquivo: {path}   (codificação: {encoding})")
    print("=" * WIDTH)

    if show_source:
        section("CÓDIGO FONTE")
        print_source(source)

    section(f"1. TOKENS  ({len(result.tokens)} tokens)")
    print_tokens(result.tokens)

    section(f"2. TABELA DE SÍMBOLOS  ({len(result.symbol_table.all())} símbolos, em ordem de inserção)")
    result.symbol_table.print_table()

    section(f"3. ERROS LÉXICOS  ({len(result.lexical_errors)})")
    if result.lexical_errors:
        for err in result.lexical_errors:
            print(err)
    else:
        print("[OK] Nenhum erro léxico.")

    section("4. ANÁLISE SINTÁTICA / AST")
    print(format_ast(result.ast, as_json=as_json))
    if result.ignored:
        print(format_ignored(result.ignored))
    print()
    if result.syntax_errors:
        print(f"Erros sintáticos ({len(result.syntax_errors)}):")
        for err in result.syntax_errors:
            print(err)
    else:
        print("[OK] Nenhum erro sintático nos comandos da gramática.")

    section(f"5. ERROS SEMÂNTICOS  ({len(result.semantic_errors)})")
    if result.semantic_errors:
        for err in result.semantic_errors:
            print(err)
    else:
        print("[OK] Nenhum erro semântico.")

    print()
    print("=" * WIDTH)
    print(f" RESUMO: {len(result.tokens)} tokens | {len(result.symbol_table.all())} símbolos | "
          f"{len(result.ast.commands)} comandos na AST")
    print(f"         erros: {len(result.lexical_errors)} léxico(s), "
          f"{len(result.syntax_errors)} sintático(s), {len(result.semantic_errors)} semântico(s)")
    print("=" * WIDTH)
    return 1 if result.has_errors else 0


USAGE = """Uso: python main.py <arquivo.java> [--json] [--ascii] [--sem-fonte]
   --json       exibe a AST em formato JSON
   --ascii      desenha a árvore só com caracteres ASCII (terminais sem UTF-8)
   --sem-fonte  não reimprime o código fonte"""


def main(argv=None):
    setup_console_encoding()
    args = list(sys.argv[1:] if argv is None else argv)
    flags = {a for a in args if a.startswith("--")}
    files = [a for a in args if not a.startswith("--")]
    if "--help" in flags or len(files) != 1:
        if "--help" not in flags:
            print("[ERRO DE ENTRADA] Informe exatamente um arquivo fonte.")
        print(USAGE)
        return 1
    try:
        set_ascii_tree("--ascii" in flags)
        return run_file(files[0], as_json="--json" in flags, show_source="--sem-fonte" not in flags)
    except KeyboardInterrupt:
        return 1
    except Exception as exc:
        print(f"\n[ERRO INESPERADO] {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
