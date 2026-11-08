from collections import OrderedDict
from m1_2 import Pager


class Cache:
    def __init__(self, pager: Pager, capacidade: int = 16):
        self.pager, self.cap = pager, capacidade
        self.frames = {}              # pagina -> bytearray
        self.suja = set()
        self.fixada = {}              # pagina -> contador de pins
        self.uso = OrderedDict()      # ordem LRU (mais antigo primeiro)
        self.acertos = self.faltas = 0

    def fixa(self, n: int) -> bytearray:
        if n in self.frames:
            self.acertos += 1
            self.uso.move_to_end(n)
        else:
            self.faltas += 1
            if len(self.frames) == self.cap:
                self._expulsa()
            self.frames[n] = self.pager.le(n)
            self.uso[n] = True
        self.fixada[n] = self.fixada.get(n, 0) + 1
        return self.frames[n]

    def solta(self, n: int, sujou: bool = False) -> None:
        if sujou:
            self.suja.add(n)
        self.fixada[n] -= 1

    def _expulsa(self) -> None:
        for n in list(self.uso):
            if self.fixada.get(n, 0) == 0:
                if n in self.suja:
                    self.pager.escreve(n, self.frames[n])
                    self.suja.discard(n)
                del self.frames[n], self.uso[n]
                return
        raise RuntimeError("todas as páginas estão fixadas")

    def descarrega(self) -> None:
        for n in list(self.suja):
            self.pager.escreve(n, self.frames[n])
        self.suja.clear()
        self.pager.sync()


def varre(cache: Cache, pager: Pager, le_registro):
    for n in range(1, pager.n_paginas):
        buf = cache.fixa(n)
        try:
            for slot in range(510):
                yield le_registro(buf, slot)
        finally:
            cache.solta(n)