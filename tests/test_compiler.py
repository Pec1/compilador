import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.tokens import TokenType
from src.lexer import Lexer
from src.parser import Parser
from src.ast_nodes import Declaration, Assignment, BinaryOp, set_ascii_tree
from src.main import analyze_source, read_source_file, main

TESTES = ROOT / "testes"


def lex(src):
    lexer = Lexer(src)
    tokens = lexer.tokenize()
    return [(t.type, t.lexeme) for t in tokens[:-1]], lexer.errors


def semantic(src):
    return [str(e) for e in analyze_source(src).semantic_errors]


class TestLexico(unittest.TestCase):
    def test_atribuicao_barema(self):
        tokens, errors = lex("x = a + 5;")
        self.assertEqual(tokens, [
            (TokenType.IDENTIFIER, "x"), (TokenType.ASSIGN, "="), (TokenType.IDENTIFIER, "a"),
            (TokenType.PLUS, "+"), (TokenType.NUMBER, "5"), (TokenType.SEMICOLON, ";")])
        self.assertEqual(errors, [])

    def test_palavras_reservadas_e_literais(self):
        tokens, _ = lex("public class X true null String")
        self.assertEqual([t for t, _ in tokens], [TokenType.KEYWORD, TokenType.KEYWORD, TokenType.IDENTIFIER,
                                                  TokenType.BOOLEAN_LITERAL, TokenType.NULL_LITERAL,
                                                  TokenType.IDENTIFIER])

    def test_numeros(self):
        for text in ["10", "3.14", "3.14f", "10L", "0x1F", "1e10", "1_000", ".5", "1e-3", "2.0d", "0b1010", "0xFFL"]:
            tokens, errors = lex(text)
            self.assertEqual(tokens, [(TokenType.NUMBER, text)], text)
            self.assertEqual(errors, [], text)

    def test_numero_no_fim_do_arquivo_sem_quebra(self):
        tokens, errors = lex("x = 5")
        self.assertEqual(tokens[-1], (TokenType.NUMBER, "5"))
        self.assertEqual(errors, [])

    def test_operadores_maior_casamento(self):
        ops = "== != <= >= && || ! ++ -- += -= *= /= ? : -> :: << >> >>> >>= >>>= <<= %= ..."
        tokens, errors = lex(ops)
        self.assertEqual([lx for _, lx in tokens], ops.split())
        self.assertEqual(errors, [])

    def test_instanceof_e_keyword(self):
        tokens, _ = lex("a instanceof String")
        self.assertEqual(tokens[1], (TokenType.KEYWORD, "instanceof"))

    def test_strings_e_chars_com_escape(self):
        bs = "\\"
        src = f'"a{bs}"b{bs}n" ' + f"'a' '{bs}n' '{bs}'' '{bs}u0041'"
        tokens, errors = lex(src)
        self.assertEqual([t for t, _ in tokens], [TokenType.STRING_LITERAL] + [TokenType.CHAR_LITERAL] * 4)
        self.assertEqual(tokens[0][1], r'"a\"b\n"')
        self.assertEqual(errors, [])

    def test_text_block(self):
        tokens, errors = lex('String s = """\n  ola\n  """;')
        self.assertEqual(tokens[3][0], TokenType.STRING_LITERAL)
        self.assertEqual(errors, [])

    def test_comentarios_sao_descartados(self):
        tokens, errors = lex("// linha\n/* bloco\n multi */ /** javadoc */ int x;")
        self.assertEqual([lx for _, lx in tokens], ["int", "x", ";"])
        self.assertEqual(errors, [])

    def test_linha_e_coluna(self):
        tokens = Lexer("int x;\n  x = 1;").tokenize()
        self.assertEqual((tokens[3].line, tokens[3].column), (2, 3))

    def test_crlf(self):
        tokens = Lexer("int x;\r\nx = 1;\r\n").tokenize()
        self.assertEqual(tokens[3].line, 2)

    def test_acentos_em_identificadores_e_strings(self):
        tokens, errors = lex('int número = 1; String s = "ação ✓";')
        self.assertIn((TokenType.IDENTIFIER, "número"), tokens)
        self.assertEqual(errors, [])

    def test_erro_lexico_continua(self):
        tokens, errors = lex("int a = 1 # 2;\nint b = `3`;")
        self.assertEqual(len(errors), 3)
        self.assertEqual((errors[0].line, errors[0].column), (1, 11))
        self.assertIn("[ERRO LÉXICO] Linha 1, coluna 11", str(errors[0]))
        self.assertIn((TokenType.IDENTIFIER, "b"), tokens)

    def test_string_nao_fechada_continua(self):
        tokens, errors = lex('String s = "abc;\nint d = 5;')
        self.assertEqual(len(errors), 1)
        self.assertIn("String não fechada", str(errors[0]))
        self.assertIn((TokenType.IDENTIFIER, "d"), tokens)

    def test_comentario_nao_fechado(self):
        _, errors = lex("int x; /* sem fim")
        self.assertEqual(len(errors), 1)

    def test_char_invalido(self):
        _, errors = lex("char c = ''; char d = 'ab';")
        self.assertEqual(len(errors), 2)

    def test_numero_malformado(self):
        _, errors = lex("int x = 12abc;")
        self.assertEqual(len(errors), 1)

    def test_entradas_vazias(self):
        for src in ["", "   ", "\n\n\n", "\t" * 1000, None]:
            tokens = Lexer(src).tokenize()
            self.assertEqual(tokens[-1].type, TokenType.EOF)


class TestTabelaDeSimbolos(unittest.TestCase):
    def test_ordem_categoria_tipo_linha(self):
        r = analyze_source("public class A {\n int x = 1;\n String s;\n}")
        rows = [(s["order"], s["name"], s["category"], s["type"], s["line"]) for s in r.symbol_table.all()]
        self.assertEqual(rows, [
            (1, "public", "palavra reservada", "-", 1),
            (2, "class", "palavra reservada", "-", 1),
            (3, "A", "identificador", "classe", 1),
            (4, "int", "palavra reservada", "tipo primitivo", 2),
            (5, "x", "identificador", "int", 2),
            (6, "String", "identificador", "classe (API Java)", 3),
            (7, "s", "identificador", "String", 3),
        ])

    def test_sem_duplicacao(self):
        r = analyze_source("int x; int y; x = y;")
        names = [s["name"] for s in r.symbol_table.all()]
        self.assertEqual(names, ["int", "x", "y"])

    def test_metodo_e_parametro(self):
        r = analyze_source("class A { static int soma(int a, int b) { return a + b; } }")
        types = {s["name"]: s["type"] for s in r.symbol_table.all()}
        self.assertEqual(types["soma"], "método (int)")
        self.assertEqual(types["a"], "int (parâmetro)")

    def test_tabela_existe_mesmo_com_erros(self):
        r = analyze_source("int x = # ;")
        self.assertTrue(r.symbol_table.all())


class TestSintatico(unittest.TestCase):
    def test_ast_formato_barema(self):
        set_ascii_tree(False)
        r = analyze_source("int x, a;\nx = a + 5;")
        self.assertEqual(r.ast.commands[2].pretty(), "\n".join([
            "Atribuicao",
            "├── ID (x)",
            "├── OP_ATRIB (=)",
            "└── Expressao (+)",
            "    ├── ID (a)",
            "    └── NUM (5)",
        ]))

    def test_ast_ascii(self):
        set_ascii_tree(True)
        try:
            r = analyze_source("x = a + 5;")
            self.assertIn("|-- ID (x)", r.ast.commands[0].pretty())
        finally:
            set_ascii_tree(False)

    def test_declaracao_multipla(self):
        r = analyze_source("int x, y = 2, z;")
        self.assertEqual([(c.name, c.initializer is not None) for c in r.ast.commands],
                         [("x", False), ("y", True), ("z", False)])

    def test_precedencia(self):
        r = analyze_source("int r = 1 + 2 * 3;")
        expr = r.ast.commands[0].initializer
        self.assertIsInstance(expr, BinaryOp)
        self.assertEqual(expr.op, "+")
        self.assertEqual(expr.right.op, "*")

    def test_parenteses_e_unario(self):
        r = analyze_source("int r = -(1 + 2) % 4;")
        self.assertEqual(r.syntax_errors, [])
        self.assertEqual(len(r.ast.commands), 1)

    def test_java_completo_nao_aborta(self):
        r = analyze_source((TESTES / "Completo.java").read_text(encoding="utf-8"))
        self.assertEqual(r.syntax_errors, [])
        self.assertEqual(r.semantic_errors, [])
        self.assertGreater(len(r.ast.commands), 3)
        self.assertGreater(len(r.ignored), 10)

    def test_avancado_sem_erros_falsos(self):
        r = analyze_source((TESTES / "Avancado.java").read_text(encoding="utf-8"))
        self.assertEqual((r.lexical_errors, r.syntax_errors, r.semantic_errors), ([], [], []))

    def test_ponto_e_virgula_esquecido(self):
        r = analyze_source("int x = 5\nx = 3;")
        self.assertEqual(len(r.syntax_errors), 1)
        self.assertIn("';'", str(r.syntax_errors[0]))
        self.assertEqual(len(r.ast.commands), 2)

    def test_erros_sintaticos_reais(self):
        for src in ["x = ;", "int = 5;", "x = (a + 5;", "x = a b;", "x = * 5;", "int x = 1 2;"]:
            r = analyze_source(src)
            self.assertTrue(r.syntax_errors, src)

    def test_chave_nao_fechada(self):
        r = analyze_source("class A { int x;")
        self.assertEqual(len(r.syntax_errors), 1)

    def test_progresso_garantido(self):
        for src in ["}}}", "{{{", ")))", "= = =", "int int int", "@@@", "case default:", "else else"]:
            r = analyze_source(src)
            self.assertIsNotNone(r.ast)

    def test_expressao_gigante_nao_estoura(self):
        analyze_source("int x = " + " + ".join(["1"] * 20000) + ";")
        analyze_source("int x = " + "(" * 5000 + "1" + ")" * 5000 + ";")
        analyze_source("int x = " + "-" * 5000 + "1;")


class TestSemantico(unittest.TestCase):
    def test_mensagem_tipo_barema(self):
        self.assertEqual(semantic('int resultado = "texto";'), [
            "[ERRO SEMÂNTICO] Incompatibilidade de tipos na linha 1: Não é possível atribuir String a um tipo int."])

    def test_mensagem_nao_declarada_barema(self):
        self.assertEqual(semantic("\n\ntotal = 10;"), [
            "[ERRO SEMÂNTICO] Variável 'total' utilizada na linha 3 não foi declarada previamente."])

    def test_barema_java(self):
        errors = [str(e) for e in analyze_source((TESTES / "Barema.java").read_text(encoding="utf-8")).semantic_errors]
        self.assertEqual(errors, [
            "[ERRO SEMÂNTICO] Incompatibilidade de tipos na linha 6: Não é possível atribuir String a um tipo int.",
            "[ERRO SEMÂNTICO] Variável 'total' utilizada na linha 7 não foi declarada previamente.",
        ])

    def test_uso_antes_da_declaracao(self):
        self.assertEqual(len(semantic("total = 10; int total;")), 1)

    def test_variavel_em_expressao(self):
        self.assertEqual(len(semantic("int x = y + 1;")), 1)

    def test_conversoes_validas(self):
        ok = ["long l = 5;", "double d = 1;", "float f = 2.5f;", "char c = 65;", "int i = 'a';",
              'String s = "a" + 1;', "String s = null;", "double d = 1 + 2.5;", "byte b = 10;"]
        for src in ok:
            self.assertEqual(semantic(src), [], src)

    def test_conversoes_invalidas(self):
        bad = ["int x = 2.5;", "float f = 2.5;", "boolean b = 1;", "int x = true;", 'int x = "a" + 1;',
               "int x = null;", "long l = 1.0;", "String s = 5;", "char c = 1.5;"]
        for src in bad:
            self.assertEqual(len(semantic(src)), 1, src)

    def test_operacao_com_string(self):
        errors = semantic('String s = "a"; int x = s - 1;')
        self.assertIn("Operação '-' inválida", errors[0])

    def test_declaracao_duplicada(self):
        errors = semantic("int x; int x;")
        self.assertIn("já havia sido declarada", errors[0])

    def test_escopos_sem_falso_positivo(self):
        src = """class A {
            int f(int n) { n = n * 2; return n; }
            void g() {
                for (int i = 0; i < 3; i++) { int t = i; t = t + campo; }
                for (int i = 0; i < 3; i++) { int t = i; }
            }
            static int campo = 1;
        }"""
        self.assertEqual(semantic(src), [])

    def test_escopo_fechado(self):
        errors = semantic("class A { void f() { int x = 1; } void g() { x = 2; } }")
        self.assertEqual(len(errors), 1)


class TestEntradaECli(unittest.TestCase):
    def run_cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(args))
        return code, buf.getvalue()

    def test_arquivo_inexistente(self):
        code, out = self.run_cli("nao_existe.java")
        self.assertEqual(code, 1)
        self.assertIn("Arquivo não encontrado", out)

    def test_sem_argumentos(self):
        code, out = self.run_cli()
        self.assertIn("Uso:", out)

    def test_diretorio(self):
        _, out = self.run_cli(str(TESTES))
        self.assertIn("diretório", out)

    def test_cp1252(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "A.java"
            p.write_bytes('String s = "ação";'.encode("cp1252"))
            content, err = read_source_file(str(p))
            self.assertIsNone(err)
            self.assertIn("ação", content)

    def test_bom(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "A.java"
            p.write_bytes(b"\xef\xbb\xbfint x;")
            content, _ = read_source_file(str(p))
            self.assertEqual(content, "int x;")

    def test_secoes_na_saida(self):
        _, out = self.run_cli(str(TESTES / "Barema.java"))
        for title in ["TOKENS", "TABELA DE SÍMBOLOS", "ERROS LÉXICOS", "AST", "ERROS SEMÂNTICOS"]:
            self.assertIn(title, out)

    def test_json(self):
        _, out = self.run_cli(str(TESTES / "Simples.java"), "--json")
        self.assertIn('"no": "Atribuicao"', out)

    def test_todos_os_arquivos_de_teste(self):
        for path in TESTES.glob("*.java"):
            code, out = self.run_cli(str(path), "--sem-fonte")
            self.assertIn("RESUMO", out, path.name)
            self.assertNotIn("ERRO INESPERADO", out, path.name)


class TestGui(unittest.TestCase):
    def test_gui_ciclo_completo(self):
        try:
            from src.gui import CompiladorGUI
            app = CompiladorGUI()
        except Exception as exc:
            self.skipTest(f"Tkinter indisponível: {exc}")
        try:
            app.withdraw()
            app.editor.insert("1.0", (TESTES / "Barema.java").read_text(encoding="utf-8"))
            app.on_analyze()
            self.assertEqual(len(app.tokens_tree.get_children()), 42)
            self.assertIn("não foi declarada previamente", app.errors_text.get("1.0", "end"))
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()
