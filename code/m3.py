import os
import struct
from bisect import bisect_left, bisect_right
from m1_2 import Pager
from m2 import Cache


class ArvoreBMais:
 
    CAB_FMT = "<BBHI8s"
    TAM_CAB = 16

    def __init__(self, cache: Cache, raiz: int | None = None, ordem: int = 340):
        self.cache = cache
        self.pager = cache.pager
        self.max_chaves = ordem 
        if raiz is None:
            self.raiz = self._nova_pagina(eh_folha=True)
        else:
            self.raiz = raiz

    # Serialização do Nó dentro da Página de 4096 bytes (para o NOTES.md)

    def _nova_pagina(self, eh_folha: bool) -> int:
        p = self.pager.aloca()
        buf = self.cache.fixa(p)
        try:
            buf[:] = bytes(Pager.TAM_PAGINA)
            struct.pack_into(self.CAB_FMT, buf, 0, 1 if eh_folha else 0, 0, 0, 0, b"\x00" * 8)
            return p
        finally:
            self.cache.solta(p, sujou=True)

    def _le_no(self, buf: bytearray):
        eh_folha, _, n_chaves, prox, _ = struct.unpack_from(self.CAB_FMT, buf, 0)
        chaves = []
        if eh_folha:
            rids = []
            for i in range(n_chaves):
                c, rp, rs = struct.unpack_from("<III", buf, self.TAM_CAB + i * 12)
                chaves.append(c)
                rids.append((rp, rs))
            return True, chaves, rids, prox
        else:
            filho0, = struct.unpack_from("<I", buf, self.TAM_CAB)
            filhos = [filho0]
            for i in range(n_chaves):
                c, f = struct.unpack_from("<II", buf, self.TAM_CAB + 4 + i * 8)
                chaves.append(c)
                filhos.append(f)
            return False, chaves, filhos, 0

    def _escreve_no(self, buf: bytearray, eh_folha: bool, chaves: list, dados: list, prox: int = 0):
        struct.pack_into(self.CAB_FMT, buf, 0, 1 if eh_folha else 0, 0, len(chaves), prox, b"\x00" * 8)
        if eh_folha:
            for i, (c, (rp, rs)) in enumerate(zip(chaves, dados)):
                struct.pack_into("<III", buf, self.TAM_CAB + i * 12, c, rp, rs)
        else:
            struct.pack_into("<I", buf, self.TAM_CAB, dados[0])
            for i, c in enumerate(chaves):
                struct.pack_into("<II", buf, self.TAM_CAB + 4 + i * 8, c, dados[i + 1])

    # Operações de Busca (Pontual e por Faixa / BETWEEN)

    def _desce_ate_folha(self, chave: int) -> int:
        pag = self.raiz
        while True:
            buf = self.cache.fixa(pag)
            try:
                eh_folha, chaves, dados, _ = self._le_no(buf)
                if eh_folha:
                    return pag
                # Regra do slide: à esquerda < K; à direita >= K (bisect_right)
                idx = bisect_right(chaves, chave)
                pag = dados[idx]
            finally:
                self.cache.solta(pag)

    def busca(self, chave: int) -> tuple[int, int] | None:

        """
        Desce a árvore até a folha e devolve o RID (pagina, slot) ou None.
        Número de páginas fixadas é igual à altura da árvore.
        """
        
        folha = self._desce_ate_folha(chave)
        buf = self.cache.fixa(folha)
        try:
            _, chaves, rids, _ = self._le_no(buf)
            idx = bisect_left(chaves, chave)
            if idx < len(chaves) and chaves[idx] == chave:
                return rids[idx]
            return None
        finally:
            self.cache.solta(folha)

    def busca_faixa(self, ch_ini: int, ch_fim: int):
        
        pag = self._desce_ate_folha(ch_ini)
        while pag != 0:
            buf = self.cache.fixa(pag)
            try:
                _, chaves, rids, prox = self._le_no(buf)
                for c, rid in zip(chaves, rids):
                    if c < ch_ini:
                        continue
                    if c > ch_fim:
                        return
                    yield c, rid
                pag = prox
            finally:
                self.cache.solta(pag)

    # Inserção com Divisão (Split de Folha, Nó Interno e Raiz)
    def insere(self, chave: int, rid: tuple[int, int]) -> None:
        promovido = self._insere_rec(self.raiz, chave, rid)
        if promovido is not None:
            ch_subiu, pag_dir = promovido
            nova_raiz = self._nova_pagina(eh_folha=False)
            buf = self.cache.fixa(nova_raiz)
            try:
                self._escreve_no(buf, False, [ch_subiu], [self.raiz, pag_dir])
            finally:
                self.cache.solta(nova_raiz, sujou=True)
            self.raiz = nova_raiz

    def _insere_rec(self, pag: int, chave: int, rid: tuple[int, int]):
        buf = self.cache.fixa(pag)
        try:
            eh_folha, chaves, dados, prox = self._le_no(buf)
            if eh_folha:
                idx = bisect_left(chaves, chave)
                if idx < len(chaves) and chaves[idx] == chave:
                    dados[idx] = rid  # Atualiza RID se a chave já existir
                else:
                    chaves.insert(idx, chave)
                    dados.insert(idx, rid)

                if len(chaves) <= self.max_chaves:
                    self._escreve_no(buf, True, chaves, dados, prox)
                    return None

                # Divisão de folha: metade fica na esquerda, metade vai para a direita.
                meio = len(chaves) // 2
                pag_dir = self._nova_pagina(eh_folha=True)
                buf_dir = self.cache.fixa(pag_dir)
                try:
                    self._escreve_no(buf_dir, True, chaves[meio:], dados[meio:], prox)
                finally:
                    self.cache.solta(pag_dir, sujou=True)

                self._escreve_no(buf, True, chaves[:meio], dados[:meio], pag_dir)
                return chaves[meio], pag_dir

            else:
                idx = bisect_right(chaves, chave)
                filho = dados[idx]
        finally:
            # Se era folha, foi modificada; se era interno, solta antes de descer para não prender frame
            self.cache.solta(pag, sujou=eh_folha)

        # Desce recursivamente sem manter o pai fixado durante a descida
        promovido = self._insere_rec(filho, chave, rid)
        if promovido is None:
            return None

        ch_subiu, filho_dir = promovido
        buf = self.cache.fixa(pag)
        try:
            _, chaves, filhos, _ = self._le_no(buf)
            idx = bisect_right(chaves, ch_subiu)
            chaves.insert(idx, ch_subiu)
            filhos.insert(idx + 1, filho_dir)

            if len(chaves) <= self.max_chaves:
                self._escreve_no(buf, False, chaves, filhos)
                return None

            # Divisão de nó interno: a chave do meio sobe e NÃO fica nos filhos
            meio = len(chaves) // 2
            ch_meio = chaves[meio]
            pag_dir = self._nova_pagina(eh_folha=False)
            buf_dir = self.cache.fixa(pag_dir)
            try:
                self._escreve_no(buf_dir, False, chaves[meio + 1:], filhos[meio + 1:])
            finally:
                self.cache.solta(pag_dir, sujou=True)

            self._escreve_no(buf, False, chaves[:meio], filhos[:meio + 1])
            return ch_meio, pag_dir
        finally:
            self.cache.solta(pag, sujou=True)


# Testes dos Exercícios 1 e 2 dos Slides do M3
if __name__ == "__main__":
    arq = "teste_m3.db"
    if os.path.exists(arq):
        os.remove(arq)

    pager = Pager(arq)
    cache = Cache(pager, capacidade=16)

    arvore = ArvoreBMais(cache, ordem=3)

    # Exercício 1 do slide: inserir 10, 20, 5, 30, 25, 40, 15
    seq_ex1 = [10, 20, 5, 30, 25, 40, 15]
    for i, ch in enumerate(seq_ex1):
        arvore.insere(ch, (2, i))  

    buf_raiz = cache.fixa(arvore.raiz)
    _, chaves_raiz, filhos_raiz, _ = arvore._le_no(buf_raiz)
    cache.solta(arvore.raiz)
    print(f"[Ex. 1] Chaves na raiz: {chaves_raiz} (esperado: [20, 30])")

    leituras_antes = cache.acertos + cache.faltas
    rid_25 = arvore.busca(25)
    leituras_busca = (cache.acertos + cache.faltas) - leituras_antes
    print(f"[Ex. 1] Busca(25) -> RID={rid_25} | Páginas lidas: {leituras_busca} (esperado: 2)")

    for i, ch in enumerate([35, 45, 50, 55], start=len(seq_ex1)):
        arvore.insere(ch, (3, i))

    faixa = list(arvore.busca_faixa(12, 33))
    print(f"[Ex. 2] BETWEEN 12 AND 33 -> {[c for c, _ in faixa]} (esperado: [15, 20, 25, 30])")

    cache.descarrega()
    pager.fecha()