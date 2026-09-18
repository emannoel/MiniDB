import os
import struct


class Pager:
    TAM_PAGINA = 4096
    TAM_CABECALHO = 16
    TAM_REGISTRO = 8
    MAGIC_NUMBER = b"MINIDB\x00\x00"  # 8 bytes

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

        # Inicializa a Página 0 com Metadados se o arquivo for novo
        if novo:
            self._inicializa_pagina_zero()
        else:
            self._valida_pagina_zero()

    def _inicializa_pagina_zero(self) -> None:
        pag0_id = self.aloca()  # Aloca a página 0
        buf = bytearray(self.TAM_PAGINA)
        struct.pack_into("<8sHH", buf, 0, self.MAGIC_NUMBER, 1, self.TAM_PAGINA)
        self.escreve(pag0_id, buf)

    def _valida_pagina_zero(self) -> None:
        buf = self.le(0)
        magic, versao, tam_pag = struct.unpack_from("<8sHH", buf, 0)

        if magic != self.MAGIC_NUMBER:
            raise ValueError("Arquivo não é um banco MINIDB válido (Magic Number incorreto).")
        if tam_pag != self.TAM_PAGINA:
            raise ValueError(f"Tamanho de página incompatível: {tam_pag} != {self.TAM_PAGINA}")

    def deslocamento_pagina(self, n: int) -> int:
        return n * self.TAM_PAGINA

    def deslocamento_slot(self, pagina: int, slot: int) -> int:
        return (pagina * self.TAM_PAGINA) + self.TAM_CABECALHO + (slot * self.TAM_REGISTRO)

    def _valida(self, n: int) -> None:
        if n < 0 or n >= self.n_paginas:
            raise IndexError(
                f"Página {n} fora dos limites. Total de páginas alocadas: {self.n_paginas}"
            )

    def le(self, n: int) -> bytearray:
        self._valida(n)
        offset = self.deslocamento_pagina(n)
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

        offset = self.deslocamento_pagina(n)
        self.f.seek(offset)
        self.f.write(buf)

    def aloca(self) -> int:
        n = self.n_paginas
        offset = self.deslocamento_pagina(n)
        self.f.seek(offset)
        self.f.write(bytes(self.TAM_PAGINA))
        self.n_paginas += 1
        return n

    def sync(self) -> None:
        self.f.flush()
        os.fsync(self.f.fileno())

    def fecha(self) -> None:
        if not self.f.closed:
            self.sync()
            self.f.close()
    
