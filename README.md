# compilador_av3

Analisador **léxico, sintático e semântico de Java** escrito em Python, feito para a AV3 de Compiladores (UNIJORGE).
Lê qualquer arquivo `.java` (com `package`, `import`, classes, métodos, `if`/`for`/`while`, generics, lambdas...),
mostra **todos os tokens**, a **tabela de símbolos**, a **AST** dos comandos da gramática restrita e os **erros semânticos**.

## Requisitos

- **Python 3.7 ou superior** (testado no 3.14). **Nenhuma dependência externa**, não há `pip install`.
- Interface gráfica opcional: usa o Tkinter, que já vem com o Python do python.org.

## Como executar

Na pasta do projeto:

```bash
python main.py testes/Barema.java
```

Se o comando `python` não existir no Windows (comum em laboratório), use o launcher `py`:

```bash
py main.py testes/Barema.java
```

No Windows, o jeito mais seguro é o `rodar.bat`: ele procura `py` e depois `python` sozinho e já ativa o UTF-8 no console:

```bash
rodar.bat testes\Barema.java
```

Opções:

| Flag | Efeito |
|---|---|
| `--json` | mostra a AST em JSON (além da gramática) |
| `--ascii` | desenha a árvore com `|--` e `` `-- `` (para terminais que não mostram `├──`) |
| `--sem-fonte` | não reimprime o código fonte no início |

Também funcionam: `python -m src.main arquivo.java`, `python src/main.py arquivo.java` e a interface gráfica `python -m src.gui`.

Arquivos em UTF-8 (com ou sem BOM) e em ANSI/Windows-1252 são aceitos automaticamente. Caminho inexistente,
pasta no lugar de arquivo ou falta de argumento geram uma mensagem `[ERRO DE ENTRADA]`, nunca um traceback.

### Versão simples (um arquivo só)

`compilador_simples.py` faz as mesmas 4 etapas em ~460 linhas, num único arquivo, e é mais fácil de explicar:

```bash
py compilador_simples.py testes/Barema.java
```

Diferenças: o léxico é uma tabela de expressões regulares, os comandos são separados por `;`, `{` e `}`, e a
semântica faz apenas as duas checagens do barema (tipo incompatível e variável não declarada), sem escopos de bloco.

## O que a saída mostra

```
CÓDIGO FONTE          (com número de linha)
1. TOKENS             #, linha:coluna, tipo e lexema de cada token
2. TABELA DE SÍMBOLOS ordem de inserção, lexema, categoria (palavra reservada / identificador), tipo, linha
3. ERROS LÉXICOS      linha e coluna; a análise continua depois do erro
4. ANÁLISE SINTÁTICA  gramática, AST de cada comando, trechos Java fora da gramática, erros sintáticos
5. ERROS SEMÂNTICOS
RESUMO
```

Exemplo, para `x = a + 5;`:

```
Atribuicao
├── ID (x)
├── OP_ATRIB (=)
└── Expressao (+)
    ├── ID (a)
    └── NUM (5)
```

```
[ERRO SEMÂNTICO] Incompatibilidade de tipos na linha 6: Não é possível atribuir String a um tipo int.
[ERRO SEMÂNTICO] Variável 'total' utilizada na linha 7 não foi declarada previamente.
```

## Gramática (GLC restrita)

Estende a gramática do barema (`<Atribuicao>`, `<Expressao>`, `<termo>`):

```bnf
<Comando>     ::= <Declaracao> | <Atribuicao>
<Declaracao>  ::= <Tipo> <ID> ["=" <Expressao>] ("," <ID> ["=" <Expressao>])* ";"
<Atribuicao>  ::= <ID> "=" <Expressao> ";"
<Expressao>   ::= <Termo> (("+" | "-") <Termo>)*
<Termo>       ::= <Fator> (("*" | "/" | "%") <Fator>)*
<Fator>       ::= "-" <Fator> | ID | NUM | STRING | CHAR | BOOL | null | "(" <Expressao> ")"
<Tipo>        ::= int | double | float | long | short | byte | char | boolean | String | Classe<...>[]
```

Tudo o que é Java válido, mas está fora dessa gramática (classe, métodos, `if`, `for`, chamadas, `new`, `++`...),
é **pulado** até `;`, `{` ou `}` e listado como "trecho ignorado". O parser não aborta.
Declarações encontradas nesses trechos (parâmetros, variável do `for`, `Scanner sc = new ...`) continuam sendo
registradas, para que a semântica não acuse falsos "não declarada".

## Análise semântica

1. Variável usada sem declaração prévia (respeita escopos de bloco; campos da classe valem em todos os métodos).
2. Incompatibilidade de tipos em declaração/atribuição, seguindo o Java: `int ← String` e `int ← double` são erro;
   `long ← int`, `double ← int`, `char ← 65` e `String ← "a" + 1` são válidos.
3. Declaração duplicada no mesmo escopo.
4. Operação aritmética com operando não numérico (`"a" - 1`; `"a" + 1` é concatenação e é válido).

## Onde está cada etapa (para a defesa)

| Etapa | Arquivo / função | Como funciona |
|---|---|---|
| Orquestração | `src/main.py`, `analyze_source` | Chama as 4 etapas em sequência: léxico → tabela → parser → semântica |
| Tokenização | `src/lexer.py`, `Lexer.tokenize` | Cursor caractere a caractere; decide pelo 1º caractere qual reconhecedor chamar (`read_identifier`, `read_number`, `read_string`, `read_char`, `read_operator`) |
| Operadores | `src/lexer.py`, lista `OPERATORS` | Ordenada do mais longo ao mais curto (maior casamento): `>>>=` vira 1 token, não 4 |
| Erro léxico | `src/lexer.py`, fim de `tokenize` | Registra `[ERRO LÉXICO] Linha L, coluna C` e avança 1 caractere, sem abortar |
| Tabela de símbolos | `src/symbol_table.py`, `build_from_tokens` e `set_type` | Lista em ordem de inserção + dicionário por nome; o tipo declarado é preenchido pelo parser |
| Parsing | `src/parser.py`, `statement`, `declaration`, `assignment`, `expression`, `term`, `factor` | Descendente recursivo: cada regra da GLC vira uma função que consome tokens e devolve um nó |
| Recuperação | `src/parser.py`, `recover`, `skip_construct` | Pula até `;`/`{`/`}` e registra o trecho ignorado |
| AST | `src/ast_nodes.py`, `render_tree` | Cada nó tem `label()` e `children()`; `render_tree` desenha com `├──`/`└──` |
| Semântica | `src/semantic.py`, `SemanticAnalyzer.analyze` | Percorre a AST, declara variáveis por escopo, procura cada uso (`lookup`) e compara tipos (`infer_type`, `check_assignment_type`) |

## Testes

```bash
python -m unittest -v tests/test_compiler.py
```

São 54 testes (léxico, tabela, parser, semântica, CLI, GUI). A pasta `testes/` tem arquivos `.java` de exemplo:

| Arquivo | Conteúdo |
|---|---|
| `Barema.java` | exatamente os exemplos do barema (AST + 2 erros semânticos) |
| `Basico.java` | todos os tipos primitivos, `+ - * / %` e parênteses |
| `Completo.java` | package, import, classe, métodos, if/for/while/do/switch, arrays, generics, @Override |
| `Avancado.java` | records, enums, interfaces, lambdas, text block, try-with-resources, classe anônima |
| `Lexico.java` | comentários, escapes, todos os formatos de número e operadores |
| `ErroLexico.java` | `#`, crase e string sem fechar (erros com linha/coluna, análise continua) |
| `Semantico.java` | 7 erros semânticos diferentes, sem falsos positivos |
| `Acentos.java`, `Ansi_cp1252.java`, `Vazio.java`, `Simples.java` | codificações, arquivo vazio, trecho sem classe |
