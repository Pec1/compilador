# Compilador AV3: analisador léxico, sintático e semântico de Java em Python

Lê um arquivo `.java` e mostra **tokens**, **tabela de símbolos**, **erros léxicos**, **árvore sintática (AST)** e
**erros semânticos**. Python 3.7 ou superior, sem nenhuma dependência (nada de `pip install`), só console.

## Como rodar

Na pasta do projeto:

```bash
python main.py testes/Barema.java
```

No Windows, se `python` não funcionar, use `py main.py testes/Barema.java` ou, o mais seguro, o `rodar.bat`
(ele acha o Python sozinho e ativa o UTF-8 no console):

```bash
rodar.bat testes\Barema.java
```

Para o arquivo do professor, passe o caminho completo: `rodar.bat C:\Users\aluno\Downloads\Prova.java`.
Se faltar o argumento ou o arquivo não existir, aparece uma mensagem `[ERRO DE ENTRADA]` (nunca um traceback).

| Arquivo de teste | O que mostra |
|---|---|
| `testes/Barema.java` | `x = a + 5;` (AST), `int resultado = "texto";` e `total = 10;` (os 2 erros semânticos) |
| `testes/Completo.java` | Java "de verdade" (package, classe, métodos, if, for, while, switch, generics): 0 erros |
| `testes/ErroLexico.java` | `#`, crase e string sem fechar: erros com linha/coluna, e a análise continua |

## Arquivos

| Arquivo | Etapa | Item do barema |
|---|---|---|
| `main.py` | lê o `.java`, chama as etapas em ordem e imprime as 5 seções | todos |
| `lexico.py` | ETAPA 1: código → lista de tokens + erros léxicos | Lista de Tokens, Assertividade Léxica |
| `tabela_simbolos.py` | tokens → tabela (ordem, lexema, categoria, tipo, linha) | Tabela de Símbolos |
| `sintatico.py` | ETAPA 2: gramática do barema → AST impressa em árvore | Sintática + AST |
| `semantico.py` | ETAPA 3: tipo incompatível e variável não declarada | Semântica |

## Gramática

```
<Comando>    ::= <Declaracao> | <Atribuicao>
<Declaracao> ::= <Tipo> ID ["=" <Expressao>] ("," ID ["=" <Expressao>])* ";"
<Atribuicao> ::= ID "=" <Expressao> ";"
<Expressao>  ::= <Termo> (("+"|"-") <Termo>)*
<Termo>      ::= <Fator> (("*"|"/") <Fator>)*
<Fator>      ::= ID | NUMERO | STRING | "(" <Expressao> ")"
<Tipo>       ::= int | double | float | long | short | byte | char | boolean | String
```

A lista com `,` existe porque o `Barema.java` tem `int x, a;`. Tudo o que não casa com `<Comando>` (class, if, for,
chamadas de método...) é **pulado sem erro** até o próximo `;`, `{` ou `}`. É isso que faz o programa aguentar qualquer
`.java`. As variáveis declaradas nesses trechos (parâmetros, variável do `for`, `Scanner sc = ...`) são anotadas
para a semântica não acusar "não declarada" à toa.

## Mapa da defesa

| Parte | Onde | O que dizer |
|---|---|---|
| **Fluxo** | `main.py`, função `main` (linhas 44–47) | "As 4 etapas em sequência: léxico → tabela → sintático → semântico." |
| **Tokenização** | `lexico.py`, lista `REGRAS` (33) e função `analisar_lexico` (57) | "Cada tipo de token é um regex. Na posição atual, tentamos as regras **em ordem** e a primeira que casar vence; guardamos o token e avançamos. Se nenhuma casar, é erro léxico com linha e coluna, e seguimos para o próximo caractere." |
| Ordem das regras | `lexico.py`, comentário da linha 28 e `OPERADORES` (24) | "Comentário antes de operador, text block antes de string, operadores do maior para o menor: `>>>=` antes de `>>` antes de `>`." |
| **Tabela de símbolos** | `tabela_simbolos.py`, `montar_tabela` (62) e `tipo_antes` (11) | "Percorre os tokens em ordem e insere cada palavra na primeira vez em que aparece (ordem de inserção). O tipo é o que vem logo antes do nome: `int x`, `String nome`, `class Pessoa`, `void metodo(`." |
| **Parsing** | `sintatico.py`, `comando` (26), `declaracao` (37), `atribuicao` (54), `expressao` (65), `termo` (74), `fator` (83) | "Descendente recursivo: uma função por regra, com a regra BNF em comentário em cima. `expressao` chama `termo`, que chama `fator`; por isso `*` fica mais fundo na árvore e é feito antes de `+`." |
| Recuperação | `sintatico.py`, `pular` (98) e `analisar_sintaxe` (123) | "Se o trecho não casa com a gramática, pulamos até `;`, `{` ou `}` e continuamos. O parser nunca aborta." |
| **AST** | `sintatico.py`, `imprimir_arvore` (142) | "Caminhamento em profundidade recursivo: o último filho recebe `└──`, os outros `├──`." |
| **Semântica** | `semantico.py`, `analisar_semantica` (64) | "Percorre as ASTs na ordem do código guardando `nome → tipo`. Uso de nome que não está no dicionário: 'não foi declarada previamente'." |
| Tipos | `semantico.py`, `tipo_da_expressao` (25) e `compativel` (44) | "O tipo da expressão é inferido de baixo para cima (`5` é int, `"texto"` é String). `int → double` é permitido; `double → int` e `String → int` são erro." |

## Perguntas prováveis

- **"Por que `String` é identificador?"** Em Java `String` é uma classe (`java.lang.String`), não uma palavra reservada.
- **"E `var`, `record`, `yield`?"** São palavras contextuais: o próprio compilador Java as lê como identificadores no
  léxico e só decide o papel delas na análise sintática. Aqui elas saem como `IDENTIFICADOR`.
- **"O que acontece com `if`, `for`, métodos?"** São tokenizados normalmente (todas as 51 palavras reservadas do Java
  estão no léxico). O parser reconhece só a gramática acima e pula o resto, sem dar erro.
- **"E `String s = "a" + 1;`?"** É válido (concatenação): `+` com String dá String.
