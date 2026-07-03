#!/usr/bin/env python3
"""
CLI para consultar Laura pelo terminal.

Uso:
  python scripts/consultar.py GGV03-001          # Pedido completo
  python scripts/consultar.py --obra GGV03       # Consolidado da obra
  python scripts/consultar.py --item redução     # Procurar item
  python scripts/consultar.py --pendentes GGV03  # Pedidos sem doc fiscal
"""

import sys
import json
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from financeiro.consultas import (
    obter_pedido_completo,
    obter_consolidado_obra,
    procurar_item,
    listar_pedidos_pendentes,
    consolidado_para_prestacao_contas
)


def format_valor(v):
    """Formata valor em R$."""
    if v is None:
        return "---"
    return f"R$ {v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def pretty_pedido(pedido):
    """Exibe pedido de forma legível."""
    if "erro" in pedido:
        print(f"\n[ERRO] {pedido['erro']}\n")
        return

    l = pedido["lancamento"]
    f = pedido["fornecedor"]
    docs = pedido["documentos"]

    print(f"\n{'='*80}")
    print(f"  PEDIDO #{l['pfm_codigo']:20} {l['fornecedor']:30} {format_valor(l['valor'])}")
    print(f"{'='*80}")

    # Status
    status_icon = {
        "pago": "[OK]",
        "a_pagar": "[..] ",
        "pago_com_recibo": "[REC]",
    }.get(l["status"], "[?]")
    print(f"\n  Status: {status_icon} {l['status'].upper()}")
    print(f"  Categoria: {l.get('categoria', 'N/A')}")
    print(f"  Data pagamento: {l['data_pagamento'] or 'Pendente'}")

    # Fornecedor
    if f:
        print(f"\n  Fornecedor:")
        print(f"    Nome: {f.get('nome')}")
        print(f"    CNPJ/CPF: {f.get('cnpj') or f.get('cpf') or '---'}")
        print(f"    PIX: {f.get('chave_pix') or '---'}")
        if f.get('emite_nf') == 1:
            print(f"    Emite NF-e: SIM")
        else:
            print(f"    Emite NF-e: NAO (gera recibo)")

    # Parcelas
    if pedido["parcelas"]:
        print(f"\n  Parcelas ({len(pedido['parcelas'])}):")
        total_pago = 0
        for p in pedido["parcelas"]:
            status_parcela = {
                "pago": "[OK]",
                "aguardando_assinatura": "[..] ",
                "assinado": "[SIM]",
            }.get(p["status"], "[?]")
            print(f"    {status_parcela} Parcela #{p['id']:2} {format_valor(p['valor']):15} {p['data_pagamento'] or 'N/A':12} ({p['status']})")
            total_pago += p["valor"] or 0
        print(f"    {'-'*60}")
        print(f"    TOTAL PAGO: {format_valor(total_pago)}")

    # Itens
    if pedido["itens"]:
        print(f"\n  Itens ({len(pedido['itens'])}):")
        for item in pedido["itens"]:
            print(f"    • {item['descricao']:50} {item['quantidade']} {item['unidade']:6} @ {format_valor(item['valor_unitario']):12}")

    # Documentos
    if docs:
        print(f"\n  Documentos:")
        for tipo, doc in docs.items():
            print(f"    • [{tipo.upper():8}] {doc['nome']:40} ({doc['criado_em'][:10]})")
    else:
        print(f"\n  Documentos: NENHUM ANEXADO")

    print(f"\n{'='*80}\n")


def pretty_consolidado(cons):
    """Exibe consolidado de forma legível."""
    print(f"\n{'='*80}")
    print(f"  OBRA {cons['ggv']:50} CONSOLIDADO")
    print(f"{'='*80}")

    print(f"\n  Resumo Financeiro:")
    print(f"    Total de pedidos:     {cons['total_pedidos']:5} pedidos")
    print(f"    Valor total:          {format_valor(cons['total_valor']):>20}")
    print(f"    Valor pago:           {format_valor(cons['total_pago']):>20}")
    print(f"    Saldo em aberto:      {format_valor(cons['saldo']):>20}")
    print(f"    Pedidos pagos:        {cons['pedidos_pagos']:5}")
    print(f"    Pedidos em aberto:    {cons['pedidos_abertos']:5}")

    if cons['por_status']:
        print(f"\n  Por Status:")
        for row in cons['por_status']:
            print(f"    {row['status']:20} {row['qtd']:5} pedidos {format_valor(row['valor']):>15}")

    print(f"\n{'='*80}\n")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    db = Path(__file__).parent.parent / "data" / "laura.db"

    if not db.exists():
        print(f"\n[ERRO] Banco nao encontrado: {db}\n")
        sys.exit(1)

    # Parse argumentos
    if sys.argv[1] == "--obra" and len(sys.argv) > 2:
        cons = obter_consolidado_obra(db, sys.argv[2])
        pretty_consolidado(cons)

    elif sys.argv[1] == "--item" and len(sys.argv) > 2:
        termo = " ".join(sys.argv[2:])
        itens = procurar_item(db, termo)
        if not itens:
            print(f"\n[OK] Nenhum item encontrado com '{termo}'\n")
        else:
            print(f"\n[OK] {len(itens)} item(ns) encontrado(s):\n")
            for item in itens:
                print(f"  {item['pfm_codigo']:15} {item['fornecedor']:30} {item['descricao']:40} {format_valor(item['valor_total'])}")
            print()

    elif sys.argv[1] == "--pendentes" and len(sys.argv) > 2:
        pend = listar_pedidos_pendentes(db, sys.argv[2])
        if not pend:
            print(f"\n[OK] Nenhum pedido pendente de documento fiscal em {sys.argv[2]}\n")
        else:
            print(f"\n[ATENCAO] {len(pend)} pedido(s) sem documento fiscal:\n")
            for p in pend:
                print(f"  {p['pfm_codigo']:15} {p['fornecedor']:30} {format_valor(p['valor']):>15} (pago: {format_valor(p['valor_pago'])})")
            print()

    else:
        # Default: obter pedido completo
        pfm_codigo = sys.argv[1].upper()
        pedido = obter_pedido_completo(db, pfm_codigo)
        pretty_pedido(pedido)


if __name__ == "__main__":
    main()
