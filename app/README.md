# app/ — Reservado para modularização completa do bot.py

A ADR-003 (2026-06-30) avaliou extrair o domínio Entrega de `bot.py` para fora
deste diretório, seguindo o padrão de `financeiro/`, e **decidiu adiar** —
o domínio entrega ainda não está independente o suficiente (dados amarrados
a `lancamentos` e `documentos`, modelo de dados ainda mudando). Ver
`docs/decisoes/ADR-003-extracao-entrega-adiada.md` para o plano de extração
pronto e o gatilho de revisão.

Este diretório permanece reservado para uma futura modularização completa do sistema.

Quando essa decisão for retomada e aprovada, os domínios hoje em `bot.py`
— Pedido de Compra, entrega, fornecedores, obras, integração Telegram —
serão migrados para aqui de forma incremental.

**Até essa decisão:**

Novos domínios nascem fora deste diretório, como módulos independentes no nível raiz do projeto.
O domínio Financeiro, por exemplo, nasce em `financeiro/` (ver ADR-002).

Não adicionar arquivos Python aqui antes de uma ADR aprovando a migração.
