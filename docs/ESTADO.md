# Estado do Projeto Laura

> Atualizado em: 2026-06-29
> Sessão: Modo teste + Comprovante PIX (identificação de candidatos)

---

## Saúde do Projeto

🟢 Verde

- Fundação concluída.
- Código estável.
- Nenhuma funcionalidade interrompida.
- Nenhuma implementação parcialmente concluída.
- Modo teste operacional e isolado de produção.

---

## Versão Atual

**v0.4.0** — Identificação de candidatos para comprovante PIX

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
- Modo teste isolado via `LAURA_ENV=test`

---

## Funcionalidades Iniciadas

- **Revisão da PFM** — botão existe, ação não implementada
- **Histórico do pedido** — botão existe, ação não implementada

---

## Última Fiada Implementada

**v0.4.0 — Identificação de candidatos para comprovante PIX**

Três fiadas entregues na mesma sessão:

1. **Modo teste** — `LAURA_ENV=test` seleciona banco, uploads e pasta de PFMs separados;
   hash com sufixo de timestamp permite reprocessar o mesmo arquivo em desenvolvimento
2. **Tipo manual antes da IA** — teclado de seleção de tipo exibido ao receber arquivo;
   Claude acionado somente após escolha explícita
3. **Candidatos PIX** — `parse_comprovante()`, `buscar_candidatos_pix()`,
   `mostrar_comprovante_candidatos()` — somente leitura, nenhum dado alterado

---

## Em Andamento

Nada. A versão v0.4.0 foi encerrada limpa.

---

## Dívidas Técnicas Conhecidas

- `bot.py` monolítico com ~1584 linhas — aceitável até ~2000 linhas (ADR-001)
- BD fornecedores: MO Construção com CNPJ errado; PRUDENTÓPOLIS com split incorreto
- `pfm_caminho` não existe como coluna — path reconstruído a cada consulta
- `gerar_pfm()` acumula responsabilidades: geração Word + gravação no banco + criação de lançamento

---

## Decisões Recentes

- Tipo do documento é definido pelo usuário antes da IA — mais confiável e extensível
- `mime_type` não foi gravado no banco (escopo contido); inferido pela extensão do arquivo
- Algoritmo de candidatos usa apenas primeiro token e CNPJ — sem biblioteca de fuzzy matching
- Modo teste implementado via variável de ambiente, não via comando Telegram — mais seguro

---

## Objetivo da Próxima Sessão

**Marcar como PAGO** — fechar o ciclo financeiro completo.

A base de candidatos está pronta (`buscar_candidatos_pix`). A próxima fiada adiciona
botões de confirmação ao resultado e grava `status='pago'` no lançamento escolhido.

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
