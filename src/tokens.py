from dataclasses import dataclass
from enum import Enum, auto

class TokenType(Enum):
    # Palavras reservadas, identificadores e literais
    KEYWORD = auto()
    IDENTIFIER = auto()
    NUMBER = auto()
    STRING_LITERAL = auto()
    CHAR_LITERAL = auto()
    BOOLEAN_LITERAL = auto()
    NULL_LITERAL = auto()

    # Atribuição e operadores aritméticos
    ASSIGN = auto()            # =
    PLUS = auto()              # +
    MINUS = auto()             # -
    MULT = auto()              # *
    DIV = auto()               # /
    MOD = auto()               # %
    INCREMENT = auto()         # ++
    DECREMENT = auto()         # --

    # Atribuições compostas
    PLUS_ASSIGN = auto()       # +=
    MINUS_ASSIGN = auto()      # -=
    MULT_ASSIGN = auto()       # *=
    DIV_ASSIGN = auto()        # /=
    MOD_ASSIGN = auto()        # %=
    AND_ASSIGN = auto()        # &=
    OR_ASSIGN = auto()         # |=
    XOR_ASSIGN = auto()        # ^=
    LSHIFT_ASSIGN = auto()     # <<=
    RSHIFT_ASSIGN = auto()     # >>=
    URSHIFT_ASSIGN = auto()    # >>>=

    # Relacionais e lógicos
    EQ = auto()                # ==
    NE = auto()                # !=
    LT = auto()                # <
    GT = auto()                # >
    LE = auto()                # <=
    GE = auto()                # >=
    AND = auto()               # &&
    OR = auto()                # ||
    NOT = auto()               # !

    # Bit a bit e deslocamentos
    BIT_AND = auto()           # &
    BIT_OR = auto()            # |
    BIT_XOR = auto()           # ^
    BIT_NOT = auto()           # ~
    LSHIFT = auto()            # <<
    RSHIFT = auto()            # >>
    URSHIFT = auto()           # >>>

    # Outros operadores
    QUESTION = auto()          # ?
    COLON = auto()             # :
    ARROW = auto()             # ->
    DOUBLE_COLON = auto()      # ::
    ELLIPSIS = auto()          # ...

    # Delimitadores
    SEMICOLON = auto()         # ;
    COMMA = auto()             # ,
    DOT = auto()               # .
    LPAREN = auto()            # (
    RPAREN = auto()            # )
    LBRACE = auto()            # {
    RBRACE = auto()            # }
    LBRACKET = auto()          # [
    RBRACKET = auto()          # ]
    AT = auto()                # @

    EOF = auto()

    # Aliases para compatibilidade
    ID = IDENTIFIER


@dataclass
class Token:
    type: TokenType
    lexeme: str
    line: int
    column: int = 1

    def __str__(self):
        return f"{self.type.name:<16} -> {self.lexeme!r:<14} (linha {self.line}, coluna {self.column})"
