import os
import sys
import struct
from m1_2 import Pager
from m2 import Cache



# Exceções de cada etapa do Módulo 4

class ErroLexico(Exception):
    pass


class ErroSintatico(Exception):
    pass


class ErroSemantico(Exception):
    pass


# Etapa 1 — Tokenizador

PALAVRAS = {
    "CREATE", "TABLE", "INT", "CHAR",
    "INSERT", "INTO", "VALUES",
    "SELECT", "FROM", "WHERE",
}


def tokeniza(sql: str) -> list[tuple[str, object]]:
    tokens, i = [], 0
    while i < len(sql):
        c = sql[i]
        if c.isspace():
            i += 1
        elif c.isalpha() or c == "_":
            j = i
            while j < len(sql) and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            p = sql[i:j]
            if p.upper() in PALAVRAS:
                tokens.append(("PALAVRA", p.upper()))
            else:
                tokens.append(("NOME", p))
            i = j
        elif c.isdigit():
            j = i
            while j < len(sql) and sql[j].isdigit():
                j += 1
            tokens.append(("NUMERO", int(sql[i:j])))
            i = j
        elif c == "'":
            j = sql.find("'", i + 1)
            if j < 0:
                raise ErroLexico(f"aspas sem fechamento na posição {i}")
            tokens.append(("TEXTO", sql[i + 1:j]))
            i = j + 1
        elif c in "(),;*=":
            tokens.append(("SIMBOLO", c))
            i += 1
        else:
            raise ErroLexico(f"caractere inesperado {c!r} na posição {i}")
    return tokens + [("FIM", None)]



# Etapa 2 — Parser (Descida Recursiva)

class Parser:
    def __init__(self, tokens: list[tuple[str, object]]):
        self.tokens, self.i = tokens, 0

    def olha(self) -> tuple[str, object]:
        return self.tokens[self.i]

    def aceita(self, tipo: str, valor: object = None) -> bool:
        t, v = self.tokens[self.i]
        if t == tipo and (valor is None or v == valor):
            self.i += 1
            return True
        return False

    def espera(self, tipo: str, valor: object = None) -> object:
        t, v = self.tokens[self.i]
        if t != tipo or (valor is not None and v != valor):
            raise ErroSintatico(f"esperava {valor or tipo}, veio {v!r}")
        self.i += 1
        return v

    def valor(self) -> object:
        t, v = self.olha()
        if t in ("NUMERO", "TEXTO"):
            self.i += 1
            return v
        raise ErroSintatico(f"esperava valor, veio {v!r}")

    def coluna(self) -> tuple[str, str, int]:
        nome = self.espera("NOME")
        if self.aceita("PALAVRA", "INT"):
            return (nome, "INT", 4)
        self.espera("PALAVRA", "CHAR")
        self.espera("SIMBOLO", "(")
        n = self.espera("NUMERO")
        self.espera("SIMBOLO", ")")
        return (nome, "CHAR", n)

    def create(self) -> dict:
        self.espera("PALAVRA", "CREATE")
        self.espera("PALAVRA", "TABLE")
        tabela = self.espera("NOME")
        self.espera("SIMBOLO", "(")
        colunas = [self.coluna()]
        while self.aceita("SIMBOLO", ","):
            colunas.append(self.coluna())
        self.espera("SIMBOLO", ")")
        return {"op": "CREATE", "tabela": tabela, "colunas": colunas}

    def insert(self) -> dict:
        self.espera("PALAVRA", "INSERT")
        self.espera("PALAVRA", "INTO")
        tabela = self.espera("NOME")
        self.espera("PALAVRA", "VALUES")
        self.espera("SIMBOLO", "(")
        valores = [self.valor()]
        while self.aceita("SIMBOLO", ","):
            valores.append(self.valor())
        self.espera("SIMBOLO", ")")
        return {"op": "INSERT", "tabela": tabela, "valores": valores}

    def select(self) -> dict:
        self.espera("PALAVRA", "SELECT")
        if self.aceita("SIMBOLO", "*"):
            colunas = ["*"]
        else:
            colunas = [self.espera("NOME")]
            while self.aceita("SIMBOLO", ","):
                colunas.append(self.espera("NOME"))
        self.espera("PALAVRA", "FROM")
        tabela = self.espera("NOME")
        where = None
        if self.aceita("PALAVRA", "WHERE"):
            col = self.espera("NOME")
            self.espera("SIMBOLO", "=")
            where = (col, self.valor())
        return {"op": "SELECT", "colunas": colunas, "tabela": tabela, "where": where}

    def comando(self) -> dict:
        _, v = self.olha()
        if v == "CREATE":
            arvore = self.create()
        elif v == "INSERT":
            arvore = self.insert()
        elif v == "SELECT":
            arvore = self.select()
        else:
            raise ErroSintatico(f"comando desconhecido {v!r}")
        self.aceita("SIMBOLO", ";")
        self.espera("FIM")
        return arvore


def analisa(sql: str) -> dict:
    return Parser(tokeniza(sql)).comando()


# Esquema e Serialização de Registros em Páginas (M1 + M4)


class Esquema:
    
    def __init__(self, colunas: list[tuple[str, str, int]]):
        self.colunas = colunas
        fmt = "<"
        for _, tipo, tam in colunas:
            fmt += "i" if tipo == "INT" else f"{tam}s"
        self.fmt = fmt
        self.tam_registro = struct.calcsize(fmt)
        self.max_slots = (Pager.TAM_PAGINA - Pager.TAM_CABECALHO) // self.tam_registro

    def serializa(self, valores: list) -> bytes:
        convertidos = []
        for (_, tipo, tam), v in zip(self.colunas, valores):
            if tipo == "INT":
                convertidos.append(int(v))
            else:
                b = v.encode("utf-8")
                convertidos.append(b.ljust(tam, b"\x00"))
        return struct.pack(self.fmt, *convertidos)

    def desserializa(self, buf: bytes | bytearray, offset: int = 0) -> tuple:
        brutos = struct.unpack_from(self.fmt, buf, offset)
        resultado = []
        for (_, tipo, _), v in zip(self.colunas, brutos):
            if tipo == "INT":
                resultado.append(v)
            else:
                resultado.append(v.rstrip(b"\x00").decode("utf-8"))
        return tuple(resultado)


def inicializa_pagina_dados(cache: Cache, pagina: int, tam_registro: int) -> None:
   
    buf = cache.fixa(pagina)
    try:
        buf[:] = bytes(Pager.TAM_PAGINA)
        struct.pack_into("<HHI8s", buf, 0, 0, tam_registro, pagina, b"\x00" * 8)
    finally:
        cache.solta(pagina, sujou=True)


def insere_registro(cache: Cache, pagina: int, esquema: Esquema, valores: list) -> tuple[int, int]:
    """Grava o registro no primeiro slot livre da página e devolve o RID (pagina, slot)."""
    buf = cache.fixa(pagina)
    try:
        n_slots, tam_reg, num_pag, lsn = struct.unpack_from("<HHI8s", buf, 0)
        if tam_reg == 0:
            tam_reg = esquema.tam_registro
            num_pag = pagina
        if n_slots >= esquema.max_slots:
            raise RuntimeError(f"Página {pagina} está cheia ({n_slots} registros).")

        reg_bytes = esquema.serializa(valores)
        offset = Pager.TAM_CABECALHO + (n_slots * esquema.tam_registro)
        buf[offset:offset + esquema.tam_registro] = reg_bytes

        struct.pack_into("<HHI8s", buf, 0, n_slots + 1, tam_reg, num_pag, lsn)
        return (pagina, n_slots)
    finally:
        cache.solta(pagina, sujou=True)


def le_registros(cache: Cache, pagina: int, esquema: Esquema):
    """Percorre todos os slots ocupados da página desserializando cada registro."""
    buf = cache.fixa(pagina)
    try:
        n_slots, _, _, _ = struct.unpack_from("<HHI8s", buf, 0)
        for slot in range(n_slots):
            offset = Pager.TAM_CABECALHO + (slot * esquema.tam_registro)
            yield esquema.desserializa(buf, offset)
    finally:
        cache.solta(pagina)



# Etapa 3 - Catálogo (Página 1 do disco) e Análise Semântica

ESQUEMA_CATALOGO = Esquema([
    ("nome", "CHAR", 32),
    ("primeira", "INT", 4),
    ("colunas", "CHAR", 200),
])
PAGINA_CATALOGO = 1


def formata_colunas(colunas: list[tuple[str, str, int]]) -> str:
    partes = []
    for nome, tipo, tam in colunas:
        partes.append(f"{nome} INT" if tipo == "INT" else f"{nome} CHAR({tam})")
    return ", ".join(partes)


def analisa_colunas(texto: str) -> list[tuple[str, str, int]]:
    p = Parser(tokeniza(texto))
    cols = [p.coluna()]
    while p.aceita("SIMBOLO", ","):
        cols.append(p.coluna())
    return cols


class Catalogo:
    
    def __init__(self, cache: Cache):
        self.cache = cache
        if cache.pager.n_paginas == 1:
            p_cat = cache.pager.aloca()  # Aloca a página 1 para o catálogo
            inicializa_pagina_dados(cache, p_cat, ESQUEMA_CATALOGO.tam_registro)

        self.tabelas: dict[str, tuple[int, Esquema]] = {}
        for nome, primeira, col_str in le_registros(cache, PAGINA_CATALOGO, ESQUEMA_CATALOGO):
            self.tabelas[nome] = (primeira, Esquema(analisa_colunas(col_str)))

    def cria_tabela(self, nome: str, colunas: list[tuple[str, str, int]]) -> int:
        if nome in self.tabelas:
            raise ErroSemantico(f"tabela {nome} já existe")
        esquema = Esquema(colunas)
        primeira = self.cache.pager.aloca()
        inicializa_pagina_dados(self.cache, primeira, esquema.tam_registro)

        col_str = formata_colunas(colunas)
        insere_registro(self.cache, PAGINA_CATALOGO, ESQUEMA_CATALOGO, [nome, primeira, col_str])
        self.tabelas[nome] = (primeira, esquema)
        return primeira

    def busca(self, nome: str) -> tuple[int, Esquema]:
        if nome not in self.tabelas:
            raise ErroSemantico(f"tabela {nome} não existe")
        return self.tabelas[nome]


def confere_insert(catalogo: Catalogo, tabela: str, valores: list) -> tuple[int, Esquema]:
    primeira, esquema = catalogo.busca(tabela)
    if len(valores) != len(esquema.colunas):
        raise ErroSemantico(
            f"esperava {len(esquema.colunas)} valores, vieram {len(valores)}"
        )
    for (nome_col, tipo, tam), val in zip(esquema.colunas, valores):
        if tipo == "INT":
            if not isinstance(val, int):
                raise ErroSemantico(f"coluna {nome_col} é INT, veio {val!r}")
        elif tipo == "CHAR":
            if not isinstance(val, str):
                raise ErroSemantico(f"coluna {nome_col} é CHAR({tam}), veio {val!r}")
            if len(val.encode("utf-8")) > tam:
                raise ErroSemantico(
                    f"coluna {nome_col} é CHAR({tam}), mas {val!r} tem {len(val.encode('utf-8'))} bytes"
                )
    return primeira, esquema


# Etapa 4 - Execução de Comandos SQL


def executa(sql: str, catalogo: Catalogo, cache: Cache) -> str:
    arvore = analisa(sql)
    op = arvore["op"]

    if op == "CREATE":
        catalogo.cria_tabela(arvore["tabela"], arvore["colunas"])
        return "OK"

    if op == "INSERT":
        primeira, esquema = confere_insert(catalogo, arvore["tabela"], arvore["valores"])
        insere_registro(cache, primeira, esquema, arvore["valores"])
        return "OK 1"

    if op == "SELECT":
        primeira, esquema = catalogo.busca(arvore["tabela"])
        nomes_esquema = [c[0] for c in esquema.colunas]

        # Define quais colunas projetar
        if arvore["colunas"] == ["*"]:
            indices = list(range(len(nomes_esquema)))
        else:
            indices = []
            for col in arvore["colunas"]:
                if col not in nomes_esquema:
                    raise ErroSemantico(f"coluna {col} não existe em {arvore['tabela']}")
                indices.append(nomes_esquema.index(col))

        # Valida cláusula WHERE se estiver presente
        where = arvore["where"]
        if where is not None:
            col_w, val_w = where
            if col_w not in nomes_esquema:
                raise ErroSemantico(f"coluna {col_w} não existe em {arvore['tabela']}")
            idx_w = nomes_esquema.index(col_w)

        linhas = []
        for reg in le_registros(cache, primeira, esquema):
            if where is not None and reg[idx_w] != val_w:
                continue
            campos = [str(reg[i]) for i in indices]
            linhas.append("|".join(campos))

        linhas.append(f"({len(linhas)} linhas)")
        return "\n".join(linhas)



# Ponto de Entrada: modo interativo (stdin) ou bateria de testes dos slides

if __name__ == "__main__":
    # Se passar o nome do arquivo no terminal (ex: python m4.py dados.db), lê SQL do stdin
    if len(sys.argv) > 1:
        pager = Pager(sys.argv[1])
        cache = Cache(pager)
        catalogo = Catalogo(cache)
        try:
            for linha in sys.stdin:
                if linha.strip():
                    print(executa(linha, catalogo, cache))
        finally:
            cache.descarrega()
            pager.fecha()
    else:
        # Demonstração automática da "Meta do M4" e dos Exercícios dos slides
        arq = "teste_m4.db"
        if os.path.exists(arq):
            os.remove(arq)

        print("--- [Processo 1] Criando tabela e inserindo registros ---")
        p1 = Pager(arq)
        c1 = Cache(p1)
        cat1 = Catalogo(c1)

        for cmd in [
            "CREATE TABLE aluno (id INT, matricula INT, nome CHAR(20));",
            "INSERT INTO aluno VALUES (1, 20260001, 'Ana');",
            "INSERT INTO aluno VALUES (2, 20260002, 'Bruno');",
        ]:
            print(f"SQL> {cmd}\n{executa(cmd, cat1, c1)}")

        c1.descarrega()
        p1.fecha()

        print("\n--- [Processo 2] Reabrindo do disco sem ver o CREATE TABLE ---")
        p2 = Pager(arq)
        c2 = Cache(p2)
        cat2 = Catalogo(c2)  # Lê o catálogo da Página 1 diretamente do disco

        cmd_select = "SELECT * FROM aluno;"
        print(f"SQL> {cmd_select}\n{executa(cmd_select, cat2, c2)}")

        print("\n--- [Testes de Erros Léxico, Sintático e Semântico dos Slides] ---")
        testes_erro = [
            "INSERT INTO aluno VALUES (1, 'Ana', 20260001);",                # Semântico: tipo trocado
            "INSERT INTO alunos VALUES (2, 20260002, 'Bruno');",             # Semântico: tabela não existe
            "INSERT INTO aluno VALUES (2, 20260002);",                       # Semântico: faltam valores
            "INSERT INTO aluno VALUES (2, 20260002, Bruno);",                # Sintático: Bruno sem aspas
            "INSERT INTO aluno VALUES (2, 20260002, 'Maria Eduarda Albuquerque');",  # Semântico: > 20 bytes
        ]
        for sql_invalido in testes_erro:
            try:
                executa(sql_invalido, cat2, c2)
            except (ErroLexico, ErroSintatico, ErroSemantico) as e:
                print(f"[Recusado corretamente] {type(e).__name__}: {e}")

        c2.descarrega()
        p2.fecha()