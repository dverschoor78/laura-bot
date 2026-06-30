# Roadmap do Projeto Laura

> Atualizado em: 2026-06-29

---

## Fase 5 — Módulo Financeiro

**Fiada 0 — Fundação** ✓ *(concluída 2026-06-30)*

- ADR-002: princípio "todo novo domínio nasce modular"
- `financeiro/lancamento.py`: enums, `sugerir_categoria()`, `init_db_financeiro()`
- `financeiro/conciliacao.py`: esqueleto (Fase 5d)
- `app/README.md`: elimina ambiguidade da pasta reservada
- `lancamentos`: novas colunas `categoria`, `tipo_documento`, `fonte_recurso`, `conciliado_em`

**Fiada 5a-1 — Categoria no Lançamento** *(próxima)*

- `sugerir_categoria()` integrada ao fluxo do PFM em bot.py
- Usuário vê categoria sugerida com botão de confirmação/correção antes de gravar
- Lançamento gravado inclui `categoria`

**Fiada 5b-1 — Extrato da Obra** *(planejada)*

- `financeiro/lancamento.py`: `extrato_obra()`, `totais_obra()`, `composicao_categorias()`
- Cockpit da obra exibe bloco financeiro ao digitar código de GGV

**Fiada 5c-1 — Lançamentos Manuais** *(planejada)*

- `financeiro/lancamento.py`: `criar_lancamento_manual()`
- Aportes, impostos e despesas avulsas sem PFM registráveis via Telegram

**Fiada 5d-1 — Conciliação Mensal** *(planejada)*

- `financeiro/conciliacao.py` completo
- Importação extrato Mercado Pago + matching automático + fechamento de período

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

**Fase 4b — Pedido de Compra 2.0** *(implementado — aguarda validação em produção)*

Design aprovado em 2026-06-30. Referência: `prints/pc_alternativa_a.html`

Implementado em 2026-06-30:
- `_PC_CSS` — CSS do documento como constante Python
- `_gerar_html_pc(doc_id)` — gera HTML com dados reais do banco
- `_html_para_pdf(html)` — converte para PDF via Playwright Chromium (async)
- Handler `pfm` envia PDF; DOCX continua gerado silenciosamente para o OneDrive
- PROMPT: 4 novos campos — Ramo de atividade, Número do orçamento, Vendedor, Telefone do vendedor
- `fornecedores.ramo` — coluna adicionada, salva automaticamente ao gerar PFM

Pendente:
- Validar layout do PDF com orçamento real
- Remover geração DOCX do fluxo principal após validação
- Data da negociação: ainda usa `criado_em` como proxy

**Fase 4c — Relatório de Compras por Obra** *(próxima)*

Extrato tipo cadastro acessível pelo cockpit da obra.
Mostra todos os PFMs de um GGV com status financeiro e totalizadores.

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
