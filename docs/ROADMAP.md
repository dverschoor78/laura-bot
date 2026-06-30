# Roadmap do Projeto Laura

> Atualizado em: 2026-06-29

---

## Em Andamento

**Fase 2 — Estrutura** *(Sprint de Experiência)*

Tela de validação do orçamento redesenhada com layout em 6 blocos orientado pela
sequência mental do engenheiro civil: Obra → Fornecedor → Itens → Valor → Condições → Logística.

Implementado nesta fase:
- `_resumo_gerar()` reescrita com layout aprovado e parse_mode HTML
- `teclado_orcamento()` unificado — condicionado ao estado da obra
- Campos `vencimento_pgto` e `encarregado` adicionados ao banco e à interface
- `GGV_ENCARREGADO` dict — padrão por obra, substituível por documento
- Botão "Conferir itens" removido — itens visíveis diretamente na tela de validação
- `DELTAD["ie"] = "Isento"` adicionado para uso no Pedido de Compra
- Botões Voltar em `sel_ggv`, `teclado_condicao`, `teclado_endereco`

Pendente nesta fase:
- Saldo do GGV na tela de pedido criado
- Saldo restante da obra na tela de pagamento confirmado
- Cartão do pedido com histórico resumido

---

## Fases Seguintes — Sprint de Experiência

**Fase 2 — Estrutura de mensagens**
- Tela de extração: fornecedor e valor em destaque na primeira linha
- Tela de pedido criado: incluir saldo atualizado do GGV
- Tela de pagamento confirmado: incluir saldo restante da obra
- Cartão do pedido: histórico resumido (criado em, pago em)
- Erros: sempre com próximo passo — nunca mensagens genéricas

**Fase 3 — Navegação e visões**
- Digitar "GGV03" → Cockpit da Obra (novo)
- Digitar nome de fornecedor → cartão do fornecedor (novo)
- /pendentes: lista por obra, vencidos destacados com ⚠️
- Tela de correção campo a campo (refatorado de "editar" para "corrigir")

**Fase 4a — Cadastro de Obras** ✓ *(concluída 2026-06-30)*

Tabela `obras` no banco com dados por GGV. Substitui dicts hardcoded no código.
- Tabela `obras` criada e pré-populada (GGV00–GGV03)
- `buscar_obra()` e `atualizar_obra()` e `criar_obra()`
- Cockpit da obra: digitar `GGV03` abre o card
- Edição campo a campo via teclado inline
- `/nova_obra` para cadastrar novas obras
- `/help` e handler de comando desconhecido
- Menu de comandos registrado no Telegram

**Fase 4b — Pedido de Compra 2.0**

Design aprovado em 2026-06-30. Referência: `prints/pc_alternativa_a.html`

Estrutura do documento (7 zonas):
1. Cabeçalho — Verschoor Investimentos Imobiliários + #GGV03-009 + data
2. Contexto — Origem (orçamento, WhatsApp, contatos) + Entrega (obra, data, encarregado)
3. Fornecedor — label "Fornecedor" + nome + ramo + CNPJ + cidade
4. Itens — numerados, descrição + qtde + valor unitário + total por item
5. Resumo financeiro — Subtotal / Desconto X,XX% / Total (destaque)
6. Condições — Pagamento (PIX, chave, vencimento) + Entrega (data, endereço)
7. Tagline — "Laura não é uma ferramenta que você usa. É uma memória que você carrega." — centralizada no fundo da página

Implementação pendente:
- Gerar HTML via template Python com dados reais
- Converter para PDF (WeasyPrint ou Playwright)
- PDF como output primário no Telegram
- Word removido do fluxo principal

**Pendências prioritárias do PC 2.0 — campos ainda ausentes:**

1. **Número do orçamento do fornecedor** — Claude não extrai hoje.
   Solução: adicionar "Número do orçamento:" ao PROMPT + campo `nr_orcamento_fornecedor` no banco.

2. **Data da negociação** — não capturada.
   Solução provisória: usar `documentos.criado_em` como "recebido em".
   Solução definitiva: campo editável pelo usuário no fluxo de confirmação.

3. **Contato do fornecedor** (nome + telefone para o bloco Origem) — existe em
   `fornecedores.contato` e `fornecedores.whatsapp` mas Claude não extrai do orçamento.
   Solução: adicionar "Contato:" e "Telefone:" ao PROMPT de extração de orçamento.

4. **Ramo do fornecedor** ("Comércio de Materiais de Construção") — não existe na tabela.
   Solução: adicionar campo `ramo` à tabela `fornecedores` + extração pelo Claude.

5. **Criar obra nova via Telegram** — hoje só pelo banco diretamente.
   Solução: fluxo `/nova_obra` com campos passo a passo.

---

## Próximas Fiadas

1. Revisão do Pedido de Compra — `pfm_revisar` (botão existe, ação pendente)
2. Histórico do Pedido — `pfm_hist` (botão existe, ação pendente)
3. Corrigir BD fornecedores (MO Construção CNPJ, PRUDENTÓPOLIS split)
4. `pfm_caminho` como coluna no banco — eliminar reconstrução de path

---

## Dívida Técnica

- **Baixa — Separar conceito de Obra do código GGV internamente**
  Decisão 2026-06-29: a mudança é de linguagem e domínio, não de migração imediata.
  Interface já usa "Obra GGV03"; banco mantém coluna `ggv` por compatibilidade.
  `pfm_codigo` (ex: GGV03-009), arquivos `.docx` e links existentes não serão alterados.
  Dívida futura: migrar domínio interno `ggv` → `obra_codigo` em fiada específica.

- **Alta — BD fornecedores inconsistente**
  MO Construção com CNPJ errado; PRUDENTÓPOLIS com split incorreto.
  Justificativa: dados incorretos afetam a busca de fornecedores em cada geração de PFM.

- **Média — `gerar_pfm()` acumula responsabilidades**
  Mistura geração Word, gravação no banco e criação de lançamento.
  Justificativa: dificulta testes e futuras extensões.

- **Média — `pfm_caminho` não existe como coluna**
  O caminho do arquivo é reconstruído a cada consulta.
  Justificativa: risco de inconsistência se a estrutura de pastas mudar.

- **Média — `mime_type` não gravado no banco**
  Inferido pela extensão do arquivo ao reprocessar.
  Justificativa: funciona para o MVP; pode falhar para arquivos sem extensão clara.

- **Baixa — deduplicação de comprovante incompleta**
  Se o Claude não extrair `ID da transação`, a proteção por identificador não atua.
  Justificativa: afeta apenas comprovantes sem número de transação visível; raro no MP.

- **Baixa — `bot.py` monolítico com ~1705 linhas**
  Aceitável até ~2000 linhas.
  Justificativa: monólito é decisão consciente — registrado na ADR-001.

---

## Ideias Futuras

- Conciliação com extrato Mercado Pago
- Relatório mensal por GGV
- Exportação XLSX dos lançamentos
- `/pendentes` com filtros por GGV e período
- Backup automático do banco via cron
- Sugestão automática de tipo de documento ("Sugerir automaticamente")
