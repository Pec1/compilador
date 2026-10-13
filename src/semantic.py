from .ast_nodes import Declaration, Assignment, BinaryOp, UnaryOp, Literal, Identifier, Ignored

# Ordem de "largura" dos tipos numéricos (para promoção e conversões de alargamento)
NUMERIC_RANK = {"byte": 1, "short": 2, "char": 2, "int": 3, "long": 4, "float": 5, "double": 6}
PRIMITIVES = set(NUMERIC_RANK) | {"boolean"}
KNOWN_TYPES = PRIMITIVES | {"String"}


class SemanticError(str):
    """Mensagem estruturada de erro semântico compatível com string."""
    def __new__(cls, message: str, line: int):
        instance = super().__new__(cls, f"[ERRO SEMÂNTICO] {message}")
        instance.message = message
        instance.line = line
        return instance


def is_numeric(type_name):
    return type_name in NUMERIC_RANK


def can_widen(source, target):
    """Conversões implícitas permitidas pelo Java entre tipos numéricos."""
    if source == target:
        return True
    if not (is_numeric(source) and is_numeric(target)):
        return False
    if target == "char" or (source == "char" and target in ("byte", "short")):
        return False
    return NUMERIC_RANK[source] < NUMERIC_RANK[target] or (source == "byte" and target == "short")


def number_type(lexeme):
    text = lexeme.lower()
    is_hex = text.startswith("0x")
    if text.endswith("l"):
        return "long"
    if not is_hex and text.endswith("f"):
        return "float"
    if not is_hex and (text.endswith("d") or "." in text or "e" in text):
        return "double"
    return "int"


class SemanticAnalyzer:
    """Percorre a AST verificando:
       1. uso de variável não declarada previamente;
       2. incompatibilidade de tipos em declarações e atribuições;
       3. declaração duplicada no mesmo escopo;
       4. operações aritméticas com operandos não numéricos.
    """
    def __init__(self, symbol_table=None):
        self.symbols = symbol_table
        self.errors = []
        self.declared = {}   # nome -> lista de declarações {type, scope, line, explicit}

    # ---------------------------------------------------------------
    # Escopos: uma declaração é visível em todo bloco interno ao seu
    # ---------------------------------------------------------------
    def declare(self, name, type_name, scope, line, explicit):
        for prev in self.declared.get(name, []):
            if prev["scope"] == scope and prev["explicit"] and explicit:
                self.errors.append(SemanticError(
                    f"Variável '{name}' declarada na linha {line} já havia sido declarada na linha {prev['line']}.", line))
                return
        self.declared.setdefault(name, []).append(
            {"type": type_name, "scope": scope, "line": line, "explicit": explicit})

    def lookup(self, name, scope):
        best = None
        for decl in self.declared.get(name, []):
            s = decl["scope"]
            if scope[:len(s)] == s and (best is None or len(s) >= len(best["scope"])):
                best = decl
        return best

    # ---------------------------------------------------------------
    # Percurso da AST
    # ---------------------------------------------------------------
    def analyze(self, program):
        self.errors = []
        self.declared = {}
        if not program or not hasattr(program, "statements"):
            return self.errors

        # Campos de classe são visíveis em todos os métodos, mesmo declarados depois
        class_scopes = getattr(program, "class_scopes", set())
        def is_field(scope):
            return bool(scope) and scope[-1] in class_scopes

        for stmt in program.statements:
            if isinstance(stmt, Declaration) and is_field(stmt.scope):
                self.declare(stmt.name, stmt.type_name, stmt.scope, stmt.line, explicit=True)
            elif isinstance(stmt, Ignored):
                for d in stmt.declarations:
                    if is_field(d.scope):
                        self.declare(d.name, d.type_name, d.scope, d.line, explicit=d.explicit)

        for stmt in program.statements:
            if isinstance(stmt, Declaration):
                if stmt.initializer is not None:
                    self.check_expression(stmt.initializer, stmt.scope)
                if not is_field(stmt.scope):
                    self.declare(stmt.name, stmt.type_name, stmt.scope, stmt.line, explicit=True)
                if stmt.initializer is not None:
                    self.check_assignment_type(stmt.type_name, stmt.initializer, stmt.scope, stmt.line)

            elif isinstance(stmt, Assignment):
                symbol = self.lookup(stmt.name, stmt.scope)
                if symbol is None:
                    self.errors.append(SemanticError(
                        f"Variável '{stmt.name}' utilizada na linha {stmt.line} não foi declarada previamente.", stmt.line))
                self.check_expression(stmt.expression, stmt.scope)
                if symbol is not None:
                    self.check_assignment_type(symbol["type"], stmt.expression, stmt.scope, stmt.line)

            elif isinstance(stmt, Ignored):
                for d in stmt.declarations:
                    if not is_field(d.scope):
                        self.declare(d.name, d.type_name, d.scope, d.line, explicit=d.explicit)

        return self.errors

    def check_expression(self, node, scope):
        if isinstance(node, Identifier):
            if self.lookup(node.name, scope) is None:
                self.errors.append(SemanticError(
                    f"Variável '{node.name}' utilizada na linha {node.line} não foi declarada previamente.", node.line))
        elif isinstance(node, UnaryOp):
            self.check_expression(node.operand, scope)
            t = self.infer_type(node.operand, scope)
            if t and not is_numeric(t):
                self.errors.append(SemanticError(
                    f"Operação '{node.op}' inválida na linha {node.line}: o operando é do tipo {t}, não numérico.", node.line))
        elif isinstance(node, BinaryOp):
            self.check_expression(node.left, scope)
            self.check_expression(node.right, scope)
            left = self.infer_type(node.left, scope)
            right = self.infer_type(node.right, scope)
            if node.op == "+" and "String" in (left, right):
                return  # concatenação de String é válida em Java
            if left and right and not (is_numeric(left) and is_numeric(right)):
                self.errors.append(SemanticError(
                    f"Operação '{node.op}' inválida na linha {node.line}: não é possível aplicar '{node.op}' "
                    f"entre {left} e {right}.", node.line))

    def infer_type(self, node, scope):
        if isinstance(node, Literal):
            if node.kind == "NUM":
                return number_type(node.value)
            return {"STRING": "String", "CHAR": "char", "BOOL": "boolean", "NULL": "null"}.get(node.kind)
        if isinstance(node, Identifier):
            symbol = self.lookup(node.name, scope)
            return symbol["type"] if symbol else None
        if isinstance(node, UnaryOp):
            t = self.infer_type(node.operand, scope)
            return self.promote(t, "int") if is_numeric(t) else None
        if isinstance(node, BinaryOp):
            left = self.infer_type(node.left, scope)
            right = self.infer_type(node.right, scope)
            if node.op == "+" and "String" in (left, right):
                return "String"
            if is_numeric(left) and is_numeric(right):
                return self.promote(left, right)
        return None

    def promote(self, a, b):
        """Promoção numérica binária: o resultado é no mínimo int."""
        widest = max(a, b, key=lambda t: NUMERIC_RANK[t])
        return widest if NUMERIC_RANK[widest] > NUMERIC_RANK["int"] else "int"

    def is_int_constant(self, node):
        if isinstance(node, UnaryOp):
            return self.is_int_constant(node.operand)
        return isinstance(node, Literal) and node.kind == "NUM" and number_type(node.value) == "int"

    def check_assignment_type(self, target_type, expression, scope, line):
        expr_type = self.infer_type(expression, scope)
        if not expr_type or target_type not in KNOWN_TYPES or expr_type == target_type:
            return
        if expr_type == "null" and target_type not in PRIMITIVES:
            return
        if can_widen(expr_type, target_type):
            return
        # Constante inteira em byte/short/char é permitida (ex.: char c = 65;)
        if target_type in ("byte", "short", "char") and self.is_int_constant(expression):
            return
        self.errors.append(SemanticError(
            f"Incompatibilidade de tipos na linha {line}: Não é possível atribuir {expr_type} a um tipo {target_type}.", line))
