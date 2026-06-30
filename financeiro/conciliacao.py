"""
Domínio: Conciliação Mensal

Este módulo é o dono do processo de Conciliação e do objeto Período.

Conciliação: confronto entre o extrato bancário (Mercado Pago) e os
lançamentos registrados na Laura. Identifica correspondências automáticas
e apresenta apenas as divergências para confirmação do usuário.

Período: um mês/ano de uma conta bancária que passou pela conciliação
e foi fechado. Lançamentos de um período fechado não podem ser alterados.

Fluxo (Fase 5d):
  1. Usuário envia extrato Mercado Pago (CSV ou XLSX) via Telegram
  2. processar_extrato_mp() parseia o arquivo
  3. identificar_correspondencias() cruza com lançamentos PAGO do período
  4. divergencias_periodo() retorna apenas o que não casou
  5. Usuário confirma as divergências uma a uma
  6. fechar_periodo() marca o mês como fechado e lançamentos como CONCILIADO

Funções deste módulo recebem db_path como parâmetro explícito.
Nenhuma variável de ambiente é lida aqui.

Implementação: Fase 5d.
"""
