# Estado do Projeto Laura

> Atualizado em: 2026-06-29
> Sessão: Engenharia de desenvolvimento — Laura Engineering v1.0 ✅

---

## Saúde do Projeto

🟢 Verde

- Fundação concluída.
- Código estável.
- Nenhuma funcionalidade interrompida.
- Nenhuma implementação parcialmente concluída.
- Engenharia de desenvolvimento concluída.
- Pronto para iniciar a próxima fase de produto.

---

## Versão Atual

**v0.3.0** — Consulta de pedido por código via texto livre

---

## Funcionalidades Disponíveis

- Recebimento de foto e PDF via Telegram
- Extração de dados por IA (Claude haiku-4-5)
- Edição de qualquer campo extraído antes de confirmar
- Seleção e correção manual de tipo e GGV
- Geração de PFM Word numerado (ex: GGV03-009)
- Salvamento automático do PFM na pasta OneDrive do GGV
- Criação de lançamento A PAGAR no banco
- Consulta de pedido digitando o código (ex: GGV03-009)
- Tela do pedido: dados financeiros, arquivos vinculados e histórico resumido

---

## Funcionalidades Iniciadas

- **Revisão da PFM** — botão existe, ação não implementada
- **Histórico do pedido** — botão existe, ação não implementada

---

## Última Fiada Implementada

**v0.3.0 — Abrir pedido via texto livre**

- Detecção do código por regex (`PFM_CODIGO_RE`) sem chamada à IA
- Objeto de domínio `Pedido` com `StatusPedido(Enum)` e 17 campos tipados
- Pipeline de três funções com responsabilidade única: `buscar_pedido()`,
  `preparar_visualizacao_pedido()`, `mostrar_pedido()`

---

## Em Andamento

Nada. A versão v0.3.0 foi encerrada limpa.

---

## Dívidas Técnicas Conhecidas

- `bot.py` monolítico com 1418 linhas — aceitável até ~2000 linhas (ADR-001)
- BD fornecedores: MO Construção com CNPJ errado; PRUDENTÓPOLIS com split incorreto
- `pfm_caminho` não existe como coluna — path reconstruído a cada consulta
- `gerar_pfm()` acumula responsabilidades: geração Word + gravação no banco + criação de lançamento

---

## Decisões Recentes

- `Pedido` passou a ser o objeto central do domínio (v0.3.0)
- Consulta por código explícito não usa IA — detecção via regex é suficiente
- Monolito em `bot.py` mantido intencionalmente — ver `docs/decisoes/ADR-001`

---

## Objetivo da Próxima Sessão

Retorno ao desenvolvimento de produto.

Próxima fiada:

**Marcar como PAGO** — fechar o ciclo financeiro completo.
Ao receber um comprovante PIX, o bot vincula ao lançamento correto e atualiza
o status para PAGO.

---

## Referência de Arquitetura

Arquitetura detalhada:
→ `docs/ARQUITETURA.md`

---

## Documentos Recomendados

- `docs/PROCESSO.md` — como conduzir uma sessão de desenvolvimento
- `docs/ROADMAP.md` — próximas fiadas e dívida técnica
- `CHANGELOG.md` — histórico completo de fiadas
- `docs/ARQUITETURA.md` — estrutura técnica atual

---

*Última atualização: 2026-06-29*
*Responsáveis: Dennis + Claude*
*Próxima revisão: ao final da próxima sessão*
