# app/ — Reservado para ADR-003

Este diretório permanece reservado para uma futura modularização completa do sistema.

Quando essa decisão for tomada (ADR-003), os domínios hoje em `bot.py`
— Pedido de Compra, fornecedores, obras, integração Telegram —
serão migrados para aqui de forma incremental.

**Até essa decisão:**

Novos domínios devem nascer fora deste diretório, como módulos independentes no nível raiz do projeto.
O domínio Financeiro, por exemplo, nasce em `financeiro/` (ver ADR-002).

Não adicionar arquivos Python aqui antes da ADR-003.
