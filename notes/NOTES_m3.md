# NOTES — Módulo 3 (Árvore B+)

## Representação de um Nó dentro da Página (4096 bytes)

Cada nó da Árvore B+ (folha ou interno) ocupa exatamente 1 página de 4096 bytes gerenciada pelo `Cache` (M2) e serializada em *little-endian* via `struct`:

1. **Cabeçalho Comum de 16 bytes (`<BBHI8s`):**
   - **Byte `0` (`uint8`):** `eh_folha` (`1` para nó folha, `0` para nó interno).
   - **Byte `1` (`uint8`):** Reservado para alinhamento (`0`).
   - **Bytes `2–3` (`uint16`):** `n_chaves` (quantidade de chaves atualmente ocupadas no nó).
   - **Bytes `4–7` (`uint32`):** `prox_folha` (número da página da folha seguinte à direita para varredura de faixa `BETWEEN`, ou `0` no fim da lista/nós internos).
   - **Bytes `8–15` (`8 bytes`):** Reservado para o `LSN` do Módulo 7.

2. **Corpo do Nó Folha (4080 bytes úteis):**
   - Guarda apenas pares `(chave, RID)` ordenados pela chave, onde o `RID` é a tupla `(pagina, slot)` do registro no M1.
   - Cada entrada ocupa **12 bytes** (`<III`: `chave` de 4B, `rid_pagina` de 4B e `rid_slot` de 4B), cabendo até **340 chaves por folha** (`4080 // 12`).

3. **Corpo do Nó Interno (4080 bytes úteis):**
   - Guarda apenas chaves separadoras e números de páginas filhas para guiar a descida.
   - Começa com o ponteiro `filho_0` de **4 bytes** (`<I`), seguido por `n_chaves` pares `(chave_i, filho_{i+1})` de **8 bytes** (`<II`), cabendo até **509 chaves e 510 filhos por nó interno** (`(4080 - 4) // 8`).

## Decisão Mais Difícil

- **Divisão (*Split*) de Folha vs. Nó Interno sem Estourar Frames Fixados:**
  - Na divisão de **folha**, a chave mediana (`meio = len // 2`) permanece como primeira chave da nova folha direita (mantendo todos os RIDs nas folhas) e uma cópia dela sobe para o pai, além de atualizar o ponteiro `prox_folha` encadeado.
  - Na divisão de **nó interno**, a chave mediana sobe para o pai e é **removida** do nível inferior, dividindo os ponteiros de filhos em `[:meio+1]` e `[meio+1:]`.
  - Para funcionar mesmo em caches pequenos (ex.: 3 frames), o nó pai é solto (`cache.solta`) antes de descer recursivamente para o filho e só volta a ser fixado caso um filho realmente se divida e promova uma chave.