# Estado do Projeto Laura

> Atualizado em: 2026-06-29
> Sessão: Sprint de Experiência — Fase 1 (Voz)

---

## Saúde do Projeto

🟢 Verde

- Fundação concluída.
- Ciclo financeiro completo: orçamento → PFM → A PAGAR → comprovante PIX → PAGO.
- Código estável.
- Nenhuma funcionalidade interrompida.
- Nenhuma implementação parcialmente concluída.
- Modo teste operacional e isolado de produção.

---

## Versão Atual

**v0.5.0** — Marcar como PAGO

---

## Funcionalidades Disponíveis

- Recebimento de foto e PDF via Telegram
- Seleção manual do tipo de documento antes da análise por IA
- Extração de dados por IA (Claude haiku-4-5) após tipo confirmado
- Edição de qualquer campo extraído antes de confirmar
- Seleção e correção manual de tipo e GGV
- Geração de PFM Word numerado (ex: GGV03-009)
- Salvamento automático do PFM na pasta OneDrive do GGV
- Criação de lançamento A PAGAR no banco
- Consulta de pedido digitando o código (ex: GGV03-009)
- Tela do pedido: dados financeiros, arquivos vinculados e histórico resumido
- Identificação de candidatos A PAGAR ao receber comprovante PIX
- Confirmação de pagamento com botões por candidato
- Marcação de lançamento como PAGO com gravação de valor, data e identificador
- Proteção contra duplo pagamento e reutilização do mesmo comprovante
- Modo teste isolado via `LAURA_ENV=test`

---

## Funcionalidades Iniciadas

- **Revisão da PFM** — botão existe, ação não implementada
- **Histórico do pedido** — botão existe, ação não implementada

---

## Última Fiada Implementada

**v0.5.0 — Marcar como PAGO**

- `teclado_candidatos_pix()`: um botão `💳 Confirmar` por candidato encontrado
- Tela de confirmação final exibe comprovante × lançamento antes de gravar
- `UPDATE lancamentos SET status='pago' WHERE pfm_codigo=? AND status='a_pagar'`
- Campos gravados: `valor_pago`, `data_pagamento`, `doc_id_comprovante`, `identificador_comprovante`
- `ID da transação` como campo dedicado no PROMPT e em `parse_comprovante()`
- Proteção em duas camadas: rowcount no UPDATE + verificação por `identificador_comprovante`
- Colunas adicionadas via `ALTER TABLE` seguro

---

## Em Andamento

Nada. Sprint de Produto encerrada limpa.

---

## Marcos do Produto

- **v0.1–0.3** — Fundação de engenharia: arquitetura, processo, documentação
- **v0.4–0.5** — Ciclo financeiro completo: orçamento → pedido → a pagar → pago
- **Sprint de Produto (2026-06-29)** — Identidade definida: quem a Laura é, o que ela promete, como ela fala

---

## Dívidas Técnicas Conhecidas

- `bot.py` monolítico com ~1705 linhas — aceitável até ~2000 linhas (ADR-001)
- BD fornecedores: MO Construção com CNPJ errado; PRUDENTÓPOLIS com split incorreto
- `pfm_caminho` não existe como coluna — path reconstruído a cada consulta
- `gerar_pfm()` acumula responsabilidades: geração Word + gravação no banco + criação de lançamento
- `mime_type` não gravado no banco — inferido pela extensão do arquivo
- Deduplicação de comprovante por `identificador_comprovante` não atua quando Claude
  não extrai o ID da transação (comprovante sem número visível)

---

## Decisões Recentes

- Tipo do documento é definido pelo usuário antes da IA — mais confiável e extensível
- `ID da transação` é a chave de deduplicação de comprovante, não o `obs` completo —
  mais curto e estável entre re-extrações do mesmo arquivo
- Proteção de pagamento em duas camadas: antes de listar candidatos + antes de gravar
- Modo teste implementado via variável de ambiente, não via comando Telegram — mais seguro

---

## Objetivo da Próxima Sessão

**Fase 2 — Estrutura** — reorganizar o conteúdo das telas principais: extração com
fornecedor e valor em destaque, tela de pedido criado com saldo do GGV, tela de
pagamento confirmado com saldo restante, erros com próximo passo sempre informado.

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
