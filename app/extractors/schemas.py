"""
schemas.py — Modelos Pydantic para validar dados extraídos pelo Claude.

Por que Pydantic?
Se o Claude retornar um campo com tipo errado (ex: valor como string "R$ 4.904,69"
em vez de float 4904.69), o Pydantic captura o erro antes de chegar ao banco.
Evita bugs silenciosos com dados financeiros.
"""

from typing import Optional
from pydantic import BaseModel, field_validator
import re


class ItemOrcamento(BaseModel):
    """Um item da tabela do orçamento."""
    ordem: Optional[int] = None
    descricao: str
    unidade: Optional[str] = None
    quantidade: Optional[float] = None
    valor_unitario: Optional[float] = None
    valor_total: Optional[float] = None

    @field_validator("valor_unitario", "valor_total", "quantidade", mode="before")
    @classmethod
    def limpar_numero(cls, v):
        """Converte string de número brasileiro para float."""
        if v is None or v == "":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        # Remove R$, pontos de milhar, converte vírgula decimal
        v = str(v).strip()
        v = re.sub(r"[R$\s]", "", v)
        v = v.replace(".", "").replace(",", ".")
        try:
            return float(v)
        except ValueError:
            return None


class OrcamentoExtraido(BaseModel):
    """Dados extraídos de um orçamento/cotação."""
    tipo: str = "orcamento"
    fornecedor: Optional[str] = None
    cnpj: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    condicao_pagamento: Optional[str] = None
    prazo_entrega: Optional[str] = None
    itens: list[ItemOrcamento] = []
    valor_total: Optional[float] = None
    observacoes: Optional[str] = None

    @field_validator("cnpj", mode="before")
    @classmethod
    def limpar_cnpj(cls, v):
        """Remove formatação do CNPJ, mantém só dígitos."""
        if not v:
            return None
        return re.sub(r"\D", "", str(v))

    @field_validator("valor_total", mode="before")
    @classmethod
    def limpar_valor(cls, v):
        """Mesmo tratamento de ItemOrcamento."""
        return ItemOrcamento.limpar_numero(v)


class ComprovanteExtraido(BaseModel):
    """Dados extraídos de um comprovante PIX."""
    tipo: str = "comprovante"
    data_pagamento: Optional[str] = None   # formato: YYYY-MM-DD
    valor: Optional[float] = None
    nome_destino: Optional[str] = None
    cnpj_destino: Optional[str] = None
    chave_pix: Optional[str] = None
    id_transacao: Optional[str] = None

    @field_validator("valor", mode="before")
    @classmethod
    def limpar_valor(cls, v):
        return ItemOrcamento.limpar_numero(v)

    @field_validator("cnpj_destino", mode="before")
    @classmethod
    def limpar_cnpj(cls, v):
        if not v:
            return None
        return re.sub(r"\D", "", str(v))
