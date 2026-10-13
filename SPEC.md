# Especificação — compilador_av3

## 1. Tokens

Cada token guarda tipo, lexema original (strings e chars mantêm as aspas), linha e coluna. Comentários
(`//`, `/* */`, `/** */`) e espaços são descartados.

| Grupo | Tipos de token |
|---|---|
| Palavras | `KEYWORD` (as 50 palavras reservadas do Java), `IDENTIFIER` (letras Unicode, `_`, `$`) |
| Literais | `NUMBER` (`10`, `3.14`, `3.14f`, `10L`, `0x1F`, `0b101`, `1e10`, `1_000`, `.5`), `STRING_LITERAL` (inclui text block `"""`), `CHAR_LITERAL`, `BOOLEAN_LITERAL`, `NULL_LITERAL` |
| Aritméticos | `PLUS` `MINUS` `MULT` `DIV` `MOD` `INCREMENT` `DECREMENT` |
| Atribuição | `ASSIGN` e compostos `PLUS_ASSIGN` ... `URSHIFT_ASSIGN` (`+= -= *= /= %= &= \|= ^= <<= >>= >>>=`) |
| Relacionais/lógicos | `EQ NE LT GT LE GE AND OR NOT` |
| Bit a bit | `BIT_AND BIT_OR BIT_XOR BIT_NOT LSHIFT RSHIFT URSHIFT` |
| Outros | `QUESTION COLON ARROW DOUBLE_COLON ELLIPSIS AT` |
| Delimitadores | `SEMICOLON COMMA DOT LPAREN RPAREN LBRACE RBRACE LBRACKET RBRACKET` |
| Fim | `EOF` |

Escapes aceitos: `\b \t \n \f \r \s \" \' \\`, octal `\0`–`\377` e Unicode `\uXXXX`.

**Erros léxicos** (registrados com linha e coluna; a análise continua): caractere inválido (`#`, `` ` ``, `\` fora
de string), string ou char não fechado, char vazio ou com mais de um caractere, escape inválido, comentário
de bloco não fechado e número malformado (`12abc`).

## 2. Gramática

```bnf
<Comando>     ::= <Declaracao> | <Atribuicao>
<Declaracao>  ::= <Modificador>* <Tipo> <ID> ["=" <Expressao>] ("," <ID> ["=" <Expressao>])* ";"
<Atribuicao>  ::= <ID> "=" <Expressao> ";"
<Expressao>   ::= <Termo> (("+" | "-") <Termo>)*
<Termo>       ::= <Fator> (("*" | "/" | "%") <Fator>)*
<Fator>       ::= "-" <Fator> | ID | NUM | STRING | CHAR | BOOL | null | "(" <Expressao> ")"
```

Construções fora da gramática são puladas e listadas como "trecho ignorado". Só são **erros sintáticos** os
problemas que também seriam erro em Java: `;` faltando, expressão faltando (`x = ;`), dois operandos seguidos
(`x = a b;`), parêntese ou chave sem par, tipo sem identificador (`int = 5;`).

## 3. Tabela de símbolos

Montada a partir dos tokens, em ordem de primeira ocorrência, sem duplicatas:

| Coluna | Conteúdo |
|---|---|
| Ordem | posição de inserção (1, 2, 3...) |
| Lexema | o texto do símbolo |
| Categoria | `palavra reservada` ou `identificador` |
| Tipo | palavra reservada: `tipo primitivo`, `literal` ou `-`; identificador: tipo declarado (`int`, `List<String>`, `int (parâmetro)`, `método (void)`, `classe`, `classe (API Java)`) |
| Linha | linha da primeira ocorrência |

## 4. Regras semânticas

| Regra | Mensagem |
|---|---|
| Uso sem declaração prévia | `[ERRO SEMÂNTICO] Variável 'total' utilizada na linha X não foi declarada previamente.` |
| Tipos incompatíveis | `[ERRO SEMÂNTICO] Incompatibilidade de tipos na linha X: Não é possível atribuir String a um tipo int.` |
| Declaração duplicada no mesmo escopo | `[ERRO SEMÂNTICO] Variável 'x' declarada na linha Y já havia sido declarada na linha X.` |
| Aritmética com não numérico | `[ERRO SEMÂNTICO] Operação '-' inválida na linha X: não é possível aplicar '-' entre String e int.` |

As conversões seguem o Java: alargamento numérico (`byte→short→int→long→float→double`, `char→int`) é permitido;
constante inteira cabe em `byte/short/char`; `null` só vai para tipos de referência; `+` com `String` é concatenação.
Escopos seguem os blocos `{ }`; campos de classe são visíveis em todos os métodos.
