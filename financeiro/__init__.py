"""
Módulo Financeiro da Laura.

Domínio: tudo que representa movimentação de dinheiro nas obras.

Objetos e Relatórios:
  - Lançamento Financeiro (lancamento.py) → modelo, CRUD, ciclo de vida
  - Relatórios Financeiros (relatorios.py) → fluxos e consolidações
  - Conciliação Mensal + Período (conciliacao.py) → Fase 5d

Uso em bot.py:
  from financeiro.lancamento import init_db_financeiro, sugerir_categoria
  from financeiro.relatorios import gerar_fluxo_pagamentos_obra, gerar_relatorio_pagamentos

Funções deste módulo recebem db_path como parâmetro explícito.
Nenhuma variável de ambiente é lida aqui.
"""
