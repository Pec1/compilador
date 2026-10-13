from .tokens import Token, TokenType

# Palavras reservadas da linguagem Java (JLS §3.9)
KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
    "class", "const", "continue", "default", "do", "double", "else", "enum",
    "extends", "final", "finally", "float", "for", "goto", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new",
    "package", "private", "protected", "public", "return", "short", "static",
    "strictfp", "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while",
}

# Literais reservados (não podem ser usados como identificadores)
LITERAL_WORDS = {
    "true": TokenType.BOOLEAN_LITERAL,
    "false": TokenType.BOOLEAN_LITERAL,
    "null": TokenType.NULL_LITERAL,
}

PRIMITIVE_TYPES = {"byte", "short", "int", "long", "float", "double", "char", "boolean"}

# Operadores e delimitadores, do mais longo para o mais curto ("maior casamento primeiro").
# Assim ">>>=" é reconhecido como um único token e não como ">", ">", ">", "=".
OPERATORS = [
    (">>>=", TokenType.URSHIFT_ASSIGN),
    ("<<=", TokenType.LSHIFT_ASSIGN),
    (">>=", TokenType.RSHIFT_ASSIGN),
    (">>>", TokenType.URSHIFT),
    ("...", TokenType.ELLIPSIS),
    ("==", TokenType.EQ),
    ("!=", TokenType.NE),
    ("<=", TokenType.LE),
    (">=", TokenType.GE),
    ("&&", TokenType.AND),
    ("||", TokenType.OR),
    ("++", TokenType.INCREMENT),
    ("--", TokenType.DECREMENT),
    ("+=", TokenType.PLUS_ASSIGN),
    ("-=", TokenType.MINUS_ASSIGN),
    ("*=", TokenType.MULT_ASSIGN),
    ("/=", TokenType.DIV_ASSIGN),
    ("%=", TokenType.MOD_ASSIGN),
    ("&=", TokenType.AND_ASSIGN),
    ("|=", TokenType.OR_ASSIGN),
    ("^=", TokenType.XOR_ASSIGN),
    ("->", TokenType.ARROW),
    ("::", TokenType.DOUBLE_COLON),
    ("<<", TokenType.LSHIFT),
    (">>", TokenType.RSHIFT),
    ("=", TokenType.ASSIGN),
    ("+", TokenType.PLUS),
    ("-", TokenType.MINUS),
    ("*", TokenType.MULT),
    ("/", TokenType.DIV),
    ("%", TokenType.MOD),
    ("<", TokenType.LT),
    (">", TokenType.GT),
    ("!", TokenType.NOT),
    ("~", TokenType.BIT_NOT),
    ("&", TokenType.BIT_AND),
    ("|", TokenType.BIT_OR),
    ("^", TokenType.BIT_XOR),
    ("?", TokenType.QUESTION),
    (":", TokenType.COLON),
    (";", TokenType.SEMICOLON),
    (",", TokenType.COMMA),
    (".", TokenType.DOT),
    ("(", TokenType.LPAREN),
    (")", TokenType.RPAREN),
    ("{", TokenType.LBRACE),
    ("}", TokenType.RBRACE),
    ("[", TokenType.LBRACKET),
    ("]", TokenType.RBRACKET),
    ("@", TokenType.AT),
]

# Escapes válidos dentro de strings e chars ('\s' existe desde o Java 15)
SIMPLE_ESCAPES = set('btnfrs"\'\\')


class LexicalError(Exception):
    """Erro léxico estruturado. É registrado em Lexer.errors (a análise continua)."""
    def __init__(self, message: str, line: int, column: int, character: str = None, tokens: list = None):
        self.message = message
        self.line = line
        self.column = column
        self.character = character
        self.tokens = list(tokens) if tokens is not None else []
        super().__init__(self._format_message())

    def _format_message(self):
        return f"[ERRO LÉXICO] Linha {self.line}, coluna {self.column}: {self.message}"


def is_ident_start(c):
    return c.isalpha() or c in "_$"


def is_ident_part(c):
    return c.isalnum() or c in "_$"


class Lexer:
    """Analisador léxico para Java.

    Percorre o código caractere a caractere com um cursor (pos, linha, coluna)
    e agrupa os caracteres em tokens. Erros léxicos são registrados em
    self.errors e a análise continua a partir do próximo caractere.
    """
    def __init__(self, source: str):
        self.source = source if source is not None else ""
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        self.errors = []

    # ---------------------------------------------------------------
    # Funções auxiliares do cursor
    # ---------------------------------------------------------------
    def peek(self, offset=0):
        i = self.pos + offset
        return self.source[i] if i < len(self.source) else ""

    def at(self, chars, offset=0):
        """True se o caractere na posição pos+offset existe e pertence a chars.
        (Evita a armadilha do Python: "" in "abc" é True.)"""
        c = self.peek(offset)
        return c != "" and c in chars

    def advance(self):
        c = self.source[self.pos]
        self.pos += 1
        if c == "\n":
            self.line += 1
            self.column = 1
        elif c != "\r":
            self.column += 1
        return c

    def error(self, message, line, column, character=None):
        self.errors.append(LexicalError(message, line, column, character=character))

    def add(self, token_type, lexeme, line, column):
        self.tokens.append(Token(token_type, lexeme, line, column))

    # ---------------------------------------------------------------
    # Laço principal
    # ---------------------------------------------------------------
    def tokenize(self):
        self.tokens = []
        self.errors = []
        while self.pos < len(self.source):
            c = self.peek()

            # Espaços, tabulações, quebras de linha (LF e CRLF) e BOM
            if c in " \t\r\n\f﻿":
                self.advance()
                continue

            # Comentários: // linha, /* bloco */ e /** javadoc */
            if c == "/" and self.peek(1) == "/":
                while self.pos < len(self.source) and self.peek() != "\n":
                    self.advance()
                continue
            if c == "/" and self.peek(1) == "*":
                self.skip_block_comment()
                continue

            # Identificadores, palavras reservadas e literais true/false/null
            if is_ident_start(c):
                self.read_identifier()
                continue

            # Números (inteiros, reais, hexadecimais, binários, com sufixo e com '_')
            if c.isdigit() or (c == "." and self.peek(1).isdigit()):
                self.read_number()
                continue

            # Text block (Java 15+): """ ... """
            if c == '"' and self.peek(1) == '"' and self.peek(2) == '"':
                self.read_text_block()
                continue

            # Strings e caracteres
            if c == '"':
                self.read_string()
                continue
            if c == "'":
                self.read_char()
                continue

            # Operadores e delimitadores (maior casamento primeiro)
            if self.read_operator():
                continue

            # Caractere inválido: registra o erro e avança (não aborta)
            line, col = self.line, self.column
            self.advance()
            self.error(f"Caractere inválido {c!r}.", line, col, character=c)

        self.add(TokenType.EOF, "", self.line, self.column)
        return self.tokens

    # ---------------------------------------------------------------
    # Reconhecedores de cada classe de token
    # ---------------------------------------------------------------
    def skip_block_comment(self):
        line, col = self.line, self.column
        self.advance()
        self.advance()
        while self.pos < len(self.source):
            if self.peek() == "*" and self.peek(1) == "/":
                self.advance()
                self.advance()
                return
            self.advance()
        self.error("Comentário de bloco '/*' não fechado antes do fim do arquivo.", line, col)

    def read_identifier(self):
        start, line, col = self.pos, self.line, self.column
        while self.pos < len(self.source) and is_ident_part(self.peek()):
            self.advance()
        lexeme = self.source[start:self.pos]
        if lexeme in KEYWORDS:
            self.add(TokenType.KEYWORD, lexeme, line, col)
        elif lexeme in LITERAL_WORDS:
            self.add(LITERAL_WORDS[lexeme], lexeme, line, col)
        else:
            self.add(TokenType.IDENTIFIER, lexeme, line, col)

    def read_digits(self, valid):
        while self.pos < len(self.source) and (self.peek() in valid or self.peek() == "_"):
            self.advance()

    def read_number(self):
        start, line, col = self.pos, self.line, self.column
        decimal = "0123456789"
        if self.peek() == "0" and self.at("xX", 1):
            self.advance()
            self.advance()
            self.read_digits(decimal + "abcdefABCDEF")
            if self.at("lL"):
                self.advance()
        elif self.peek() == "0" and self.at("bB", 1):
            self.advance()
            self.advance()
            self.read_digits("01")
            if self.at("lL"):
                self.advance()
        else:
            self.read_digits(decimal)
            if self.peek() == "." and self.peek(1).isdigit():
                self.advance()
                self.read_digits(decimal)
            elif self.peek() == "." and not is_ident_start(self.peek(1)) and self.peek(1) != ".":
                self.advance()  # "1." também é um double válido
            if self.at("eE") and (self.peek(1).isdigit() or (self.at("+-", 1) and self.peek(2).isdigit())):
                self.advance()
                if self.at("+-"):
                    self.advance()
                self.read_digits(decimal)
            if self.at("lLfFdD"):
                self.advance()

        lexeme = self.source[start:self.pos]
        # Letras coladas ao número (ex.: "12abc") formam um literal malformado
        if self.pos < len(self.source) and is_ident_part(self.peek()):
            while self.pos < len(self.source) and is_ident_part(self.peek()):
                self.advance()
            lexeme = self.source[start:self.pos]
            self.error(f"Literal numérico malformado {lexeme!r}.", line, col, character=lexeme)
            return
        if lexeme.endswith("_") or "_." in lexeme or "._" in lexeme:
            self.error(f"Literal numérico malformado {lexeme!r} ('_' fora de posição).", line, col, character=lexeme)
            return
        self.add(TokenType.NUMBER, lexeme, line, col)

    def read_escape(self):
        """Consome uma sequência de escape iniciada por '\\'. Retorna False se inválida."""
        line, col = self.line, self.column
        self.advance()  # barra invertida
        nxt = self.peek()
        if nxt and nxt in SIMPLE_ESCAPES:
            self.advance()
            return True
        if nxt and nxt in "01234567":
            for _ in range(3):
                if self.at("01234567"):
                    self.advance()
            return True
        if nxt == "u":
            while self.peek() == "u":
                self.advance()
            hex_digits = 0
            while hex_digits < 4 and self.at("0123456789abcdefABCDEF"):
                self.advance()
                hex_digits += 1
            if hex_digits == 4:
                return True
        self.error(f"Sequência de escape inválida '\\{nxt}'.", line, col, character="\\" + nxt)
        if nxt and nxt != "\n":
            self.advance()
        return False

    def read_string(self):
        start, line, col = self.pos, self.line, self.column
        self.advance()  # aspas de abertura
        while self.pos < len(self.source):
            ch = self.peek()
            if ch == "\\":
                self.read_escape()
                continue
            if ch == '"':
                self.advance()
                self.add(TokenType.STRING_LITERAL, self.source[start:self.pos], line, col)
                return
            if ch in "\r\n":
                break
            self.advance()
        # String não fechada: registra o erro e continua na próxima linha
        self.error("String não fechada (falta '\"' antes do fim da linha).", line, col, character='"')

    def read_text_block(self):
        start, line, col = self.pos, self.line, self.column
        for _ in range(3):
            self.advance()
        while self.pos < len(self.source):
            if self.peek() == "\\":
                self.advance()
                if self.pos < len(self.source):
                    self.advance()
                continue
            if self.peek() == '"' and self.peek(1) == '"' and self.peek(2) == '"':
                for _ in range(3):
                    self.advance()
                self.add(TokenType.STRING_LITERAL, self.source[start:self.pos], line, col)
                return
            self.advance()
        self.error('Text block \'"""\' não fechado antes do fim do arquivo.', line, col)

    def read_char(self):
        start, line, col = self.pos, self.line, self.column
        self.advance()  # aspa simples de abertura
        if self.peek() == "'":
            self.advance()
            self.error("Literal de caractere vazio ''.", line, col, character="''")
            return
        if self.peek() in ("", "\r", "\n"):
            self.error("Literal de caractere não fechado.", line, col, character="'")
            return
        if self.peek() == "\\":
            self.read_escape()
        else:
            self.advance()
        if self.peek() == "'":
            self.advance()
            self.add(TokenType.CHAR_LITERAL, self.source[start:self.pos], line, col)
            return
        # Mais de um caractere ou sem fechamento: consome até a aspa (na mesma linha)
        while self.pos < len(self.source) and self.peek() not in "'\r\n":
            self.advance()
        if self.peek() == "'":
            self.advance()
            self.error(f"Literal de caractere inválido {self.source[start:self.pos]!r} (deve conter um único caractere).", line, col)
        else:
            self.error("Literal de caractere não fechado.", line, col, character="'")

    def read_operator(self):
        line, col = self.line, self.column
        for text, token_type in OPERATORS:
            if self.source.startswith(text, self.pos):
                for _ in text:
                    self.advance()
                self.add(token_type, text, line, col)
                return True
        return False
