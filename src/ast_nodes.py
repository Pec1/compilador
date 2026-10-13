from dataclasses import dataclass, field
from typing import Optional

# Caracteres usados para desenhar a árvore (há um modo ASCII para terminais sem UTF-8)
UNICODE_TREE = {"branch": "├── ", "last": "└── ", "pipe": "│   ", "space": "    "}
ASCII_TREE = {"branch": "|-- ", "last": "`-- ", "pipe": "|   ", "space": "    "}
TREE = dict(UNICODE_TREE)


def set_ascii_tree(enabled: bool):
    TREE.clear()
    TREE.update(ASCII_TREE if enabled else UNICODE_TREE)


def render_tree(node):
    """Desenha um nó e seus filhos no formato:
        Atribuicao
        ├── ID (x)
        └── NUM (5)
    """
    if isinstance(node, str):
        return node
    lines = [node.label()]
    kids = node.children()
    for i, kid in enumerate(kids):
        last = i == len(kids) - 1
        sub = render_tree(kid).splitlines() or ["<vazio>"]
        lines.append((TREE["last"] if last else TREE["branch"]) + sub[0])
        lines.extend((TREE["space"] if last else TREE["pipe"]) + s for s in sub[1:])
    return "\n".join(lines)


class ASTNode:
    def label(self):
        raise NotImplementedError

    def children(self):
        return []

    def pretty(self):
        return render_tree(self)

    def to_dict(self):
        raise NotImplementedError


@dataclass
class VarInfo:
    """Declaração encontrada fora da gramática (parâmetro, variável do for, campo com 'new'...)."""
    name: str
    type_name: str
    line: int
    kind: str = "variavel"
    scope: tuple = ()
    explicit: bool = False   # True quando veio de uma declaração "Tipo id = ...;" de verdade


@dataclass
class Ignored:
    """Trecho de código Java fora da gramática restrita, pulado pelo parser."""
    text: str
    line: int
    column: int = 1
    reason: str = ""
    declarations: list = field(default_factory=list)
    scope: tuple = ()
    is_error: bool = False


@dataclass
class Program(ASTNode):
    statements: list
    class_scopes: set = field(default_factory=set)

    @property
    def commands(self):
        """Somente os comandos reconhecidos pela gramática (declarações e atribuições)."""
        return [s for s in self.statements if isinstance(s, ASTNode)]

    @property
    def ignored(self):
        return [s for s in self.statements if isinstance(s, Ignored)]

    def label(self):
        return "Programa"

    def children(self):
        return self.commands

    def to_dict(self):
        return {"Programa": [c.to_dict() for c in self.commands]}


@dataclass
class Declaration(ASTNode):
    type_name: str
    name: str
    line: int
    initializer: Optional[ASTNode] = None
    column: int = 1
    scope: tuple = ()

    def label(self):
        return "Declaracao"

    def children(self):
        kids = [f"TIPO ({self.type_name})", f"ID ({self.name})"]
        if self.initializer is not None:
            kids += ["OP_ATRIB (=)", self.initializer]
        return kids

    def to_dict(self):
        d = {"no": "Declaracao", "linha": self.line, "tipo": self.type_name, "id": self.name}
        if self.initializer is not None:
            d["op"] = "="
            d["expressao"] = self.initializer.to_dict()
        return d


@dataclass
class Assignment(ASTNode):
    name: str
    line: int
    expression: ASTNode
    column: int = 1
    scope: tuple = ()

    def label(self):
        return "Atribuicao"

    def children(self):
        return [f"ID ({self.name})", "OP_ATRIB (=)", self.expression]

    def to_dict(self):
        return {"no": "Atribuicao", "linha": self.line, "id": self.name, "op": "=",
                "expressao": self.expression.to_dict()}


@dataclass
class BinaryOp(ASTNode):
    op: str
    left: ASTNode
    right: ASTNode
    line: int = 1
    column: int = 1

    def label(self):
        return f"Expressao ({self.op})"

    def children(self):
        return [self.left, self.right]

    def to_dict(self):
        return {"no": "Expressao", "op": self.op, "esq": self.left.to_dict(), "dir": self.right.to_dict()}


@dataclass
class UnaryOp(ASTNode):
    op: str
    operand: ASTNode
    line: int = 1
    column: int = 1

    def label(self):
        return f"Unario ({self.op})"

    def children(self):
        return [self.operand]

    def to_dict(self):
        return {"no": "Unario", "op": self.op, "operando": self.operand.to_dict()}


@dataclass
class Literal(ASTNode):
    value: str
    kind: str          # NUM, STRING, CHAR, BOOL, NULL
    line: int = 1
    column: int = 1

    def label(self):
        return f"{self.kind} ({self.value})"

    def to_dict(self):
        return {"no": self.kind, "valor": self.value}


@dataclass
class Identifier(ASTNode):
    name: str
    line: int = 1
    column: int = 1

    def label(self):
        return f"ID ({self.name})"

    def to_dict(self):
        return {"no": "ID", "nome": self.name}
