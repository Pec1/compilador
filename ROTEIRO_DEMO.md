# Roteiro da demonstração (5 minutos)

## Antes de começar (no computador do laboratório)

1. Copie a pasta inteira do projeto e abra um terminal **dentro dela**.
2. Use **`rodar.bat`** no lugar de `python main.py` (ex.: `rodar.bat testes\Barema.java`). Ele acha o Python sozinho,
   seja por `py` ou por `python`. Se aparecer "Python não foi encontrado; ... Microsoft Store", o comando `python`
   é só o atalho da Store; `py` ou o `rodar.bat` resolvem. Para o arquivo do professor, passe o **caminho completo**
   (ex.: `rodar.bat C:\Users\aluno\Downloads\Prova.java`).
3. Rode `python main.py testes/Barema.java` uma vez. Se a árvore aparecer com caracteres estranhos no lugar de `├──`,
   use `--ascii` em todos os comandos (ou rode `chcp 65001` antes).
4. Aumente a fonte do terminal (Ctrl + roda do mouse) para o projetor.

## Roteiro

| Tempo | O que fazer | O que dizer / qual item do barema |
|---|---|---|
| 0:00–0:20 | Mostrar a pasta: `main.py`, `src/` (lexer, symbol_table, parser, ast_nodes, semantic) | "Python puro, sem dependências; cada etapa é um arquivo." |
| 0:20–1:50 | `python main.py testes/Barema.java` | Rolar de cima para baixo pelas seções: |
| | **1. TOKENS** | **Item I.1 (3,0):** cada token com tipo, lexema, linha e coluna; `public`/`class`/`int` como KEYWORD, `{` como LBRACE |
| | **2. TABELA DE SÍMBOLOS** | **Item I.2 (3,0):** ordem de inserção, palavra reservada × identificador, tipo declarado (`int`, `método (void)`, `String[] (parâmetro)`), linha |
| | **3. ERROS LÉXICOS: 0** | **Item I.3 (1,0):** nenhum erro de reconhecimento |
| | **4. AST**, comando `x = a + 5;` | **Item II (2,0):** a gramática impressa e a árvore `Atribuicao → ID (x), OP_ATRIB (=), Expressao (+) → ID (a), NUM (5)`; class/main aparecem como "ignorados", ou seja, o parser não aborta |
| | **5. ERROS SEMÂNTICOS** | **Item III (1,0):** as duas mensagens do barema, com a linha correta |
| 1:50–2:40 | `python main.py testes/ErroLexico.java --sem-fonte` | Robustez: `#`, crase e string sem fechar com linha/coluna, e **a análise continua** (as declarações seguintes aparecem na AST) |
| 2:40–3:10 | `python main.py testes/Semantico.java --sem-fonte` (só a seção 5) | 7 erros diferentes (double→int, duplicada, `"a" - 1`...) e zero falsos positivos com parâmetros, campos e `for` |
| 3:10–3:20 | (Opcional) arquivo do professor: `python main.py caminho\do\Arquivo.java` | Funciona com qualquer Java; se ele vier antes, rode-o no lugar do `ErroLexico` |
| 3:20–5:00 | **Defesa (Item IV, 1,0):** abrir os arquivos nesta ordem ↓ | |

## Ordem dos arquivos na explicação do código

1. **`src/main.py:52`, `analyze_source`**: "O pipeline: as 4 etapas em sequência (comentários 1 a 4, linhas 58–76)."
2. **`src/lexer.py:151`, `tokenize`**: "Um cursor anda caractere a caractere; o primeiro caractere decide o reconhecedor:
   letra → identificador/palavra reservada, dígito → número, aspas → string. Na linha 198, um caractere inválido vira
   erro com linha e coluna, e o laço continua."
   Mostrar também **`OPERATORS` (linha 25)**: "ordenados do maior para o menor, por isso `>>>=` vira um token só."
3. **`src/symbol_table.py:45`, `build_from_tokens`**: "Percorre os tokens e insere cada palavra reservada e identificador
   na primeira vez em que aparece, o que preserva a ordem de inserção. Depois, `set_type` (linha 62) recebe do parser o tipo declarado."
4. **`src/parser.py:329–347`, `expression` / `term` / `factor`**: "Descendente recursivo: cada regra da gramática é uma
   função. `expression` trata `+ -`, `term` trata `* / %` (por isso a precedência sai certa) e `factor` trata ID, número e parênteses."
   Depois **`assignment` (linha 299)**: "consome ID, '=', Expressao e ';' e cria o nó `Assignment`."
   E **`skip_construct` (linha 443)**: "o que não está na gramática é pulado até `;` ou `{`, sem abortar."
5. **`src/ast_nodes.py:15`, `render_tree`**: "Cada nó informa seu rótulo e seus filhos; essa função desenha a árvore."
6. **`src/semantic.py:80`, `analyze`**: "Percorre a AST. Na declaração, registra a variável no escopo atual. No uso, faz
   `lookup` (linha 69); se não achar, gera o erro da linha 112. Em `check_assignment_type` (linha 177), compara o tipo
   inferido da expressão com o tipo da variável, o que produz a mensagem da linha 189."

## Perguntas prováveis

- **"Por que `String` aparece como identificador?"** Em Java, `String` é uma classe (`java.lang.String`), não uma
  palavra reservada. Por isso a tabela mostra "classe (API Java)".
- **"O que acontece com `if`, `for`, métodos?"** São tokenizados normalmente (item léxico completo). O parser reconhece
  a gramática restrita e lista o resto como "trecho ignorado", sem abortar.
- **"E `String s = "a" + 1;`?"** É válido em Java (concatenação). Já `"a" - 1` é erro semântico.
- **"E se eu tirar o `;`?"** Aparece `[ERRO SINTÁTICO] ... Era esperado ';'` e o comando seguinte continua sendo analisado.
