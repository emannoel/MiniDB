# NOTES — Módulo 2

## Resumo

Implementação da classe `Cache` (*Buffer Pool*), camada intermediária entre o motor de busca e o `Pager` (M1), responsável por manter cópias de páginas de 4096 bytes em memória principal (*frames*) e minimizar leituras e escritas físicas em disco.

## Decisões de Projeto

1. **Capacidade do Cache e Ambiente de Testes:**
   - **Capacidade Padrão (`16` frames):** Definida como padrão da classe (`64 KB` em memória), equilibrando retenção de páginas quentes e baixo consumo de RAM.
   - **Capacidade nos Testes (`3` frames):** Reduzida propositalmente na suíte de testes para forçar o enchimento rápido do *buffer pool* e validar a expulsão LRU e a persistência de páginas sujas.

2. **Política de Substituição LRU e Decisão Mais Difícil:**
   - Uso de `OrderedDict` (`self.uso`) com `move_to_end(n)` para atualizar a fila LRU em $O(1)$ a cada acerto (*hit*).
   - **Decisão mais difícil:** Coordenar o compartilhamento da mesma referência mutável (`bytearray`) com o contador de fixação (`self.fixada`). Na expulsão (`_expulsa()`), o cache percorre `self.uso` do mais antigo ao mais novo buscando a primeira página com `fixada == 0` e levanta `RuntimeError` caso todas as páginas estejam fixadas.

3. **Controle de Páginas Sujas (*Steal* / *No-Force*):**
   - Alterações em memória são marcadas em `self.suja` via `solta(n, sujou=True)`, evitando gravações em disco a cada tupla alterada.
   - A escrita física via `pager.escreve()` ocorre apenas quando uma página suja é expulsa (*Steal*) ou na chamada explícita de `descarrega()` seguida de `pager.sync()` (*No-Force*).

---

## Métricas do M2

- **Validação LRU (Capacidade = 3 frames):** Para a sequência de acessos `1, 2, 3, 1, 4`, obtivemos **1 acerto** (`acertos = 1`) e **4 faltas** (`faltas = 4`), com expulsão da página `2` e estado final dos frames em `[3, 1, 4]`.
- **Redução de I/O na Varredura:** Leituras repetidas de registros na mesma página ou de páginas residentes no `Cache` realizam **0 chamadas** a `pager.le()`, mantendo a invariante `acertos + faltas == total de chamadas a fixa()`.