"""
Lista de Compras — objeto central do momento "antes da compra".

Contrato conceitual: docs/POLITICA_COMPRAS.md, docs/CASOS_DE_USO_COMPRAS.md,
docs/MODELO_DOMINIO_COMPRAS.md.

Fiada 1: criar e consultar Lista de Compras, com sugestão de itens recorrentes
baseada em histórico real de itens_pedido — nunca inventada. Sem vínculo com
orçamento, sem alertas proativos (isso é fiada futura).

Toda função recebe db_path como parâmetro explícito (ADR-002) — importável sem
inicializar o bot.
"""

import sqlite3
from enum import Enum


class StatusLista(str, Enum):
    ABERTA = "aberta"
    ENCERRADA = "encerrada"
    DESCARTADA = "descartada"


class StatusItem(str, Enum):
    PENDENTE = "pendente"
    COMPRADO = "comprado"
    REMOVIDO = "removido"


def init_db_compras(db_path):
    with sqlite3.connect(db_path) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS listas_compra (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ggv        TEXT NOT NULL,
                status     TEXT NOT NULL DEFAULT 'aberta',
                criado_em  TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS lista_compra_itens (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                lista_id    INTEGER NOT NULL,
                descricao   TEXT NOT NULL,
                unidade     TEXT,
                quantidade  REAL,
                status      TEXT NOT NULL DEFAULT 'pendente',
                criado_em   TEXT DEFAULT (datetime('now','localtime'))
            )
        """)


def buscar_lista_aberta(db_path, ggv):
    """Retorna a Lista de Compras aberta da obra, se existir."""
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        row = con.execute(
            "SELECT * FROM listas_compra WHERE ggv=? AND status=? ORDER BY criado_em DESC LIMIT 1",
            (ggv, StatusLista.ABERTA.value)
        ).fetchone()
        return dict(row) if row else None


def buscar_lista(db_path, lista_id):
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM listas_compra WHERE id=?", (lista_id,)).fetchone()
        return dict(row) if row else None


def criar_ou_buscar_lista_aberta(db_path, ggv):
    """Retorna (lista_id, criada_agora) — reaproveita a lista aberta da obra, se existir."""
    lista = buscar_lista_aberta(db_path, ggv)
    if lista:
        return lista["id"], False
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            "INSERT INTO listas_compra (ggv, status) VALUES (?, ?)",
            (ggv, StatusLista.ABERTA.value)
        )
        return cur.lastrowid, True


def sugerir_itens(db_path, ggv, limite=8):
    """
    Itens recorrentes já comprados nesta obra, com o último preço pago quando existir.

    Nunca inventa: retorna lista vazia se não houver nenhum item histórico para a obra —
    quem chama deve comunicar essa ausência claramente, não silenciar (Princípio 8 da
    Política de Compras).
    """
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("""
            SELECT ip.descricao, ip.unidade, COUNT(*) as frequencia, MAX(ip.criado_em) as ultima_vez
            FROM itens_pedido ip
            JOIN lancamentos l ON ip.pfm_codigo = l.pfm_codigo
            WHERE l.ggv = ? AND ip.descricao IS NOT NULL AND ip.descricao != ''
            GROUP BY LOWER(ip.descricao)
            ORDER BY frequencia DESC, ultima_vez DESC
            LIMIT ?
        """, (ggv, limite)).fetchall()

        sugestoes = []
        for row in rows:
            preco = con.execute("""
                SELECT ip.valor_unitario
                FROM itens_pedido ip
                JOIN lancamentos l ON ip.pfm_codigo = l.pfm_codigo
                WHERE l.ggv = ? AND LOWER(ip.descricao) = LOWER(?) AND ip.valor_unitario IS NOT NULL
                ORDER BY ip.criado_em DESC
                LIMIT 1
            """, (ggv, row["descricao"])).fetchone()
            sugestoes.append({
                "descricao": row["descricao"],
                "unidade": row["unidade"] or "",
                "frequencia": row["frequencia"],
                "ultimo_preco": preco["valor_unitario"] if preco else None,
            })
        return sugestoes


def adicionar_item(db_path, lista_id, descricao, unidade="", quantidade=None):
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            "INSERT INTO lista_compra_itens (lista_id, descricao, unidade, quantidade, status) "
            "VALUES (?,?,?,?,?)",
            (lista_id, descricao.strip(), (unidade or "").strip(), quantidade, StatusItem.PENDENTE.value)
        )
        return cur.lastrowid


def remover_item(db_path, item_id):
    with sqlite3.connect(db_path) as con:
        con.execute(
            "UPDATE lista_compra_itens SET status=? WHERE id=?",
            (StatusItem.REMOVIDO.value, item_id)
        )


def listar_itens(db_path, lista_id):
    """Itens ativos da lista (pendentes ou comprados) — remove os descartados da visão padrão."""
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM lista_compra_itens WHERE lista_id=? AND status != ? ORDER BY id",
            (lista_id, StatusItem.REMOVIDO.value)
        ).fetchall()
        return [dict(r) for r in rows]
