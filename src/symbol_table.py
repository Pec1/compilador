from .tokens import TokenType
from .lexer import PRIMITIVE_TYPES

PALAVRA_RESERVADA = "palavra reservada"
IDENTIFICADOR = "identificador"

# Classes da biblioteca padrão do Java mais comuns (aparecem com tipo "classe (API Java)")
API_CLASSES = {
    "String", "Object", "System", "Math", "Integer", "Long", "Double", "Float", "Character",
    "Boolean", "Byte", "Short", "StringBuilder", "Scanner", "List", "ArrayList", "LinkedList",
    "Map", "HashMap", "TreeMap", "Set", "HashSet", "TreeSet", "Arrays", "Collections",
    "Exception", "RuntimeException", "Thread", "Runnable", "Override", "Iterator", "Optional",
}


class SymbolTable:
    """Tabela de símbolos didática.

    É preenchida durante a análise léxica (ordem de primeira ocorrência de cada
    palavra reservada e identificador) e enriquecida pelo parser com o tipo
    declarado de cada identificador (variável, parâmetro, método, classe...).
    """

    def __init__(self):
        self._symbols = []
        self._by_name = {}

    def insert(self, name: str, category: str, type_name: str, line):
        """Insere o símbolo se ainda não existir. Retorna o registro (novo ou existente)."""
        if not name:
            return None
        if name in self._by_name:
            return self._by_name[name]
        symbol = {
            "order": len(self._symbols) + 1,
            "name": name,
            "category": category,
            "type": type_name,
            "line": line,
        }
        self._symbols.append(symbol)
        self._by_name[name] = symbol
        return symbol

    def build_from_tokens(self, tokens):
        """Etapa léxica: registra palavras reservadas e identificadores na ordem em que aparecem."""
        for tok in tokens:
            if tok.type == TokenType.KEYWORD:
                kind = "tipo primitivo" if tok.lexeme in PRIMITIVE_TYPES else "-"
                self.insert(tok.lexeme, PALAVRA_RESERVADA, kind, tok.line)
            elif tok.type in (TokenType.BOOLEAN_LITERAL, TokenType.NULL_LITERAL):
                self.insert(tok.lexeme, PALAVRA_RESERVADA, "literal", tok.line)
            elif tok.type == TokenType.IDENTIFIER:
                self.insert(tok.lexeme, IDENTIFICADOR, "-", tok.line)

    def mark_api_classes(self):
        """Classes da API Java que não foram declaradas no próprio arquivo."""
        for symbol in self._symbols:
            if symbol["category"] == IDENTIFICADOR and symbol["type"] == "-" and symbol["name"] in API_CLASSES:
                symbol["type"] = "classe (API Java)"

    def set_type(self, name: str, type_name: str):
        """Etapa sintática: registra o tipo declarado (apenas a primeira declaração vale)."""
        symbol = self._by_name.get(name)
        if symbol is not None and symbol["category"] == IDENTIFICADOR and symbol["type"] == "-":
            symbol["type"] = type_name

    def lookup(self, name: str):
        if not name:
            return None
        return self._by_name.get(name)

    def exists(self, name: str):
        return bool(name and name in self._by_name)

    def all(self):
        return list(self._symbols)

    def clear(self):
        self._symbols.clear()
        self._by_name.clear()

    def format_table(self):
        if not self._symbols:
            return "(vazia)"
        name_w = max(14, max(len(s["name"]) for s in self._symbols) + 2)
        type_w = max(16, max(len(str(s["type"])) for s in self._symbols) + 2)
        header = f"{'Ordem':<7}{'Lexema':<{name_w}}{'Categoria':<20}{'Tipo':<{type_w}}{'Linha'}"
        lines = [header, "-" * len(header)]
        for s in self._symbols:
            lines.append(f"{s['order']:<7}{s['name']:<{name_w}}{s['category']:<20}{str(s['type']):<{type_w}}{s['line']}".rstrip())
        return "\n".join(lines)

    def print_table(self):
        print(self.format_table())
