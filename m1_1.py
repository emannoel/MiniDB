import os

class Pager:
    TAM_PAGINA = 4096

    def __init__(self, caminho: str):
        self.caminho = caminho
        novo = not os.path.exists(caminho)
        self.f = open(caminho, "w+b" if novo else "r+b")
        self.f.seek(0, os.SEEK_END)
        tamanho_total = self.f.tell()
        if tamanho_total % self.TAM_PAGINA != 0:
            raise IOError(
                f"Arquivo corrompido: tamanho ({tamanho_total} bytes) "
                f"não é múltiplo do tamanho da página ({self.TAM_PAGINA} bytes)."
            )
        self.n_paginas = tamanho_total // self.TAM_PAGINA

    def _valida(self, n: int) -> None:
        if n < 0 or n >= self.n_paginas:
            raise IndexError(
                f"Página {n} fora dos limites. Total de páginas alocadas: {self.n_paginas}"
            )

    def le(self, n: int) -> bytearray:
        self._valida(n)
        offset = n * self.TAM_PAGINA
        self.f.seek(offset)
        buf = self.f.read(self.TAM_PAGINA)

        if len(buf) != self.TAM_PAGINA:
            raise IOError(f"Página {n} truncada: lidos apenas {len(buf)} bytes.")

        return bytearray(buf)

    def escreve(self, n: int, buf: bytes | bytearray) -> None:
        self._valida(n)
        if len(buf) != self.TAM_PAGINA:
            raise ValueError(
                f"Tamanho do buffer inválido: esperado {self.TAM_PAGINA} bytes, "
                f"recebido {len(buf)} bytes."
            )

        offset = n * self.TAM_PAGINA
        self.f.seek(offset)
        self.f.write(buf)

    def aloca(self) -> int:
        n = self.n_paginas
        offset = n * self.TAM_PAGINA
        self.f.seek(offset)
        self.f.write(bytes(self.TAM_PAGINA))
        self.n_paginas += 1
        return n

    def sync(self) -> None:
        self.f.flush()
        os.fsync(self.f.fileno())
