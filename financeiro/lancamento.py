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
    ]
    with sqlite3.connect(db_path) as con:
        for col in novas_colunas:
            try:
                con.execute(f"ALTER TABLE lancamentos ADD COLUMN {col}")
            except Exception:
                pass
