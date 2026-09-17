import os

TAM_PAGINA = 4096
TAM_CABECALHO = 16
TAM_REGISTRO = 8

def le_pagina(f, n: int) -> bytes:
    f.seek(n * TAM_PAGINA)
    buf = f.read(TAM_PAGINA)
    if len(buf) != TAM_PAGINA:
        raise ValueError(f"Página {n} incompleta ou fora dos limites ({len(buf)}B).")
    return buf

def escreve_pagina(f, n: int, buf: bytes) -> None:
    if len(buf) != TAM_PAGINA:
        raise ValueError(f"Buffer de tamanho inválido ({len(buf)}B).")
    f.seek(n * TAM_PAGINA)
    f.write(buf)

def deslocamento(pagina: int, slot: int) -> int:
    return (pagina * TAM_PAGINA) + TAM_CABECALHO + (slot * TAM_REGISTRO)

if __name__ == "__main__":
    nome_arquivo = "teste.db"
    
    # Escrita inicial (página 2 e página 3)
    f = open(nome_arquivo, "w+b")
    escreve_pagina(f, 2, b"A" * TAM_PAGINA)
    escreve_pagina(f, 3, b"B" * TAM_PAGINA)
    f.close() 
    # Reabertura para validação
    f = open(nome_arquivo, "r+b")
    p2 = le_pagina(f, 2)
    
    # Verificações
    print(len(p2), p2 == b"A" * TAM_PAGINA)
    print(le_pagina(f, 3)[:1])
    print(os.path.getsize(nome_arquivo) % 4096 == 0)
    
    # Deslocamento
    offset_rid = deslocamento(2, 0)
    print(f"Byte do RID (2, 0): {offset_rid}")
    
    f.close()
