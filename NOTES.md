# Módulo 1

## Conceitos Fundamentais

 **Página (4096 bytes):** Bloco contíguo de tamanho fixo de memória/disco. É a unidade mínima de leitura e escrita do SGBD. Organização física onde o arquivo `.db` é composto por páginas sequenciais. O endereço de uma página $n$ é calculado diretamente por `offset = n * 4096`.
  * `f.flush()`: Limpa o buffer interno da aplicação (Python) e entrega os dados ao buffer do sistema operacional.
  * `os.fsync()`: Força o SO a gravar fisicamente o cache de RAM nos setores do disco (SSD/HD).
 **Tipos Binários em Python:**
  * `bytes`: Estrutura imutável usada nas operações de I/O do arquivo (`read`/`write`).
  * `bytearray`: Estrutura mutável usada para manipular dados de uma página diretamente na RAM antes da gravação.

## Contrato do Pager

 **Abertura Segura:** Checa se o arquivo existe para definir o modo de abertura (`r+b` para arquivos existentes e `w+b` para novos), evitando apagar dados por engano.
 **Validação Rígida:** Garante que todas as leituras e escritas recebam/retornem buffers de exatamente 4096 bytes e impede acessos a páginas inexistentes.
 **Alocação Sequencial:** Adiciona novas páginas escrevendo 4096 bytes zerados (`b'\x00'`) no final do arquivo.
