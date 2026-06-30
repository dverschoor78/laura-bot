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


class CategoriaLancamento(str, Enum):
    MATERIAL = "material"
    MO       = "mo"
    SERVICOS = "servicos"
    TAXA     = "taxa"
    TERRENO  = "terreno"
    IMPOSTO  = "imposto"
    APORTE   = "aporte"
    VENDA    = "venda"
    COMISSAO = "comissao"

    def label(self):
        return {
            "material": "Material",
            "mo":       "Mão de obra",
            "servicos": "Serviços",
            "taxa":     "Taxa / Licença",
            "terreno":  "Terreno",
            "imposto":  "Imposto",
            "aporte":   "Aporte de capital",
            "venda":    "Venda",
            "comissao": "Comissão",
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
_RAMO_PARA_CATEGORIA = {
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
    "energia":              CategoriaLancamento.TAXA,
    "água":                 CategoriaLancamento.TAXA,
    "agua":                 CategoriaLancamento.TAXA,
    "distribui":            CategoriaLancamento.TAXA,
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


def vincular_nfe(pfm_codigo: str, doc_id_nfe: int, db_path: str) -> bool:
    """Vincula uma NF-e a um lançamento pago. Retorna True se o vínculo foi criado."""
    with sqlite3.connect(db_path) as con:
        cur = con.execute(
            "UPDATE lancamentos SET doc_id_nfe=? WHERE pfm_codigo=? AND status='pago' AND doc_id_nfe IS NULL",
            (doc_id_nfe, pfm_codigo)
        )
        return cur.rowcount == 1


def buscar_pedidos_sem_nfe(ggv: str, db_path: str) -> list:
    """Retorna lançamentos pagos sem NF-e vinculada para um GGV."""
    with sqlite3.connect(db_path) as con:
        return con.execute(
            """SELECT pfm_codigo, fornecedor, valor
               FROM lancamentos
               WHERE ggv=? AND status='pago' AND doc_id_nfe IS NULL
               ORDER BY pfm_codigo""",
            (ggv,)
        ).fetchall()


def buscar_candidatos_nfe(cnpj: str, valor: float, db_path: str) -> list:
    """Encontra pedidos pagos sem NF-e.

    Retorna todos os pedidos elegíveis, ordenados por score:
    - CNPJ coincide (+5), valor próximo (<1% +3, <5% +1)
    - Score=0 significa sem sinal forte mas ainda elegível (fallback manual)
    """
    with sqlite3.connect(db_path) as con:
        rows = con.execute(
            """SELECT l.pfm_codigo, l.fornecedor, l.valor, f.cnpj
               FROM lancamentos l
               LEFT JOIN fornecedores f ON LOWER(f.nome) = LOWER(l.fornecedor)
               WHERE l.status='pago' AND l.doc_id_nfe IS NULL""",
        ).fetchall()
    candidatos = []
    for pfm_codigo, fornecedor, valor_lanc, cnpj_forn in rows:
        score = 0
        if cnpj and cnpj_forn and cnpj.replace(".", "").replace("/", "").replace("-", "") == \
                cnpj_forn.replace(".", "").replace("/", "").replace("-", ""):
            score += 5
        if valor_lanc and valor:
            diff = abs(float(valor_lanc) - float(valor)) / max(float(valor), 0.01)
            if diff < 0.01:
                score += 3
            elif diff < 0.05:
                score += 1
        candidatos.append({"pfm_codigo": pfm_codigo, "fornecedor": fornecedor,
                            "valor_lanc": valor_lanc, "score": score})
    return sorted(candidatos, key=lambda x: x["score"], reverse=True)
