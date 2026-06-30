# Roadmap do Projeto Laura

> Atualizado em: 2026-06-30 (Fiada 6c++ concluída; ADR-003 registrada)

---

## Fase 5 — Módulo Financeiro

**Fiada 0 — Fundação** ✓ *(concluída 2026-06-30)*

- ADR-002: princípio "todo novo domínio nasce modular"
- `financeiro/lancamento.py`: enums, `sugerir_categoria()`, `init_db_financeiro()`
- `financeiro/conciliacao.py`: esqueleto (Fase 5d)
- `app/README.md`: elimina ambiguidade da pasta reservada
- `lancamentos`: novas colunas `categoria`, `tipo_documento`, `fonte_recurso`, `conciliado_em`

**Fiada 5a-1 — Categoria no Lançamento** ✓ *(concluída 2026-06-30)*

- `sugerir_categoria()` integrada ao fluxo do PFM em bot.py
- Tela de categoria antes de gerar o pedido: sugestão com confirmação ou grade de seleção
- Lançamento gravado inclui `categoria`; exibida na mensagem pós-PFM e na tela Financeiro

**Fiada 5b-1 — Extrato da Obra** *(adiada — depende do ciclo documental completo da Fase 6)*

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

## Fase 6 — Documentos de Fechamento

> Princípio: todo pagamento confirmado precisa de um documento fiscal vinculado — NF-e ou recibo. Sem exceção.

### Decisão de produto — 2026-06-30

**NF-e é obrigação, não opção.**

Todos os fornecedores devem emitir NF-e. O recibo é exceção restrita a casos onde
o fornecedor legalmente não pode emitir (autônomos informais, prestadores muito pequenos).

Motivação: **Regime Especial de Tributação (RET)** — exige que todos os custos da
incorporação tenham respaldo fiscal para apuração correta do tributo.

Exceções devem ser documentadas: qual fornecedor, qual pedido, por quê não tem NF.
Isso protege o RET em auditoria — não é descuido, é exceção registrada.

Fornecedores habituais sem NF (ex: Sabiá, MO Construção) devem ser marcados no
cadastro como `emite_nf = false` para Laura gerar recibo automaticamente, sem perguntar.

---

**Fiada 6a — Recebimento de NF-e** ✓ *(concluída 2026-06-30)*

- Novo tipo de documento `nota_fiscal`: extração de número, CNPJ, emitente, valor, data
- `buscar_candidatos_nfe()`: pedidos pagos sem NF-e; ordenado por CNPJ + valor próximo
- Vínculo `doc_id_nfe` em `lancamentos`; cockpit exibe número + botão de acesso
- Revisão do Pedido de Compra implementada: `pfm_revisar` → rev01, rev02...
- PROMPT de comprovante: prefere EndToEnd PIX (`E10573521...`) ao número MP

**Fiada 6b — Recibo como Exceção** *(planejada)*

- Recibo só é gerado quando fornecedor está marcado como `emite_nf = false` no cadastro
  OU quando usuário declara explicitamente que NF-e não será emitida
- Exceção registrada: motivo + pedido + fornecedor — rastreável para fins de RET
- Recibo gerado em PDF via Playwright: serviço (do orçamento) + pagamento (do PIX) + partes
- Status novo: `pago_com_recibo`
- Coluna `emite_nf BOOLEAN` adicionada à tabela `fornecedores`

**Fiada 6c — Foto de Entrega + Gestão de Entrega** ✓ *(concluída 2026-06-30)*

- Novo tipo de documento `foto_entrega` — sem Claude, direto à seleção do pedido
- 3 rotas: foto enviada, `/entrega`, botão `📦 Entregue` no cockpit
- Sugestões de observação (Jeito da Laura): completa, parcial, avaria, diferente, outra
- Qualquer pedido elegível, independente de status financeiro
- Colunas `obs_entrega`, `entregue_em` em `lancamentos`
- Gestão completa: `✏️ Editar entrega` → mudar obs, trocar/remover foto, apagar entrega
- `📎 Foto / Documento` na tela de obs para anexar antes de confirmar
- Tabela `entrega_fotos`: múltiplas fotos por pedido, cada uma com legenda obrigatória
- Galeria "👀 Ver arquivos" (ícone por tipo) + remoção individual por foto
- Navegação padronizada `← Voltar`/`✖ Fechar` em todos os menus
- **ADR-003 registrada:** extração do domínio entrega de `bot.py` avaliada e adiada — ver `docs/decisoes/ADR-003-extracao-entrega-adiada.md`

---

### Casos a tratar durante a implementação da Fase 6

Identificados em 2026-06-30 antes de iniciar qualquer fiada.
Cada um deve ser endereçado na fiada correspondente — não deixar para depois.

**1. Divergência de valor NF ≠ PIX**
Desconto negociado, frete separado ou arredondamento podem gerar diferença.
Laura deve alertar e permitir aceitar com observação ou bloquear o vínculo.

**2. Entregas parciais — múltiplas NF por pedido**
Um pedido pode ter três entregas e três NF-e diferentes.
O modelo atual é 1 pedido → 1 NF. Precisa suportar N NF por pedido antes de fechar o status.

**3. Fluxo inverso — entrega antes do PIX**
Material chega com crédito no fornecedor; NF-e chega antes do pagamento.
Laura precisa aceitar NF → aguardar PIX, além do fluxo padrão PIX → aguardar NF.

**4. Dados do prestador para o recibo**
O recibo precisa de CPF, nome completo e endereço do autônomo.
O cadastro de fornecedores tem CNPJ e nome comercial — incompleto para pessoa física.
Definir quais campos coletar no cadastro antes de gerar o primeiro recibo.

**5. Limitação fiscal do recibo gerado**
O recibo gerado por Laura tem valor como controle interno.
Para serviços com obrigação de NFS-e municipal (ISS acima de certo valor), pode não satisfazer
obrigação fiscal. Comunicar essa limitação ao usuário no momento da geração.

**6. Formatos de NF-e**
XML da SEFAZ (estruturado, preferencial), PDF do DANFE, foto do DANFE impresso.
Priorizar XML — mais rico e sem necessidade de OCR. Foto é fallback de última instância.

**7. Alerta proativo de NF pendente**
Laura monitora pedidos com status `pago` sem NF vinculada há N dias e alerta:
"GGV03-009 · Sabiá · pago há 7 dias sem nota fiscal."
Implementar junto com a Fiada 6b.

---

## Próximas Fiadas

1. **Usar entrega em produção real** — deixar o fluxo rodar no dia a dia antes de revisitar extração (gatilho na ADR-003)
2. Fiada 6b — Recibo como exceção (fornecedor sem NF-e, coluna `emite_nf` em `fornecedores`)
3. Validar PC 2.0 em produção + remover DOCX do fluxo principal
4. Corrigir BD fornecedores (MO Construção CNPJ, PRUDENTÓPOLIS split)

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

- **Média — `bot.py` monolítico com 3277 linhas**
  Acima do limite ADR-001 (2.500–3.000 linhas). Extração do domínio `entrega/` avaliada e
  **adiada por decisão** (ADR-003) — os dados de entrega ainda não são independentes
  (acoplados a `lancamentos` e `documentos`) e a feature tem zero horas de produção real.
  Gatilho de revisão explícito em `docs/decisoes/ADR-003-extracao-entrega-adiada.md`.

---

## Visão de Longo Prazo — Obra como Terceiro Objeto

*Registrado em 2026-06-30. Não implementar antes de existir motivo real.*

A Laura possui hoje dois objetos de domínio:
- **Pedido de Compra** — a decisão de comprar
- **Lançamento Financeiro** — o impacto financeiro dessa decisão

Naturalmente surgirá um terceiro: a **Obra** — não apenas como código identificador (GGV03),
mas como agregador de toda a informação de uma construção.

Uma Obra futura reunirá:
- Pedidos de Compra (já existem, vinculados por GGV)
- Lançamentos Financeiros (em construção)
- Documentos (plantas, contratos, alvarás)
- Cronograma físico
- Custos acumulados e projeção de término
- Indicadores de rentabilidade

Quando esse momento chegar, a separação já existirá nos domínios.
Bastará criar o objeto Obra como agregador — sem reescrever o que já funciona.

---

## Ideias Futuras

- Relatório mensal por GGV gerado e enviado automaticamente
- Exportação XLSX dos lançamentos por obra
- `/pendentes` com filtros por GGV e período
- Backup automático do banco via cron
- Sugestão automática de tipo de documento ("Sugerir automaticamente")
