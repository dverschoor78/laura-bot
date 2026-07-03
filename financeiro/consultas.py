"""
Consultas rápidas ao banco da Laura.

Funções otimizadas para acesso instantâneo a informações consolidadas.
Usadas por relatórios, CLI e respostas ao Dennis.

Sempre recebem db_path como parametro explícito (ADR-002).
"""

import sqlite3
from pathlib import Path
from datetime import datetime


def obter_pedido_completo(db_path, pfm_codigo: str) -> dict:
    """
    Retorna todos os dados de um pedido em uma única chamada.

    Consolida: lançamento + parcelas + itens + documentos + fornecedor.
    Tempo esperado: <50ms com índices.

    Args:
        db_path: Path ou str do banco (data/laura.db)
        pfm_codigo: Ex: "GGV03-001"

    Returns:
        dict com estrutura:
        {
            "codigo": "GGV03-001",
            "fornecedor": {...},
            "lancamento": {...},
            "parcelas": [...],
            "itens": [...],
            "documentos": {...}
        }
    """
    if isinstance(db_path, str):
        db_path = Path(db_path)

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    try:
        # Lançamento
        lanc = con.execute(
            "SELECT * FROM lancamentos WHERE pfm_codigo = ?",
            (pfm_codigo,)
        ).fetchone()

        if not lanc:
            return {"erro": f"Pedido {pfm_codigo} nao encontrado"}

        lanc_dict = dict(lanc)

        # Fornecedor
        fornec = con.execute(
            "SELECT * FROM fornecedores WHERE LOWER(nome) = LOWER(?)",
            (lanc["fornecedor"],)
        ).fetchone()
        fornec_dict = dict(fornec) if fornec else {}

        # Parcelas
        parcelas = con.execute(
            "SELECT id, valor, data_pagamento, status, doc_id_comprovante, doc_id_recibo, doc_id_recibo_assinado "
            "FROM parcelas_pagamento WHERE pfm_codigo = ? ORDER BY criado_em",
            (pfm_codigo,)
        ).fetchall()
        parcelas_list = [dict(p) for p in parcelas]

        # Itens da compra
        itens = con.execute(
            "SELECT descricao, quantidade, unidade, valor_unitario, valor_total "
            "FROM itens_pedido WHERE pfm_codigo = ? ORDER BY numero",
            (pfm_codigo,)
        ).fetchall()
        itens_list = [dict(i) for i in itens]

        # Documentos (NF, recibo, comprovante, orçamento)
        doc_ids = [lanc["doc_id"], lanc["doc_id_nfe"], lanc["doc_id_recibo"], lanc["doc_id_comprovante"]]
        doc_ids = [d for d in doc_ids if d]  # Remove NULLs

        docs_dict = {}
        if doc_ids:
            placeholders = ",".join("?" * len(doc_ids))
            docs = con.execute(
                f"SELECT id, tipo, nome, criado_em FROM documentos WHERE id IN ({placeholders})",
                doc_ids
            ).fetchall()
            for doc in docs:
                doc_dict = dict(doc)
                docs_dict[doc["tipo"]] = doc_dict

        # Consolidar
        return {
            "codigo": pfm_codigo,
            "lancamento": lanc_dict,
            "fornecedor": fornec_dict,
            "parcelas": parcelas_list,
            "itens": itens_list,
            "documentos": docs_dict
        }

    finally:
        con.close()


def obter_consolidado_obra(db_path, ggv: str) -> dict:
    """
    Resumo financeiro consolidado de uma obra.

    Retorna: total pedidos, total pago, saldo, pedidos por status.
    Tempo esperado: <100ms.
    """
    if isinstance(db_path, str):
        db_path = Path(db_path)

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    try:
        # Estatísticas gerais
        stats = con.execute("""
            SELECT
                COUNT(*) as total_pedidos,
                SUM(valor) as total_valor,
                COUNT(CASE WHEN status='pago' THEN 1 END) as pedidos_pagos,
                COUNT(CASE WHEN status='a_pagar' THEN 1 END) as pedidos_abertos,
                COUNT(CASE WHEN status LIKE 'pago%' OR status='a_pagar' THEN 1 END) as pedidos_ativos
            FROM lancamentos
            WHERE ggv = ?
        """, (ggv,)).fetchone()
        stats_dict = dict(stats) if stats else {}

        # Total pago (soma das parcelas efetivas)
        pago = con.execute("""
            SELECT COALESCE(SUM(valor), 0) as total_pago
            FROM parcelas_pagamento
            WHERE pfm_codigo IN (SELECT pfm_codigo FROM lancamentos WHERE ggv = ?)
        """, (ggv,)).fetchone()
        pago_total = pago["total_pago"] if pago else 0

        # Saldo
        saldo = (stats_dict.get("total_valor", 0) or 0) - pago_total

        # Pedidos por status
        por_status = con.execute("""
            SELECT status, COUNT(*) as qtd, SUM(valor) as valor
            FROM lancamentos
            WHERE ggv = ?
            GROUP BY status
        """, (ggv,)).fetchall()

        return {
            "ggv": ggv,
            "total_pedidos": stats_dict.get("total_pedidos", 0),
            "total_valor": stats_dict.get("total_valor", 0),
            "total_pago": pago_total,
            "saldo": saldo,
            "pedidos_pagos": stats_dict.get("pedidos_pagos", 0),
            "pedidos_abertos": stats_dict.get("pedidos_abertos", 0),
            "por_status": [dict(row) for row in por_status]
        }

    finally:
        con.close()


def listar_pedidos_pendentes(db_path, ggv: str = None) -> list:
    """
    Lista todos os pedidos que ainda faltam documento fiscal.

    Retorna: pedidos que estao pagos mas sem NF-e ou recibo.
    """
    if isinstance(db_path, str):
        db_path = Path(db_path)

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    try:
        query = """
            SELECT
                l.pfm_codigo,
                l.ggv,
                l.fornecedor,
                l.valor,
                l.status,
                COALESCE(SUM(p.valor), 0) as valor_pago,
                CASE WHEN l.doc_id_nfe IS NULL THEN 'falta_nfe' ELSE 'ok_nfe' END as nfe_status,
                CASE WHEN l.doc_id_recibo IS NULL THEN 'falta_recibo' ELSE 'ok_recibo' END as recibo_status
            FROM lancamentos l
            LEFT JOIN parcelas_pagamento p ON l.pfm_codigo = p.pfm_codigo
            WHERE l.status LIKE 'pago%'
        """
        params = []

        if ggv:
            query += " AND l.ggv = ?"
            params.append(ggv)

        query += " GROUP BY l.pfm_codigo ORDER BY l.criado_em DESC"

        rows = con.execute(query, params).fetchall()

        # Filtrar: mostrar só os que realmente faltam doc
        pendentes = []
        for row in rows:
            row_dict = dict(row)
            # Falta se: nao tem NF E nao tem recibo
            if row_dict["nfe_status"] == "falta_nfe" and row_dict["recibo_status"] == "falta_recibo":
                pendentes.append(row_dict)

        return pendentes

    finally:
        con.close()


def procurar_item(db_path, descricao_parcial: str) -> list:
    """
    Busca rapida de itens ja comprados por descricao.

    Ex: procurar_item(db, "redução") retorna todos os itens com "redução" no nome.
    """
    if isinstance(db_path, str):
        db_path = Path(db_path)

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    try:
        rows = con.execute("""
            SELECT
                ip.pfm_codigo,
                ip.descricao,
                ip.quantidade,
                ip.unidade,
                ip.valor_unitario,
                ip.valor_total,
                l.fornecedor,
                l.data_pagamento,
                l.valor as valor_pedido
            FROM itens_pedido ip
            JOIN lancamentos l ON ip.pfm_codigo = l.pfm_codigo
            WHERE LOWER(ip.descricao) LIKE ?
            ORDER BY l.data_pagamento DESC
        """, (f"%{descricao_parcial.lower()}%",)).fetchall()

        return [dict(row) for row in rows]

    finally:
        con.close()


def consolidado_para_prestacao_contas(db_path, ggv: str = None) -> dict:
    """
    Retorna dados estruturados para relatorio de prestacao de contas.

    Mostra cada pedido com: valor total, valor pago, documento fiscal, status.
    """
    if isinstance(db_path, str):
        db_path = Path(db_path)

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    try:
        query = """
            SELECT
                l.pfm_codigo,
                l.ggv,
                l.fornecedor,
                l.valor,
                l.status,
                l.categoria,
                COALESCE(SUM(p.valor), 0) as valor_pago,
                CASE
                    WHEN l.doc_id_nfe IS NOT NULL THEN 'nfe'
                    WHEN l.doc_id_recibo IS NOT NULL THEN 'recibo'
                    ELSE 'pendente'
                END as tipo_documento,
                CASE
                    WHEN l.doc_id_nfe IS NOT NULL THEN 'OK'
                    WHEN l.doc_id_recibo IS NOT NULL THEN 'assinado'
                    ELSE 'FALTA'
                END as status_documento
            FROM lancamentos l
            LEFT JOIN parcelas_pagamento p ON l.pfm_codigo = p.pfm_codigo
        """
        params = []

        if ggv:
            query += " WHERE l.ggv = ?"
            params.append(ggv)

        query += " GROUP BY l.pfm_codigo ORDER BY l.criado_em DESC"

        rows = con.execute(query, params).fetchall()

        return {
            "ggv": ggv or "todas",
            "gerado_em": datetime.now().isoformat(),
            "pedidos": [dict(row) for row in rows]
        }

    finally:
        con.close()


if __name__ == "__main__":
    # Teste rápido
    db = Path(__file__).parent.parent / "data" / "laura.db"

    print("=== TESTE DE VELOCIDADE ===\n")

    import time

    # Teste 1: obter pedido completo
    start = time.time()
    pedido = obter_pedido_completo(db, "GGV03-001")
    elapsed = (time.time() - start) * 1000
    print(f"[{elapsed:.1f}ms] obter_pedido_completo('GGV03-001')")
    if "erro" not in pedido:
        print(f"      Fornecedor: {pedido['fornecedor'].get('nome', 'N/A')}")
        print(f"      Valor: R$ {pedido['lancamento'].get('valor', 0):.2f}")
        print(f"      Parcelas: {len(pedido['parcelas'])}")

    # Teste 2: consolidado da obra
    start = time.time()
    cons = obter_consolidado_obra(db, "GGV03")
    elapsed = (time.time() - start) * 1000
    print(f"\n[{elapsed:.1f}ms] obter_consolidado_obra('GGV03')")
    print(f"      Total: {cons['total_pedidos']} pedidos, R$ {cons['total_valor']:.2f}")
    print(f"      Pago: R$ {cons['total_pago']:.2f} | Saldo: R$ {cons['saldo']:.2f}")

    # Teste 3: pendentes
    start = time.time()
    pend = listar_pedidos_pendentes(db, "GGV03")
    elapsed = (time.time() - start) * 1000
    print(f"\n[{elapsed:.1f}ms] listar_pedidos_pendentes('GGV03')")
    print(f"      Encontrados: {len(pend)} pedidos sem documento fiscal")

    # Teste 4: procurar item
    start = time.time()
    itens = procurar_item(db, "redução")
    elapsed = (time.time() - start) * 1000
    print(f"\n[{elapsed:.1f}ms] procurar_item('redução')")
    print(f"      Encontrados: {len(itens)} itens")
