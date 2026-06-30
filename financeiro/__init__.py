"""
Módulo Financeiro da Laura.

Domínio: tudo que representa movimentação de dinheiro nas obras.

Objetos centrais:
  - Lançamento Financeiro (lancamento.py)
  - Conciliação Mensal + Período (conciliacao.py)

Uso em bot.py:
  from financeiro.lancamento import init_db_financeiro, sugerir_categoria
  from financeiro.conciliacao import ...  # Fase 5d

Funções deste módulo recebem db_path como parâmetro explícito.
Nenhuma variável de ambiente é lida aqui.
"""
