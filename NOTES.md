# NOTES — Módulo 1

## Resumo
Implementação da classe Pager, componente responsável por gerenciar os arquivos em páginas fixas de 4096 bytes, permitindo a manipulação binária.

## Decisões de Projeto

1. **Página 0 (Metadados Globais):**
   * Contém a assinatura binária `b"MINIDB\x00\x00"` (Magic Number), a versão do schema e a validação do tamanho de página (`4096`).
   * Arquivos sem essa assinatura ou com tamanhos desalinhados são recusados na abertura.

2. **Cálculo de Deslocamento (*Offset*):**
   * Deslocamento de Página: $n \times 4096$.
   * Deslocamento de Slot: $(n \times 4096) + 16 + (\text{slot} \times 8)$.

3. **Garantia de Durabilidade:**
   * `flush()` esvazia os buffers da aplicação Python para o Kernel.
   * `os.fsync()` força o registro físico no disco (SSD/HD), resistindo a um encerramento abrupto (`kill -9`).

---

## Métricas do M1

* **Total de Páginas do Arquivo de Teste:** $N$ páginas (Página 0 reservada para Metadados + Páginas de Dados alocadas).
* **Varredura Completa (*Sequential Scan*):** Para ler todo o banco, o sistema realiza exatamente **1 leitura de I/O por página alocada** (`n_paginas` chamadas de `le()`).
