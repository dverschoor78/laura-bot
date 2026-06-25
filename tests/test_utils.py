"""
test_utils.py — Testes das funções utilitárias.

Estes são os primeiros testes do projeto — simples, sem dependências externas.
Execute com: pytest tests/test_utils.py -v
"""

import pytest
from app.utils.formatters import formatar_moeda, formatar_cnpj, formatar_data, limpar_cnpj
from app.utils.hasher import sha256_bytes
from app.extractors.schemas import ItemOrcamento, OrcamentoExtraido


class TestFormatadores:
    def test_moeda_valor_normal(self):
        assert formatar_moeda(4904.69) == "R$ 4.904,69"

    def test_moeda_valor_zero(self):
        assert formatar_moeda(0) == "R$ 0,00"

    def test_moeda_valor_nulo(self):
        assert formatar_moeda(None) == "R$ —"

    def test_cnpj_formatado(self):
        assert formatar_cnpj("77488385000889") == "77.488.385/0008-89"

    def test_cpf_formatado(self):
        assert formatar_cnpj("51847906915") == "518.479.069-15"

    def test_cnpj_nulo(self):
        assert formatar_cnpj(None) == "—"

    def test_data_iso_para_br(self):
        assert formatar_data("2026-07-23") == "23/07/2026"

    def test_data_nula(self):
        assert formatar_data(None) == "—"

    def test_limpar_cnpj(self):
        assert limpar_cnpj("77.488.385/0008-89") == "77488385000889"
        assert limpar_cnpj("518.479.069-15") == "51847906915"
        assert limpar_cnpj(None) == ""


class TestHasher:
    def test_hash_consistente(self):
        dados = b"conteudo de teste"
        assert sha256_bytes(dados) == sha256_bytes(dados)

    def test_hash_diferente_para_conteudos_diferentes(self):
        assert sha256_bytes(b"a") != sha256_bytes(b"b")

    def test_hash_formato(self):
        h = sha256_bytes(b"teste")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestSchemas:
    def test_item_valor_string_br(self):
        """Claude pode retornar 'R$ 4.904,69' — deve converter para float."""
        item = ItemOrcamento(descricao="Aço", valor_total="R$ 4.904,69")
        assert item.valor_total == pytest.approx(4904.69)

    def test_item_valor_numerico(self):
        item = ItemOrcamento(descricao="Tijolo", valor_total=6400.0)
        assert item.valor_total == 6400.0

    def test_orcamento_cnpj_limpo(self):
        orc = OrcamentoExtraido(cnpj="77.488.385/0008-89")
        assert orc.cnpj == "77488385000889"

    def test_orcamento_campos_opcionais_nulos(self):
        orc = OrcamentoExtraido()
        assert orc.fornecedor is None
        assert orc.valor_total is None
        assert orc.itens == []
