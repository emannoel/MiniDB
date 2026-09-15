# MiniDB

Um SGBD (Sistema Gerenciador de Banco de Dados) simplificado, desenvolvido para a disciplina de **Banco de Dados II**.

---

## 🛠️ Tecnologias e Decisões de Projeto

* **Linguagem:** Python 3
* **Interface:** Entrada e saída padrão, interpretando um subconjunto de comandos SQL.

---

## 🏗️ Arquitetura dos Módulos

O desenvolvimento do `minidb` é dividido em 7 módulos incrementais:

1. **M1 — Página e Arquivo de Dados:** Estruturação de dados binários em disco e organização por blocos/páginas.
2. **M2 — Cache de Páginas (Buffer Pool):** Gerenciamento de memória RAM para otimizar leitura/escrita em disco (estratégia LRU).
3. **M3 — Árvore B+:** Estruturação e navegação do índice para buscas e inserções eficientes.
4. **M4 — Parser e Catálogo:** Leitura da sintaxe SQL, validação no catálogo e conversão para árvore de execução.
5. **M5 — Executor:** Implementação dos operadores de busca (varredura sequencial e por índice).
6. **M6 — Transações:** Suporte aos comandos `BEGIN`, `COMMIT` e `ROLLBACK`.
7. **M7 — Recuperação (WAL):** Implementação de *Write-Ahead Logging* para garantir consistência e recuperação de dados após falhas brutas (`kill -9`).

---

## 💻 Como Executar

O `minidb` recebe o caminho do arquivo de banco de dados como argumento e lê instruções SQL diretamente da entrada padrão (`stdin`).

### Exemplo de uso via terminal:

```bash
python3 main.py dados.db < consultas.sql
