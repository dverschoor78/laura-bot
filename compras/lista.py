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


class GrauConfianca(str, Enum):
    """Vocabulário do Princípio 8 da Política de Compras — toda referência apresentada
    declara sua origem e confiança. Usado em laura_grau_confianca_referencia."""
    CONFIRMADA = "confirmada"
    APROXIMADA = "aproximada"
    AUSENTE = "ausente"


class OrigemReferencia(str, Enum):
    ULTIMO_PRECO_PAGO = "ultimo_preco_pago"
    MEDIA_ULTIMAS_COMPRAS = "media_ultimas_compras"
    ITEM_SEMELHANTE = "item_semelhante"
    SEM_REFERENCIA = "sem_referencia"


# Colunas de snapshot — congeladas no momento da confirmação da lista, nunca recalculadas
# depois. insumos_sinapi é atualizada mensalmente; a leitura histórica de uma lista antiga
# não pode mudar de valor sozinha com o tempo (CONSTITUICAO.md — "Dados são sagrados").
_COLUNAS_SNAPSHOT = (
    "sinapi_codigo INTEGER",
    "sinapi_descricao_referencia TEXT",
    "sinapi_unidade_referencia TEXT",
    "sinapi_preco_referencia REAL",
    "sinapi_mes_referencia TEXT",
    "observacoes TEXT",
    "laura_preco_referencia REAL",
    "laura_data_referencia TEXT",
    "laura_fornecedor_referencia TEXT",
    "laura_origem_referencia TEXT",
    "laura_grau_confianca_referencia TEXT",
)

# Identidade comercial do item — mesma categoria de descricao/unidade/quantidade, não
# "referência externa" como as colunas de snapshot acima. Adicionadas 2026-07-04 junto com a
# primeira gravação real de Lista de Compras: sem elas, fabricante e código comercial (já
# extraídos pela Camada 1 desde o início) seriam descartados silenciosamente ao salvar.
_COLUNAS_ITEM = (
    "fabricante TEXT",
    "codigo TEXT",
)

# Atributos do cabeçalho da lista (não do item) — endereço herdado da obra, mas editável
# por lista (nunca sobrescreve obras.endereco_entrega); observações gerais são novas,
# opcionais, pensadas como instrução geral da compra (Dennis, 2026-07-05).
_COLUNAS_LISTA = (
    "endereco_entrega TEXT",
    "observacoes TEXT",
)
_COLUNAS_LISTA_EDITAVEIS = {"endereco_entrega", "observacoes"}


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
        for col in _COLUNAS_LISTA:
            try:
                con.execute(f"ALTER TABLE listas_compra ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass
        con.execute(f"""
            CREATE TABLE IF NOT EXISTS lista_compra_itens (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                lista_id      INTEGER NOT NULL,
                descricao     TEXT NOT NULL,
                unidade       TEXT,
                quantidade    REAL,
                {", ".join(_COLUNAS_ITEM)},
                {", ".join(_COLUNAS_SNAPSHOT)},
                status        TEXT NOT NULL DEFAULT 'pendente',
                criado_em     TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        # ALTER seguro — cobre bancos onde a tabela já existia antes destas colunas
        for col in _COLUNAS_ITEM + _COLUNAS_SNAPSHOT:
            try:
                con.execute(f"ALTER TABLE lista_compra_itens ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass


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


def atualizar_lista(db_path, lista_id, **kwargs):
    """Atualiza atributos do cabeçalho da lista (endereço de entrega, observações gerais)
    — nunca o item. Só aceita colunas na allowlist (mesmo padrão de segurança de
    atualizar()/atualizar_obra() em bot.py, corrigido em 2026-07-03 contra SQL injection
    via nome de coluna dinâmico)."""
    campos = {k: v for k, v in kwargs.items() if k in _COLUNAS_LISTA_EDITAVEIS}
    if not campos:
        return
    set_clause = ", ".join(f"{k}=?" for k in campos)
    with sqlite3.connect(db_path) as con:
        con.execute(f"UPDATE listas_compra SET {set_clause} WHERE id=?", (*campos.values(), lista_id))


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


def adicionar_item(
    db_path, lista_id, descricao, unidade="", quantidade=None,
    fabricante=None, codigo=None,
    sinapi_codigo=None, sinapi_descricao_referencia=None, sinapi_unidade_referencia=None,
    sinapi_preco_referencia=None, sinapi_mes_referencia=None,
    observacoes=None,
    laura_preco_referencia=None, laura_data_referencia=None, laura_fornecedor_referencia=None,
    laura_origem_referencia=None, laura_grau_confianca_referencia=None,
):
    """Grava o item já com os snapshots (SINAPI e referência interna da Laura) congelados
    no momento da confirmação — nunca recalculados depois. insumos_sinapi muda todo mês;
    itens_pedido/lancamentos crescem a cada compra; a leitura de uma lista antiga não pode
    mudar de valor sozinha com o tempo (CONSTITUICAO.md — "Dados são sagrados"). Todos os
    parâmetros de snapshot são opcionais — item sem nenhuma correspondência ainda é um
    item válido (Princípio 8: ausência de referência também é informação)."""
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            """INSERT INTO lista_compra_itens (
                lista_id, descricao, unidade, quantidade, fabricante, codigo, status,
                sinapi_codigo, sinapi_descricao_referencia, sinapi_unidade_referencia,
                sinapi_preco_referencia, sinapi_mes_referencia, observacoes,
                laura_preco_referencia, laura_data_referencia, laura_fornecedor_referencia,
                laura_origem_referencia, laura_grau_confianca_referencia
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                lista_id, descricao.strip(), (unidade or "").strip(), quantidade, fabricante, codigo,
                StatusItem.PENDENTE.value,
                sinapi_codigo, sinapi_descricao_referencia, sinapi_unidade_referencia,
                sinapi_preco_referencia, sinapi_mes_referencia, observacoes,
                laura_preco_referencia, laura_data_referencia, laura_fornecedor_referencia,
                laura_origem_referencia, laura_grau_confianca_referencia,
            )
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
