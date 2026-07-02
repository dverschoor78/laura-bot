"""Gera um pedido de teste ponta-a-ponta (documento -> gerar_pfm -> PDF), em LAURA_ENV=test.
Nao toca no banco/pastas de producao. Uso: python scripts/teste_gerar_pedido.py
"""
import os
os.environ["LAURA_ENV"] = "test"

import sys
import asyncio
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bot

DADOS_TESTE = """**Fornecedor:** Materiais Teste LTDA

**Ramo de atividade:** Comercio de Materiais de Construcao

**Resumo da compra:** Cimento e areia para fundacao

**CNPJ/CPF:** 11.111.111/0001-11

Chave PIX: teste@materiaisteste.com.br

**Numero do orcamento:** 999999

**Vendedor:** Fulano de Tal

**Telefone do vendedor:** (42) 99999-0000

**Itens:**
1. Cimento CP-II 50kg (20,00 UND) - R$ 19,90 cada = R$ 398,00
2. Areia media m3 (2,00 M3) - R$ 63,11 cada = R$ 126,22

**Valor total:** R$ 524,22

**Desconto:** Nao informado

**Condicao de pagamento:** 50% na entrega, 50% em 30 dias

**Prazo de entrega:** 5 dias uteis

**Validade da proposta:** 15/07/2026

**Observacoes:** Pedido de teste gerado para validar fluxo sem DOCX.
"""


def preparar_documento_teste() -> int:
    bot.init_db()
    with sqlite3.connect(bot.DB_PATH) as con:
        con.execute("DELETE FROM documentos WHERE hash='teste-fluxo-sem-docx'")
        cur = con.execute(
            "INSERT INTO documentos (nome, caminho, hash, tipo, ggv, dados_claude, "
            "condicao_pgto, data_entrega, endereco_entrega, desconto_rs) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                "orcamento-teste.pdf", "data/test_uploads/orcamento-teste.pdf",
                "teste-fluxo-sem-docx", "orcamento", "GGV03", DADOS_TESTE,
                "50% na entrega, 50% em 30 dias", "2026-07-10",
                "Rua Teste, 123 - Carambei/PR", None,
            ),
        )
        return cur.lastrowid


async def main():
    doc_id = preparar_documento_teste()
    print(f"Documento de teste criado: doc_id={doc_id}")

    caminho, pfm_codigo, fornecedor, total_v, lanc_status, ja_existia = bot.gerar_pfm(doc_id)
    print(f"gerar_pfm() -> codigo={pfm_codigo} fornecedor={fornecedor} total={total_v} "
          f"lanc_status={lanc_status} ja_existia={ja_existia}")
    print(f"Caminho retornado: {caminho} (extensao: {caminho.suffix})")

    docx_irmao = caminho.with_suffix(".docx")
    print(f"Existe .docx correspondente? {docx_irmao.exists()} (esperado: False)")

    html = bot._gerar_html_pc(doc_id)
    pdf_bytes = await bot._html_para_pdf(html)
    caminho.write_bytes(pdf_bytes)
    print(f"PDF gravado em: {caminho} ({len(pdf_bytes)} bytes)")
    print(f"Comeca com %PDF? {pdf_bytes[:4] == b'%PDF'}")

    with sqlite3.connect(bot.DB_PATH) as con:
        itens = con.execute(
            "SELECT numero, descricao, unidade, quantidade, valor_unitario, valor_total "
            "FROM itens_pedido WHERE pfm_codigo=? ORDER BY numero", (pfm_codigo,)
        ).fetchall()
    print(f"Itens salvos em itens_pedido: {len(itens)}")
    for it in itens:
        print(f"  {it}")


if __name__ == "__main__":
    asyncio.run(main())
