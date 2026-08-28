"""
Domínio: Lançamento Financeiro

Este módulo é o dono do objeto Lançamento Financeiro:
modelo, enumeradores, ciclo de vida, CRUD, consultas e visões.

Ciclo de vida:
  A_PAGAR → PAGO → CONCILIADO

Origem:
  - Pedido de Compra aprovado (criado automaticamente por bot.py)
  - Entrada manual via Telegram (Fase 5c: aportes, impostos, avulsos)

Visões (Fase 5b):
  extrato_obra(), totais_obra(), composicao_categorias(), fluxo_caixa_mensal()
"""
import sqlite3
from enum import Enum
from typing import Optional


class CategoriaLancamento(str, Enum):
    MATERIAL        = "material"
    MO              = "mo"
    SERVICOS        = "servicos"           # serviços privados (gestão, engenharia, MO especializada) — exigem NF-e
    SERVICO_PUBLICO = "servico_publico"    # concessionárias (Copel, Sanepar) — a fatura é o fechamento fiscal
    TAXA            = "taxa"
    TERRENO         = "terreno"
    IMPOSTO         = "imposto"
    APORTE          = "aporte"
    VENDA           = "venda"
    COMISSAO        = "comissao"

    def label(self):
        return {
            "material":        "Material",
            "mo":              "Mão de obra",
            "servicos":        "Serviços",
            "servico_publico": "Serviço público",
            "taxa":            "Taxa / Licença",
            "terreno":         "Terreno",
            "imposto":         "Imposto",
            "aporte":          "Aporte de capital",
            "venda":           "Venda",
            "comissao":        "Comissão",
        }[self.value]


class StatusLancamento(str, Enum):
    A_PAGAR          = "a_pagar"
    PAGO             = "pago"
    CONCILIADO       = "conciliado"
    PENDENTE_REVISAO = "pendente_revisao"
    SUBSTITUIDO      = "substituido"


class TipoDocumento(str, Enum):
    NOTA   = "nota"
    RECIBO = "recibo"
    FATURA = "fatura"
    GUIA   = "guia"
    DARF   = "darf"
    BOLETO = "boleto"
    CONTA  = "conta"
    VIA    = "via"


# Mapeamento ramo do fornecedor → categoria sugerida.
# Chaves em minúsculas; comparação via substring (chave in ramo.lower()).
# A ORDEM IMPORTA: a primeira chave que casar vence. Serviço público vem antes de
# material porque "Distribuição de Energia Elétrica" (Copel) contém "eletric" — sem a
# precedência, a fatura de energia era sugerida como Material (caso real, 2026-07-08).
_RAMO_PARA_CATEGORIA = {
    "energia":              CategoriaLancamento.SERVICO_PUBLICO,
    "água":                 CategoriaLancamento.SERVICO_PUBLICO,
    "agua":                 CategoriaLancamento.SERVICO_PUBLICO,
    "saneamento":           CategoriaLancamento.SERVICO_PUBLICO,
    "distribui":            CategoriaLancamento.SERVICO_PUBLICO,
    "material":             CategoriaLancamento.MATERIAL,
    "materiais":            CategoriaLancamento.MATERIAL,
    "ferro":                CategoriaLancamento.MATERIAL,
    "aço":                  CategoriaLancamento.MATERIAL,
    "aco":                  CategoriaLancamento.MATERIAL,
    "elétric":              CategoriaLancamento.MATERIAL,
    "eletric":              CategoriaLancamento.MATERIAL,
    "hidráulic":            CategoriaLancamento.MATERIAL,
    "hidraulic":            CategoriaLancamento.MATERIAL,
    "madeira":              CategoriaLancamento.MATERIAL,
    "vidros":               CategoriaLancamento.MATERIAL,
    "telhas":               CategoriaLancamento.MATERIAL,
    "areia":                CategoriaLancamento.MATERIAL,
    "argamassa":            CategoriaLancamento.MATERIAL,
    "cimento":              CategoriaLancamento.MATERIAL,
    "mão de obra":          CategoriaLancamento.MO,
    "mao de obra":          CategoriaLancamento.MO,
    "pedreiro":             CategoriaLancamento.MO,
    "construção civil":     CategoriaLancamento.MO,
    "construcao civil":     CategoriaLancamento.MO,
    "serviços":             CategoriaLancamento.SERVICOS,
    "servicos":             CategoriaLancamento.SERVICOS,
    "gestão":               CategoriaLancamento.SERVICOS,
    "gestao":               CategoriaLancamento.SERVICOS,
    "engenharia":           CategoriaLancamento.SERVICOS,
    "arquitetura":          CategoriaLancamento.SERVICOS,
    "contabilidade":        CategoriaLancamento.SERVICOS,
    "contábil":             CategoriaLancamento.SERVICOS,
    "contabil":             CategoriaLancamento.SERVICOS,
    "calhas":               CategoriaLancamento.SERVICOS,
    "plotagem":             CategoriaLancamento.SERVICOS,
    "taxa":                 CategoriaLancamento.TAXA,
    "licença":              CategoriaLancamento.TAXA,
    "licenca":              CategoriaLancamento.TAXA,
}


def sugerir_categoria(ramo: str) -> CategoriaLancamento | None:
    """Sugere categoria a partir do ramo do fornecedor. Retorna None se não há sugestão."""
    if not ramo:
        return None
    ramo_lower = ramo.lower().strip()
    for chave, cat in _RAMO_PARA_CATEGORIA.items():
        if chave in ramo_lower:
            return cat
    return None


def init_db_financeiro(db_path):
    """Adiciona colunas financeiras à tabela lancamentos. Idempotente via try/except."""
    novas_colunas = [
        "categoria TEXT",
        "tipo_documento TEXT",
        "fonte_recurso TEXT",
        "conciliado_em TEXT",
        "doc_id_nfe INTEGER",
    ]
    with sqlite3.connect(db_path) as con:
        for col in novas_colunas:
            try:
                con.execute(f"ALTER TABLE lancamentos ADD COLUMN {col}")
            except Exception:
                pass


def init_db_notas_fiscais(db_path):
    """Tabela notas_fiscais_pedido — N NF-e por pedido (Caso 2 do ROADMAP Fase 6, identificado
    em 2026-06-30 e nunca implementado até bater na prática: GGV03-025/Operador Nacional do
    Registro, dois serviços de cartório de registro de imóveis, duas NF-e pro mesmo pedido).
    Fonte de verdade de quantas/quais notas um pedido tem; lancamentos.doc_id_nfe continua
    apontando pra primeira, só por compatibilidade com código que lê esse campo isoladamente
    (nunca a única fonte pra código novo). Backfill idempotente: todo pedido que já tinha
    doc_id_nfe no modelo antigo ganha a linha correspondente aqui."""
    with sqlite3.connect(db_path) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS notas_fiscais_pedido (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pfm_codigo  TEXT NOT NULL,
                doc_id      INTEGER NOT NULL,
                valor       REAL,
                numero      TEXT,
                criado_em   TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(pfm_codigo, doc_id)
            )
        """)
        con.execute("""
            INSERT OR IGNORE INTO notas_fiscais_pedido (pfm_codigo, doc_id)
            SELECT pfm_codigo, doc_id_nfe FROM lancamentos WHERE doc_id_nfe IS NOT NULL
        """)


def vincular_nfe(pfm_codigo: str, doc_id_nfe: int, db_path: str,
                  valor: Optional[float] = None, numero: Optional[str] = None) -> bool:
    """Vincula uma NF-e ao pedido — nunca substitui uma já vinculada, sempre acrescenta
    (Caso 2 do ROADMAP: um pedido pode ter mais de uma NF-e). Independente do status de
    pagamento — a nota pode ser emitida a qualquer momento. Retorna True se este doc_id
    passou a estar vinculado agora; False se já estava (mesmo arquivo reenviado)."""
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            "INSERT OR IGNORE INTO notas_fiscais_pedido (pfm_codigo, doc_id, valor, numero) "
            "VALUES (?,?,?,?)",
            (pfm_codigo, doc_id_nfe, valor, numero)
        )
        if cur.rowcount == 0:
            return False
        # Compatibilidade: lancamentos.doc_id_nfe guarda a primeira NF-e do pedido, pra
        # código que ainda lê esse campo isolado (ex: botão único do cockpit quando só há uma).
        con.execute(
            "UPDATE lancamentos SET doc_id_nfe=? WHERE pfm_codigo=? AND doc_id_nfe IS NULL",
            (doc_id_nfe, pfm_codigo)
        )
    return True


def trocar_nfe(pfm_codigo: str, novo_doc_id_nfe: int, db_path: str) -> Optional[int]:
    """Substitui a NF-e vinculada a um lançamento por outra — corrige um arquivo errado. Só
    faz sentido no caso comum (uma NF-e só); quando o pedido tem duas ou mais, a correção é
    por item na tela "Ver notas fiscais" (remover + reenviar). Retorna o doc_id da NF-e
    antiga (pra quem chamar poder limpar o arquivo/registro dela), ou None se o pedido não
    existe."""
    with sqlite3.connect(db_path) as con:
        row = con.execute("SELECT doc_id_nfe FROM lancamentos WHERE pfm_codigo=?", (pfm_codigo,)).fetchone()
        if row is None:
            return None
        doc_id_antigo = row[0]
        con.execute("UPDATE lancamentos SET doc_id_nfe=? WHERE pfm_codigo=?", (novo_doc_id_nfe, pfm_codigo))
        con.execute(
            "UPDATE notas_fiscais_pedido SET doc_id=?, valor=NULL, numero=NULL "
            "WHERE pfm_codigo=? AND doc_id=?",
            (novo_doc_id_nfe, pfm_codigo, doc_id_antigo)
        )
    return doc_id_antigo


def listar_notas_fiscais(pfm_codigo: str, db_path: str) -> list:
    """Todas as NF-e vinculadas a um pedido, mais antiga primeiro."""
    with sqlite3.connect(db_path) as con:
        return con.execute(
            "SELECT id, doc_id, valor, numero, criado_em FROM notas_fiscais_pedido "
            "WHERE pfm_codigo=? ORDER BY id",
            (pfm_codigo,)
        ).fetchall()


def remover_nota_fiscal(nfe_id: int, db_path: str) -> Optional[tuple]:
    """Desvincula uma NF-e específica do pedido — corrige um vínculo errado sem mexer nas
    outras notas do mesmo pedido. Se era a NF-e apontada por lancamentos.doc_id_nfe, promove
    a próxima (ou limpa, se não sobrar nenhuma). Retorna (pfm_codigo, doc_id) removidos, ou
    None se a NF-e não existia."""
    with sqlite3.connect(db_path) as con:
        row = con.execute(
            "SELECT pfm_codigo, doc_id FROM notas_fiscais_pedido WHERE id=?", (nfe_id,)
        ).fetchone()
        if not row:
            return None
        pfm_codigo, doc_id_removido = row
        con.execute("DELETE FROM notas_fiscais_pedido WHERE id=?", (nfe_id,))
        lanc = con.execute(
            "SELECT doc_id_nfe FROM lancamentos WHERE pfm_codigo=?", (pfm_codigo,)
        ).fetchone()
        if lanc and lanc[0] == doc_id_removido:
            proxima = con.execute(
                "SELECT doc_id FROM notas_fiscais_pedido WHERE pfm_codigo=? ORDER BY id LIMIT 1",
                (pfm_codigo,)
            ).fetchone()
            con.execute(
                "UPDATE lancamentos SET doc_id_nfe=? WHERE pfm_codigo=?",
                (proxima[0] if proxima else None, pfm_codigo)
            )
    return row


def soma_notas_fiscais(pfm_codigo: str, db_path: str) -> float:
    with sqlite3.connect(db_path) as con:
        row = con.execute(
            "SELECT COALESCE(SUM(valor),0) FROM notas_fiscais_pedido WHERE pfm_codigo=?", (pfm_codigo,)
        ).fetchone()
    return row[0] or 0.0


def buscar_pedidos_sem_nfe(ggv: str, db_path: str) -> list:
    """Retorna lançamentos sem NF-e vinculada para um GGV, qualquer status de pagamento."""
    with sqlite3.connect(db_path) as con:
        return con.execute(
            """SELECT pfm_codigo, fornecedor, valor
               FROM lancamentos
               WHERE ggv=? AND doc_id_nfe IS NULL
               ORDER BY pfm_codigo""",
            (ggv,)
        ).fetchall()


def buscar_candidatos_nfe(cnpj: str, valor: float, db_path: str) -> list:
    """Encontra pedidos ainda elegíveis a receber esta NF-e, qualquer status de pagamento — a
    nota pode ser emitida a qualquer momento, não só quando o pedido está totalmente pago.
    Elegível: sem nenhuma NF-e ainda, ou já com NF-e mas a soma delas não cobre o valor total
    do pedido (Caso 2 do ROADMAP — pedido com mais de uma NF-e, ex: GGV03-025/ONR).

    Retorna todos os pedidos elegíveis, ordenados por score:
    - CNPJ coincide (+5), valor próximo (<1% +3, <5% +1)
    - Score=0 significa sem sinal forte mas ainda elegível (fallback manual)
    - `valor_lanc` do candidato é o que falta cobrir (valor total, ou o restante quando já
      há NF-e parcial vinculada) — `parcial=True` sinaliza esse segundo caso pra exibição
    """
    with sqlite3.connect(db_path) as con:
        rows = con.execute(
            """SELECT l.pfm_codigo, l.fornecedor, l.valor, f.cnpj,
                      COALESCE((SELECT SUM(n.valor) FROM notas_fiscais_pedido n
                                WHERE n.pfm_codigo = l.pfm_codigo), 0) AS soma_nfe
               FROM lancamentos l
               LEFT JOIN fornecedores f ON LOWER(f.nome) = LOWER(l.fornecedor)
               WHERE l.doc_id_nfe IS NULL
                  OR l.valor IS NULL
                  OR (SELECT COALESCE(SUM(n.valor), 0) FROM notas_fiscais_pedido n
                      WHERE n.pfm_codigo = l.pfm_codigo) < l.valor - 0.01""",
        ).fetchall()
    candidatos = []
    for pfm_codigo, fornecedor, valor_lanc, cnpj_forn, soma_nfe in rows:
        parcial = bool(soma_nfe and soma_nfe > 0.009)
        valor_restante = (valor_lanc - soma_nfe) if (valor_lanc and parcial) else valor_lanc
        score = 0
        if cnpj and cnpj_forn and cnpj.replace(".", "").replace("/", "").replace("-", "") == \
                cnpj_forn.replace(".", "").replace("/", "").replace("-", ""):
            score += 5
        if valor_restante and valor:
            diff = abs(float(valor_restante) - float(valor)) / max(float(valor), 0.01)
            if diff < 0.01:
                score += 3
            elif diff < 0.05:
                score += 1
        candidatos.append({"pfm_codigo": pfm_codigo, "fornecedor": fornecedor,
                            "valor_lanc": valor_restante, "score": score, "parcial": parcial})
    # Desempate por proximidade de valor — dentro do mesmo score (ex: todos com score 0),
    # o valor mais perto do informado na NF-e vem primeiro, em vez de ordem arbitrária do banco
    def _distancia(c):
        if not (valor and c["valor_lanc"]):
            return 0
        return abs(float(c["valor_lanc"]) - float(valor))
    return sorted(candidatos, key=lambda x: (-x["score"], _distancia(x)))
