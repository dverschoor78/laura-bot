"""
Módulo Financeiro da Laura.

Domínio: tudo que representa movimentação de dinheiro nas obras.

Objetos e Relatórios:
  - Lançamento Financeiro (lancamento.py) → modelo, CRUD, ciclo de vida
  - Relatórios Financeiros (relatorios.py) → fluxos e consolidações
  - Consultas Rápidas (consultas.py) → acesso instantâneo a dados (2-3ms)
  - Conciliação Mensal + Período (conciliacao.py) → Fase 5d

Uso em bot.py:
  from financeiro.lancamento import init_db_financeiro, sugerir_categoria
  from financeiro.relatorios import gerar_fluxo_pagamentos_obra, gerar_relatorio_pagamentos
  from financeiro.consultas import obter_pedido_completo, obter_consolidado_obra

Uso no terminal (CLI):
  from pathlib import Path
  from financeiro.consultas import obter_pedido_completo, procurar_item, listar_pedidos_pendentes

  db = Path("data/laura.db")
  pedido = obter_pedido_completo(db, "GGV03-001")  # <2ms
  itens = procurar_item(db, "redução")              # <1ms
  pendentes = listar_pedidos_pendentes(db, "GGV03") # <1ms

Funções deste módulo recebem db_path como parâmetro explícito.
Nenhuma variável de ambiente é lida aqui.
"""
