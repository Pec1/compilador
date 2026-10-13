from .tokens import Token, TokenType
from .lexer import PRIMITIVE_TYPES
from .ast_nodes import (Program, Declaration, Assignment, BinaryOp, UnaryOp, Literal, Identifier,
                        Ignored, VarInfo)

# Modificadores aceitos antes de uma declaração (ex.: private static final int X = 10;)
MODIFIERS = {"public", "private", "protected", "static", "final", "transient", "volatile"}

# Comandos de controle cujo cabeçalho "( ... )" é pulado como um bloco só
CONTROL_HEADERS = {"if", "for", "while", "switch", "catch", "synchronized", "try"}

# Palavras que normalmente iniciam um comando (usadas para detectar ';' esquecido no fim da linha)
STATEMENT_KEYWORDS = PRIMITIVE_TYPES | {
    "if", "for", "while", "do", "return", "switch", "try", "throw", "break", "continue",
    "else", "final", "public", "private", "protected", "static", "class", "case", "default",
}

OPERAND_TYPES = {
    TokenType.IDENTIFIER, TokenType.NUMBER, TokenType.STRING_LITERAL, TokenType.CHAR_LITERAL,
    TokenType.BOOLEAN_LITERAL, TokenType.NULL_LITERAL,
}

LITERAL_KINDS = {
    TokenType.NUMBER: "NUM",
    TokenType.STRING_LITERAL: "STRING",
    TokenType.CHAR_LITERAL: "CHAR",
    TokenType.BOOLEAN_LITERAL: "BOOL",
    TokenType.NULL_LITERAL: "NULL",
}

# Tokens que, logo após uma expressão, indicam Java válido porém fora da gramática restrita
CONTINUATION_TYPES = {
    TokenType.DOT, TokenType.LPAREN, TokenType.LBRACKET, TokenType.QUESTION, TokenType.COLON,
    TokenType.EQ, TokenType.NE, TokenType.LT, TokenType.GT, TokenType.LE, TokenType.GE,
    TokenType.AND, TokenType.OR, TokenType.BIT_AND, TokenType.BIT_OR, TokenType.BIT_XOR,
    TokenType.LSHIFT, TokenType.RSHIFT, TokenType.URSHIFT, TokenType.INCREMENT, TokenType.DECREMENT,
    TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN, TokenType.MULT_ASSIGN,
    TokenType.DIV_ASSIGN, TokenType.MOD_ASSIGN, TokenType.AND_ASSIGN, TokenType.OR_ASSIGN,
    TokenType.XOR_ASSIGN, TokenType.LSHIFT_ASSIGN, TokenType.RSHIFT_ASSIGN, TokenType.URSHIFT_ASSIGN,
    TokenType.ARROW, TokenType.DOUBLE_COLON,
}

# Tokens permitidos dentro de argumentos genéricos: List<String>, Map<String, List<Integer>>
GENERIC_TYPES = {
    TokenType.IDENTIFIER, TokenType.COMMA, TokenType.DOT, TokenType.QUESTION, TokenType.LBRACKET,
    TokenType.RBRACKET, TokenType.LT, TokenType.GT, TokenType.RSHIFT, TokenType.URSHIFT, TokenType.BIT_AND,
}


class SyntacticError(Exception):
    """Exceção estruturada para erros sintáticos."""
    def __init__(self, message: str, line: int, column: int, expected: str = None, found: str = None, token=None):
        self.message = message
        self.line = line
        self.column = column
        self.expected = expected
        self.found = found
        self.token = token
        super().__init__(self._format_message())

    def _format_message(self):
        text = f"Era esperado {self.expected}." if self.expected else f"{self.message}."
        if self.found is not None:
            if self.found in ("EOF", ""):
                text += " Encontrado: fim de arquivo (EOF)."
            else:
                text += f" Encontrado: '{self.found}'."
        return f"[ERRO SINTÁTICO] Linha {self.line}, coluna {self.column}: {text}"


class Parser:
    """Parser descendente recursivo para a gramática restrita (ver GRAMMAR em main.py).

    Reconhece declarações e atribuições em qualquer ponto do arquivo Java.
    Construções Java fora da gramática (class, métodos, if, for, chamadas...) são
    puladas até ';', '{' ou '}' e registradas como trechos ignorados, sem abortar.
    """
    def __init__(self, tokens):
        self.tokens = list(tokens) if tokens is not None else []
        if not self.tokens or self.tokens[-1].type != TokenType.EOF:
            last = self.tokens[-1] if self.tokens else None
            self.tokens.append(Token(TokenType.EOF, "", last.line if last else 1, last.column if last else 1))
        self.current = 0
        self.depth = 0
        self.max_depth = 200
        self.max_operators = 300
        self.operators = 0
        self.statements = []
        self.errors = []
        self.scope_stack = []
        self.next_scope_id = 0
        self.class_scopes = set()
        self.symbol_types = {}     # nome -> tipo declarado (alimenta a tabela de símbolos)
        self.pending_decls = []

    # ---------------------------------------------------------------
    # Navegação nos tokens
    # ---------------------------------------------------------------
    def tok(self, index):
        return self.tokens[min(index, len(self.tokens) - 1)]

    def peek(self, offset=0):
        return self.tok(self.current + offset)

    def previous(self):
        return self.tok(max(self.current - 1, 0))

    def advance(self):
        token = self.peek()
        if self.current < len(self.tokens) - 1:
            self.current += 1
        return token

    def check(self, token_type, lexeme=None):
        t = self.peek()
        return t.type == token_type and (lexeme is None or t.lexeme == lexeme)

    def error_here(self, expected):
        t = self.peek()
        found = t.lexeme if t.type != TokenType.EOF else "EOF"
        return SyntacticError(f"Era esperado {expected}", t.line, t.column, expected=expected, found=found, token=t)

    def expect(self, token_type, expected):
        if not self.check(token_type):
            raise self.error_here(expected)
        return self.advance()

    # ---------------------------------------------------------------
    # Escopos (blocos { }) e tipos para a tabela de símbolos
    # ---------------------------------------------------------------
    def current_scope(self):
        return tuple(self.scope_stack)

    def push_scope(self, is_class=False):
        self.next_scope_id += 1
        self.scope_stack.append(self.next_scope_id)
        if is_class:
            self.class_scopes.add(self.next_scope_id)
        return self.current_scope()

    def declare_symbol(self, name, type_name):
        self.symbol_types.setdefault(name, type_name)

    # ---------------------------------------------------------------
    # <Programa> ::= <Comando>*
    # ---------------------------------------------------------------
    def parse(self):
        while not self.check(TokenType.EOF):
            start = self.current
            self.pending_decls = []
            self.operators = 0
            try:
                self.statement()
            except SyntacticError as err:
                self.recover(start, err)
            except RecursionError:
                err = self.error_here("expressão com profundidade suportada")
                self.recover(start, err)
            if self.current == start:
                self.advance()  # garantia de progresso
        if self.scope_stack:
            t = self.peek()
            self.errors.append(SyntacticError(
                "", t.line, t.column,
                expected=f"'}}' para fechar {len(self.scope_stack)} bloco(s) aberto(s)", found="EOF", token=t))
        return Program(self.statements, set(self.class_scopes))

    def statement(self):
        t = self.peek()
        if t.type == TokenType.RBRACE:
            self.advance()
            if self.scope_stack:
                self.scope_stack.pop()
            else:
                self.errors.append(SyntacticError("'}' sem '{' correspondente", t.line, t.column, found="}", token=t))
            return
        if t.type == TokenType.LBRACE:
            self.advance()
            self.push_scope()
            return
        if t.type == TokenType.SEMICOLON:
            self.advance()
            return
        if self.is_declaration_start():
            self.declaration()
            return
        if t.type == TokenType.IDENTIFIER and self.peek(1).type == TokenType.ASSIGN:
            self.assignment()
            return
        if t.type == TokenType.KEYWORD and t.lexeme in PRIMITIVE_TYPES and self.peek(1).type not in (
                TokenType.DOT, TokenType.LBRACKET, TokenType.IDENTIFIER):
            # "int = 5;" ou "int 5;": tipo primitivo sem identificador é erro de sintaxe
            self.advance()
            err = self.error_here(f"um identificador após o tipo '{t.lexeme}'")
            err.real = True
            raise err
        self.skip_construct()

    # ---------------------------------------------------------------
    # Reconhecimento de tipos: int, String, int[], List<String>, java.util.Map<K, V>
    # ---------------------------------------------------------------
    def match_type(self, i, allow_void=False):
        t = self.tok(i)
        if t.type == TokenType.KEYWORD and (t.lexeme in PRIMITIVE_TYPES or (allow_void and t.lexeme == "void")):
            parts = [t.lexeme]
            i += 1
        elif t.type == TokenType.IDENTIFIER:
            parts = [t.lexeme]
            i += 1
            while self.tok(i).type == TokenType.DOT and self.tok(i + 1).type == TokenType.IDENTIFIER:
                parts.append("." + self.tok(i + 1).lexeme)
                i += 2
            if self.tok(i).type == TokenType.LT:
                generic = self.match_generic(i)
                if generic is None:
                    return None
                i, text = generic
                parts.append(text)
        else:
            return None
        while self.tok(i).type == TokenType.LBRACKET and self.tok(i + 1).type == TokenType.RBRACKET:
            parts.append("[]")
            i += 2
        if self.tok(i).type == TokenType.ELLIPSIS:
            parts.append("...")
            i += 1
        return i, "".join(parts)

    def match_generic(self, i):
        depth = 0
        text = []
        while True:
            t = self.tok(i)
            if t.type == TokenType.LT:
                depth += 1
            elif t.type == TokenType.GT:
                depth -= 1
            elif t.type == TokenType.RSHIFT:
                depth -= 2
            elif t.type == TokenType.URSHIFT:
                depth -= 3
            elif t.type == TokenType.KEYWORD and t.lexeme in PRIMITIVE_TYPES | {"extends", "super"}:
                pass
            elif t.type not in GENERIC_TYPES:
                return None
            if t.type == TokenType.COMMA:
                text.append(", ")
            elif t.lexeme in ("extends", "super"):
                text.append(f" {t.lexeme} ")
            else:
                text.append(t.lexeme)
            i += 1
            if depth == 0:
                return i, "".join(text)
            if depth < 0:
                return None

    def is_declaration_start(self):
        i = self.current
        while self.tok(i).type == TokenType.KEYWORD and self.tok(i).lexeme in MODIFIERS:
            i += 1
        result = self.match_type(i)
        if result is None:
            return False
        j, _ = result
        return (self.tok(j).type == TokenType.IDENTIFIER
                and self.tok(j + 1).type in (TokenType.ASSIGN, TokenType.SEMICOLON, TokenType.COMMA))

    # ---------------------------------------------------------------
    # <Declaracao> ::= <Tipo> <ID> ["=" <Expressao>] ("," <ID> ["=" <Expressao>])* ";"
    # ---------------------------------------------------------------
    def declaration(self):
        while self.check(TokenType.KEYWORD) and self.peek().lexeme in MODIFIERS:
            self.advance()
        end, type_name = self.match_type(self.current)
        self.current = end
        while True:
            name_tok = self.expect(TokenType.IDENTIFIER, "um identificador após o tipo")
            self.declare_symbol(name_tok.lexeme, type_name)
            self.pending_decls = [VarInfo(name_tok.lexeme, type_name, name_tok.line, "variavel",
                                         self.current_scope(), explicit=True)]
            initializer = None
            if self.check(TokenType.ASSIGN):
                self.advance()
                initializer = self.expression()
            if not self.check(TokenType.COMMA):
                self.expect_semicolon("';' ao final da declaração")
            self.pending_decls = []
            self.statements.append(Declaration(type_name, name_tok.lexeme, name_tok.line, initializer,
                                               column=name_tok.column, scope=self.current_scope()))
            if self.check(TokenType.COMMA):
                self.advance()
                continue
            return

    # ---------------------------------------------------------------
    # <Atribuicao> ::= <ID> "=" <Expressao> ";"
    # ---------------------------------------------------------------
    def assignment(self):
        name_tok = self.advance()
        self.advance()  # '='
        expr = self.expression()
        self.expect_semicolon("';' ao final da atribuição")
        self.statements.append(Assignment(name_tok.lexeme, name_tok.line, expr,
                                          column=name_tok.column, scope=self.current_scope()))

    def expect_semicolon(self, expected):
        if self.check(TokenType.SEMICOLON):
            self.advance()
            return
        t, prev = self.peek(), self.previous()
        # ';' esquecido no fim da linha: registra o erro e aceita o comando
        if t.type in (TokenType.EOF, TokenType.RBRACE) or (t.line > prev.line and t.type not in CONTINUATION_TYPES):
            self.errors.append(SyntacticError("", prev.line, prev.column + len(prev.lexeme), expected=expected,
                                              found=t.lexeme if t.type != TokenType.EOF else "EOF", token=t))
            return
        raise self.error_here(expected)

    # ---------------------------------------------------------------
    # <Expressao> ::= <Termo> (("+" | "-") <Termo>)*
    # <Termo>     ::= <Fator> (("*" | "/" | "%") <Fator>)*
    # <Fator>     ::= ("-" | "+") <Fator> | ID | NUM | STRING | CHAR | BOOL | NULL | "(" <Expressao> ")"
    # ---------------------------------------------------------------
    def count_operator(self):
        self.operators += 1
        if self.operators > self.max_operators:
            raise self.error_here(f"expressão com no máximo {self.max_operators} operadores")

    def expression(self):
        node = self.term()
        while self.check(TokenType.PLUS) or self.check(TokenType.MINUS):
            self.count_operator()
            op_tok = self.advance()
            right = self.term()
            node = BinaryOp(op_tok.lexeme, node, right, line=op_tok.line, column=op_tok.column)
        return node

    def term(self):
        node = self.factor()
        while self.check(TokenType.MULT) or self.check(TokenType.DIV) or self.check(TokenType.MOD):
            self.count_operator()
            op_tok = self.advance()
            right = self.factor()
            node = BinaryOp(op_tok.lexeme, node, right, line=op_tok.line, column=op_tok.column)
        return node

    def factor(self):
        t = self.peek()
        if t.type in (TokenType.MINUS, TokenType.PLUS):
            self.count_operator()
            self.advance()
            operand = self.factor()
            if t.type == TokenType.PLUS:
                return operand
            return UnaryOp("-", operand, line=t.line, column=t.column)
        if t.type == TokenType.IDENTIFIER:
            self.advance()
            return Identifier(t.lexeme, line=t.line, column=t.column)
        if t.type in LITERAL_KINDS:
            self.advance()
            return Literal(t.lexeme, LITERAL_KINDS[t.type], line=t.line, column=t.column)
        if t.type == TokenType.LPAREN:
            self.depth += 1
            if self.depth > self.max_depth:
                self.depth -= 1
                raise self.error_here(f"expressão com no máximo {self.max_depth} níveis de parênteses")
            try:
                self.advance()
                expr = self.expression()
                self.expect(TokenType.RPAREN, "')' para fechar a expressão")
                return expr
            finally:
                self.depth -= 1
        prev = self.previous()
        if prev.type in (TokenType.ASSIGN, TokenType.PLUS, TokenType.MINUS, TokenType.MULT, TokenType.DIV,
                         TokenType.MOD, TokenType.LPAREN):
            raise self.error_here(f"uma expressão após '{prev.lexeme}'")
        raise self.error_here("uma expressão")

    # ---------------------------------------------------------------
    # Recuperação de erros
    # ---------------------------------------------------------------
    def is_real_error(self, err):
        """Diferencia erro de sintaxe de Java válido que só está fora da gramática restrita."""
        t = err.token
        if t is None or getattr(err, "real", False):
            return True
        idx = self.tokens.index(t) if t in self.tokens else self.current
        prev = self.tok(max(idx - 1, 0))
        if t.type in (TokenType.SEMICOLON, TokenType.EOF, TokenType.RBRACE, TokenType.COMMA):
            return True
        if t.type in OPERAND_TYPES:
            return True
        if t.type in (TokenType.MULT, TokenType.DIV, TokenType.MOD):
            return True
        if t.type == TokenType.RPAREN and prev.type != TokenType.LPAREN:
            return True
        if t.type == TokenType.ASSIGN and prev.type == TokenType.ASSIGN:
            return True
        if t.line > prev.line and t.type == TokenType.KEYWORD and t.lexeme in STATEMENT_KEYWORDS:
            return True
        return False

    def recover(self, start, err):
        real = self.is_real_error(err)
        if real:
            self.errors.append(err)
        self.skip_statement_rest()
        reason = "erro sintático" if real else f"fora da gramática restrita (encontrado '{err.found}')"
        self.add_ignored(start, reason, self.current_scope(), list(self.pending_decls), is_error=real)
        self.pending_decls = []

    def skip_statement_rest(self):
        """Pula até o fim do comando atual (';' no nível 0), respeitando ( [ { aninhados."""
        depth = 0
        while not self.check(TokenType.EOF):
            t, prev = self.peek(), self.previous()
            if depth == 0:
                if t.type == TokenType.SEMICOLON:
                    self.advance()
                    return
                if t.type == TokenType.RBRACE:
                    return
                if t.line > prev.line and t.type == TokenType.KEYWORD and t.lexeme in STATEMENT_KEYWORDS:
                    return
            if t.type in (TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE):
                depth += 1
            elif t.type in (TokenType.RPAREN, TokenType.RBRACKET, TokenType.RBRACE):
                depth = max(depth - 1, 0)
            self.advance()

    def skip_balanced_parens(self):
        depth = 0
        while not self.check(TokenType.EOF):
            t = self.advance()
            if t.type == TokenType.LPAREN:
                depth += 1
            elif t.type == TokenType.RPAREN:
                depth -= 1
                if depth <= 0:
                    return

    def skip_construct(self):
        """Pula uma construção Java fora da gramática (cabeçalho de classe/método, if, for, chamada...)."""
        start = self.current
        first = self.peek()
        opens_block = False

        if first.type == TokenType.KEYWORD and first.lexeme == "else" and self.peek(1).lexeme == "if":
            self.advance()
            first = self.peek()

        if first.type == TokenType.KEYWORD and (first.lexeme == "case" or (
                first.lexeme == "default" and self.peek(1).type in (TokenType.COLON, TokenType.ARROW))):
            depth = 0
            while not self.check(TokenType.EOF):
                t = self.peek()
                if depth == 0 and t.type in (TokenType.SEMICOLON, TokenType.LBRACE, TokenType.RBRACE):
                    break
                self.advance()
                if t.type == TokenType.LPAREN:
                    depth += 1
                elif t.type == TokenType.RPAREN:
                    depth -= 1
                elif depth == 0 and t.type in (TokenType.COLON, TokenType.ARROW):
                    break
        elif first.type == TokenType.KEYWORD and first.lexeme in ("else", "do", "finally"):
            self.advance()
            if self.check(TokenType.LBRACE):
                self.advance()
                opens_block = True
        elif first.type == TokenType.KEYWORD and first.lexeme in CONTROL_HEADERS:
            self.advance()
            if self.check(TokenType.LPAREN):
                self.skip_balanced_parens()
            if self.check(TokenType.LBRACE):
                self.advance()
                opens_block = True
            elif self.check(TokenType.SEMICOLON):
                self.advance()
        else:
            depth = 0
            while not self.check(TokenType.EOF):
                t = self.peek()
                if depth == 0:
                    if t.type == TokenType.SEMICOLON:
                        self.advance()
                        break
                    if t.type == TokenType.LBRACE:
                        self.advance()
                        opens_block = True
                        break
                    if t.type == TokenType.RBRACE:
                        break
                if t.type in (TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE):
                    depth += 1
                elif t.type in (TokenType.RPAREN, TokenType.RBRACKET, TokenType.RBRACE):
                    depth = max(depth - 1, 0)
                self.advance()

        is_class = any(self.tok(i).lexeme in ("class", "interface", "enum")
                       and self.tok(i).type == TokenType.KEYWORD for i in range(start, self.current))
        scope = self.push_scope(is_class) if opens_block else self.current_scope()
        decls = self.scan_declarations(start, self.current, scope)
        self.add_ignored(start, "fora da gramática restrita", scope, decls)

    def scan_declarations(self, start, end, scope):
        """Procura declarações dentro de um trecho ignorado: parâmetros, variáveis do for,
        nomes de classes e métodos. Assim a semântica não acusa falsos 'não declarada'."""
        found = []
        is_method = False
        i = start
        while i < end:
            t = self.tok(i)
            if t.type == TokenType.KEYWORD and t.lexeme in ("class", "interface", "enum") \
                    and self.tok(i + 1).type == TokenType.IDENTIFIER:
                self.declare_symbol(self.tok(i + 1).lexeme, t.lexeme if t.lexeme != "class" else "classe")
                i += 2
                continue
            if i > start and self.tok(i - 1).type == TokenType.DOT:
                i += 1
                continue
            result = self.match_type(i, allow_void=True)
            if result is not None:
                j, type_name = result
                name, nxt = self.tok(j), self.tok(j + 1)
                if j < end and name.type == TokenType.IDENTIFIER:
                    if nxt.type == TokenType.LPAREN:
                        self.declare_symbol(name.lexeme, f"método ({type_name})")
                        is_method = True
                        i = j + 1
                        continue
                    if type_name != "void" and nxt.type in (TokenType.ASSIGN, TokenType.SEMICOLON, TokenType.COMMA,
                                                            TokenType.RPAREN, TokenType.COLON):
                        kind = "parametro" if is_method else "variavel"
                        self.declare_symbol(name.lexeme, f"{type_name} (parâmetro)" if is_method else type_name)
                        found.append(VarInfo(name.lexeme, type_name, name.line, kind, scope))
                        i = j + 1
                        continue
            i += 1
        return found

    def add_ignored(self, start, reason, scope, decls, is_error=False):
        end = max(self.current, start + 1)
        text, prev = "", None
        for i in range(start, min(end, len(self.tokens))):
            t = self.tok(i)
            if t.type == TokenType.EOF:
                break
            glued = prev is not None and t.line == prev.line and t.column == prev.column + len(prev.lexeme)
            text += ("" if glued or prev is None else " ") + t.lexeme
            prev = t
        first = self.tok(start)
        self.statements.append(Ignored(text, first.line, first.column, reason, decls, scope, is_error))
