# NOTES — Módulo 4 (Do Texto à Árvore, Catálogo e Execução)

## Resumo

Implementação das quatro etapas de processamento de consultas SQL (`CREATE TABLE`, `INSERT` e `SELECT`): Tokenizador (`tokeniza`), Parser de descida recursiva (`Parser`), Catálogo persistente na Página 1 (`Catalogo`) com análise semântica e Executor integrado ao `Cache` (M2) e `Pager` (M1).

## Decisões de Projeto

1. **Separação Estrita das 3 Primeiras Etapas (Léxica, Sintática e Semântica):**
   - **Tokenizador (`ErroLexico`):** Varre o SQL caractere a caractere produzindo pares `(tipo, valor)`, normalizando palavras reservadas para maiúsculas, convertendo literais numéricos para `int` e validando fechamento de aspas simples.
   - **Parser (`ErroSintatico`):** Confere apenas a ordem estrutural dos tokens contra a gramática usando `espera()` e `aceita()`, devolvendo um dicionário que representa a árvore sintática sem consultar o disco.
   - **Análise Semântica (`ErroSemantico`):** Confronta a árvore sintática com o `Catalogo` antes de tocar em qualquer página de dados, garantindo que comandos inválidos (tabela inexistente, quantidade incorreta de colunas, tipo `INT` vs `CHAR(n)` ou estouro de bytes em `CHAR(n)`) falhem sem sujar páginas no cache.

2. **Persistência do Catálogo na Página 1 (`PAGINA_CATALOGO = 1`):**
   - O catálogo é uma tabela autodescritiva gravada na Página 1 com registros fixos de **236 bytes** (`nome CHAR(32)`, `primeira INT`, `colunas CHAR(200)`).
   - Ao abrir um banco existente, o `Catalogo` lê os registros da Página 1 via `Cache` e reconstrói em memória os objetos `Esquema` de cada tabela usando o próprio parser de colunas (`analisa_colunas`), permitindo que novos processos executem `SELECT` e `INSERT` sem terem visto o `CREATE TABLE`.

3. **Layout de Página de Dados e Serialização Fixa (`Esquema`):**
   - Cada página de tabela mantém o cabeçalho de 16 bytes (`<HHI8s`: `n_slots`, `tam_registro`, `num_pagina` e 8 bytes reservados para o LSN do M7).
   - Strings `CHAR(n)` são codificadas em UTF-8 e preenchidas com `\x00` até `n` bytes (`ljust`), mantendo todos os registros com tamanho fixo (ex.: 28 bytes para `aluno`, cabendo até `(4096 - 16) // 28 = 145` registros na página 2).