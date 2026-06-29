# CHANGELOG

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versionamento baseado em [Semantic Versioning](https://semver.org/).

---

## [Não lançado]

### Próximas fiadas (priorizadas)
1. Apresentação Profissional do Pedido — novo layout do Pedido de Compra, identidade visual moderna, geração automática de PDF
2. Revisão do Pedido de Compra — botão existe, ação pendente
3. Histórico do Pedido — botão existe, ação pendente
4. Corrigir BD fornecedores (MO Construção CNPJ errado, PRUDENTÓPOLIS split)
5. `pfm_caminho` como coluna no banco — eliminar reconstrução de path

---

## [0.5.0] — 2026-06-29

### Fiada — Marcar como PAGO

Ciclo financeiro completo: orçamento → PFM → A PAGAR → comprovante PIX → PAGO.

- Botões de candidato (`💳 Confirmar GGV03-001`) exibidos junto à lista de correspondências
- Tela de confirmação final mostra comprovante × lançamento lado a lado antes de gravar
- `lancamentos.status` atualizado para `pago` somente após confirmação explícita
- Campos gravados: `valor_pago`, `data_pagamento`, `doc_id_comprovante`, `identificador_comprovante`
- `ID da transação` extraído pelo Claude (número MP ou E2E Pix) — campo dedicado no PROMPT
- Proteção 1: `UPDATE WHERE pfm_codigo=? AND status='a_pagar'` + verificação de `rowcount`
  — bloqueia duplo clique ou status alterado entre telas
- Proteção 2: verifica `identificador_comprovante` antes de listar candidatos e antes de gravar
  — bloqueia reutilização do mesmo comprovante mesmo quando reenviado em sessão diferente
- Ao consultar o pedido, tela mostra `🟢 PAGO`
- Colunas adicionadas via `ALTER TABLE` seguro: `valor_pago`, `data_pagamento`,
  `doc_id_comprovante`, `identificador_comprovante`

**Limitação conhecida:** se o Claude não extrair o `ID da transação` do comprovante
(comprovante sem número de transação visível), a proteção por identificador não atua.
O pagamento ocorre normalmente, mas reenvio do mesmo arquivo não é detectado.

---

## [0.4.0] — 2026-06-29

### Fiada — Modo teste (`LAURA_ENV=test`)
- `LAURA_ENV=test` no `.env` ativa modo de desenvolvimento isolado
- Banco separado: `data/laura_test.db`
- Uploads separados: `data/test_uploads/`
- PFMs gerados em teste salvos em `data/test_pfms/` com prefixo `TESTE-`
- Hash com sufixo de timestamp em modo teste — permite reprocessar o mesmo arquivo
- `/start` exibe aviso completo: banco, uploads e pasta de PFMs ativos
- Aviso `🧪 MODO TESTE ATIVO` ao receber arquivo
- Produção (`data/laura.db`) não é tocada durante testes
- `.env.example` atualizado com `LAURA_ENV=test` comentado

### Fiada — Tipo do documento escolhido antes da IA
- Ao receber arquivo, bot pergunta o tipo antes de chamar Claude:
  📋 Orçamento / 💰 Comprovante PIX / 🏦 Extrato MP / 🗑 Outro
- Claude só é chamado após seleção explícita — evita extração com tipo errado
- Callback `sel_tipo_inicial` lê o arquivo do disco, infere mime pela extensão e aciona Claude
- Fluxo de orçamento preservado integralmente
- Comprovante PIX segue fluxo próprio, sem exibir "Revisar e gerar PFM"
- Botão de correção de tipo pós-extração mantido para ajustes

### Fiada — Identificar candidatos para comprovante PIX
- `parse_comprovante(dados_claude)`: extrai valor, data, favorecido, CNPJ, chave PIX,
  instituição financeira e identificador/observação do texto Claude
- `buscar_candidatos_pix(valor_v, favorecido, cnpj)`: pontua lançamentos `a_pagar`
  por valor exato (+3), valor ±10% (+1), CNPJ via BD fornecedores (+3),
  primeiro token do favorecido (+2) — retorna até 3 candidatos ordenados por score
- `mostrar_comprovante_candidatos(dados, candidatos)`: formata resultado para o Telegram
  com confiança Alta ✅ / Média 🟡 / Baixa 🔸
- PROMPT atualizado: "Destinatário" → "Favorecido", campos Instituição financeira e
  Identificador/Observação adicionados
- Nenhum dado financeiro alterado — fiada é somente leitura

---

## [0.3.0] — 2026-06-29

### Fiada — Abrir pedido via texto livre
- Digitar `GGV03-009` (ou qualquer texto contendo o código) abre o painel do pedido
- Detecção por regex (`PFM_CODIGO_RE`) — zero chamada à IA para código explícito
- `buscar_pedido(pfm_codigo)` parseia o código e consulta `documentos` + `lancamentos`
- `teclado_pedido()`: 5 botões — Revisar, Ver PFM, Lançamento, Histórico, Fechar
- `pfm_ver`: verifica existência do arquivo em disco antes de enviar (alerta se não encontrar)
- `pfm_lanc`: mostra detalhes do registro financeiro
- `pfm_revisar` e `pfm_hist`: placeholders para fiadas futuras
- `pfm_fechar`: encerra o painel

### Fiada — Tela do Pedido (objeto central)
- Nova tela rica com 5 seções separadas por `──────────────────────────────`
  1. Cabeçalho: status, fornecedor, CNPJ
  2. Financeiro: valor orçamento, desconto, valor negociado, condição pgto, vencimento
  3. Entrega: data prevista
  4. Arquivos vinculados: orçamento original + PFM.docx (se existirem em disco)
  5. Histórico resumido: data de recebimento + data de geração da PFM

### Fiada — Objeto de domínio `Pedido`
- `StatusPedido(str, Enum)`: centraliza os status possíveis — A_PAGAR, PAGO, PENDENTE_REVISAO, SUBSTITUIDO, SEM_LANCAMENTO
- `@dataclass Pedido`: 17 campos tipados — substitui dicionários `raw` e `vm`
- Pipeline de 3 funções com responsabilidade única:
  - `buscar_pedido()` — DB + cálculos financeiros → retorna `Pedido`
  - `preparar_visualizacao_pedido()` — filesystem (arquivos existem?) + histórico → enriquece `Pedido`
  - `mostrar_pedido()` — formatação pura → retorna `str`; sem IO
- Status lógico separado da apresentação: `Pedido.status = StatusPedido.A_PAGAR`; emojis/labels apenas em `mostrar_pedido()`
- `_fmt_data_curta()`: helper de formatação de data para o histórico

---

## [0.2.0] — 2026-06-28

### Fiada 13 — PFM salvo na pasta OneDrive correta
- `GGV_ONEDRIVE` dict mapeia cada GGV para sua pasta de destino no OneDrive
- PFMs do GGV03 salvos em `00 Obras/2026-06 GGV03/04 Aquisição e Execução/`
- Fallback para `data/pfms/` para GGVs sem mapeamento

### Fiada 14 — Edição de campos extraídos pela IA
- Botão "✏️ Editar campos" na tela de confirmação inicial
- Submenu com 11 campos editáveis: Fornecedor, CNPJ/CPF, Valor total, Chave PIX, Itens, Desconto, Condição pgto, Data entrega, Endereço, GGV, Tipo doc.
- Campos de texto exibem valor atual antes do prompt (permite copiar e colar)
- Itens: exibe bloco completo com instrução de formato
- GGV e Tipo: reutilizam os seletores já existentes; retornam à tela de revisão se já confirmado
- `_substituir_campo()` e `_substituir_itens()`: edição inline no `dados_claude` sem re-extração
- Botão ◀️ Voltar retorna à tela de revisão

### Desconto
- Claude extrai desconto automaticamente do documento (campo "Desconto" no PROMPT)
- Se informado em %, Claude converte para R$ usando o total do orçamento
- Usuário pode editar manualmente via botão 🏷️ Desconto no submenu
- PFM mostra 3 linhas de total quando desconto > 0: SUBTOTAL / DESCONTO (x.xx%) / TOTAL DO PEDIDO
- Valor gravado em coluna `desconto_rs TEXT` no banco

### Opção B — UX redesenhada (tela de revisão central)
- ✅ Confirmar vai direto para tela de revisão com todos os dados extraídos
- Tela de revisão mostra dados do Claude + bloco de resumo (💰/📅/📍/🏷️) + botões Gerar/Editar/Cancelar
- Condição de pgto, Data de entrega e Endereço são editados pelo submenu (não mais em fluxo sequencial obrigatório)
- Todas as edições retornam à tela de revisão
- `_resumo_gerar()`: função central que monta tela de revisão a partir do banco
- `_dados_display()`: filtra do texto do Claude os campos duplicados no bloco de resumo (Desconto, Condição de pagamento, Prazo de entrega)

### Melhorias e correções
- `max_tokens` 1024 → 4096: suporte a orçamentos com 37+ itens
- PROMPT: Chave PIX com dica para buscar em qualquer parte do documento
- PROMPT: "liste todos os itens" (removido limite de 10)
- PFM: "PRAZO / OBSERVAÇÃO" renomeado para "OBSERVAÇÃO"; prazo e obs mesclados sem duplicar
- `teclado_gerar()` substituiu `teclado_pfm()`: inclui botões Editar e Cancelar além de Gerar PFM
- `teclado_endereco()` sem parâmetro `pgto` (removido com Opção B)

### Housekeeping
- Dead code removido: variáveis não utilizadas no handler `edit_desconto` (emoji, label_tipo, label_ggv, dados_atuais, ggv_db)
- Bug corrigido: `float(desconto_atual)` → `_parse_brl()` para suportar vírgula decimal
- Defaults automáticos removidos: PIX à vista e endereço obra não são mais setados ao confirmar (eram inconsistentes)

---

## [0.1.1] — 2026-06-25

### Auditoria e refinamento

**Bug crítico corrigido — "cliente como fornecedor"**
- `buscar_fornecedor()`: ignora busca por CNPJ quando o CNPJ extraído pelo Claude pertence à própria DeltaD
- Claude às vezes extrai o CNPJ do "DADOS PARA FATURA" (DeltaD) em vez do fornecedor real
- Com o guard, cai direto na busca por nome, que encontra o fornecedor correto

**Bugs menores corrigidos**
- `_campo()`: `.strip("*").strip()` — asteriscos markdown podiam deixar espaço residual no valor
- `_obs()`: `lstrip("- *")` para limpar markdown bold, igual ao `_itens()`
- `CREATE TABLE documentos`: `data_entrega TEXT` ausente da definição inicial (existia só no ALTER TABLE)
- `gerar_pfm()`: guard `if row is None` antes de desempacotar — `ValueError` explícito em vez de `TypeError` genérico
- Mensagem pós-PFM: "Pronto para fiada 9." substituído por mensagem neutra

**Código morto removido**
- `_secao()`: função do layout v0.0.8 nunca chamada desde v0.1.0

**PROMPT**
- `[dados extraídos]` substituído por texto sem colchetes — consistente com a instrução "sem colchetes" do próprio PROMPT

---

## [0.1.0] — 2026-06-25

### Fiadas 11 + 12 — Layout PFM + Itens Estruturados + Data de Entrega

**Layout PFM (fiada 11)**
- Novo `gerar_pfm()` com python-docx tabelas: 5 tabelas (cabeçalho, fornecedor, empreendimento, materiais, prazo|dados)
- Cabeçalho: DeltaD Engenharia à esq + Nº PFM e data por extenso à dir
- FORNECEDOR: tabela label|valor — razão social, CNPJ, I.E., logradouro, bairro, e-mail, WhatsApp, PIX
- MATERIAIS: 6 colunas (ID, DESCRIÇÃO, UND, QTDE, R$ UNIT, R$ TOTAL) + linha TOTAL DO PEDIDO
- Parte inferior: PRAZO E CONDIÇÕES (esq) | DADOS PARA FATURA + DADOS PARA ENTREGA (dir)
- DADOS PARA FATURA: DeltaD/Verschoor hardcoded (CNPJ, endereço, e-mail)
- Validação de cidade: filtra dados inválidos do import (> 30 chars, '/', dígitos)
- `_campo()` estendido: reconhece "não informado", "n/a", "—" como A PREENCHER
- `_data_extenso()`: "Carambeí, 25 de junho de 2026."
- Constante DELTAD com dados fixos da empresa

**Itens estruturados (fiada 12)**
- ITEM_RE parseia `N. Descrição (QTDE UND) — R$ TOTAL` com regex lazy (lida com parênteses no nome)
- `_parse_brl()` / `_fmt_brl()`: conversão de valores BR
- `_itens()` retorna dicts `{desc, und, qtde, unit, total, _total_v}` quando parseia com sucesso
- R$ UNIT calculado automaticamente: total / qtde
- Total do pedido calculado a partir dos itens; fallback para extração Claude se não parsear
- Fix trigger `_itens()`: `re.match` em vez de `re.search` (evitava falso positivo em "Materiais" no nome do fornecedor)

**Data de entrega (fiada 12)**
- Novo passo no fluxo: após condição de pagamento, bot pergunta data de entrega
- Entrada texto livre (ex: "07/08/2026", "7 dias úteis", "A combinar")
- Coluna `data_entrega` adicionada à tabela documentos (ALTER TABLE seguro)
- Aparece no documento após PIX, antes de DADOS PARA ENTREGA
- PRAZO Claude mantido separado se diferente da data acordada

**PROMPT atualizado**
- Itens: formato explícito `N. Descrição (QTDE UND) — R$ TOTAL`
- Campos separados: "Prazo de entrega" ≠ "Validade da proposta"

---

## [0.0.9] — 2026-06-25

### Fiada 9 (import) + Bug fix + Fiada 10 (BD fornecedores no bot)

**Bug corrigido — tipo com colchetes (regressão v0.0.8)**
- Claude retornava `TIPO:[orcamento]` (com colchetes literais)
- `parse_resposta` preservava os colchetes → `if tipo == "orcamento"` falhava
- Bot caía no else e imprimia "Confirmado" sem entrar no fluxo de PFM
- Corrigido: `.strip("[]").split("|")[0]` em tipo e ggv no parser
- PROMPT reformatado para evitar ambiguidade dos colchetes

**Fiada 9 — import_fornecedores.py**
- Script avulso que varreu 69 PFMs do GGV01
- Extraiu 28 fornecedores únicos via lxml XML (campos em text boxes)
- Tabela `fornecedores` criada em `data/laura.db`

**Fiada 10 — BD fornecedores integrado ao bot**
- `init_db()` cria tabela `fornecedores` (deploy limpo não precisa mais do script)
- `buscar_fornecedor(nome)`: fuzzy search por primeiro token, case-insensitive
- `gerar_pfm()` usa dados do BD (razão social, CNPJ, PIX, endereço) quando encontra o fornecedor
- Fallback para dados extraídos pelo Claude se fornecedor não estiver no BD

---

## [0.0.8] — 2026-06-25

### Fiada 7+8 — Correção do fluxo + Geração do PFM Word (consolidado)
- Corrigido bug: `query.answer()` duplo quebrava o handler de pagamento (pgto)
  → Alerta de GGV ausente agora retorna antes do `query.answer()` padrão
- Removido `parse_mode="Markdown"` das mensagens intermediárias (eliminada fonte de erros silenciosos)
- Adicionado `try/except` global no handler de botões com mensagem de erro visível
- Gerar PFM: botão "📄 Gerar PFM" aparece ao concluir coleta de dados
- Função `gerar_pfm()` com python-docx: título, nº/data, fornecedor, empreendimento, itens, valor, pagamento, entrega, observações, assinatura
- Numeração automática por GGV: GGV03-001, GGV03-002... (MAX+1 no SQLite)
- Coluna `pfm_numero INTEGER` adicionada ao banco
- PFM salvo em `data/pfms/{codigo}.docx`
- Documento enviado via Telegram após geração
- Helpers: `_campo()`, `_itens()`, `_obs()`, `_secao()`, `proximo_pfm_numero()`
- `python-docx` adicionado às dependências

---

## [0.0.7] — 2026-06-25

### Fiada 7 — Coleta de dados do PFM
- Ao confirmar orçamento, bot entra em fluxo de coleta de dados para PFM
- Condição de pagamento via botões: 💰 PIX à vista | 💰 PIX 50%+50% | ✏️ Outro (digitado)
- Endereço de entrega via botões: 🏗 Obra (GGV) | 🏠 Casa | 🏢 Escritório | 🌳 Chácara | ✏️ Outro
- Endereços conhecidos hardcoded: GGV01/02/03 (Rua Índia), Casa, Escritório, Chácara
- Opção "Outro" em qualquer campo ativa entrada de texto livre pelo usuário
- Novo handler `receber_texto` processa respostas textuais em contexto (aguardando)
- Estado temporário salvo em `ctx.user_data` (doc_id, ggv, aguardando, condicao_pgto)
- Colunas `condicao_pgto` e `endereco_entrega` adicionadas ao banco com ALTER TABLE seguro
- Status do documento muda para `pronto_pfm` ao completar a coleta
- Exibe resumo final: GGV, pagamento e endereço confirmados

---

## [0.0.6] — 2026-06-25

### Fiada 6 — Classificação + GGV + Confirmação
- Claude classifica o documento: orçamento, comprovante PIX, extrato MP ou não relacionado
- Claude identifica o GGV pelo conteúdo (matrícula, endereço, número do pedido)
- Botões: ✅ Confirmar | 🔄 Tipo | 🏗 GGV | ❌ Cancelar
- Reclassificação manual de tipo e GGV via botões inline
- Bloqueio: não permite confirmar sem GGV definido (alerta popup)
- Rejeição de formatos não suportados (Excel, Word) com mensagem clara
- tipo e ggv salvos no banco SQLite

---

## [0.0.5] — 2026-06-25

### Fiada 5 — Claude lê o documento
- Após salvar, envia o arquivo para Claude (haiku-4-5)
- Extrai: tipo, fornecedor, CNPJ, itens, valor total, condição de pagamento, observações
- Exibe resultado no Telegram antes de qualquer gravação
- Funciona com foto (JPEG) e PDF

---

## [0.0.4] — 2026-06-25

### Fiada 4 — SQLite
- Cria banco `data/laura.db` automaticamente na inicialização
- Registra cada arquivo recebido: nome, caminho, hash, status, data
- Detecção de duplicatas persiste entre reinicializações do bot

---

## [0.0.3] — 2026-06-25

### Fiada 3 — hash SHA256
- Calcula impressão digital do arquivo antes de salvar
- Detecta duplicatas em memória durante a sessão
- Arquivo duplicado: avisa e ignora em vez de salvar duas vezes
- Exibe os primeiros 16 caracteres do hash na confirmação

---

## [0.0.2] — 2026-06-25

### Fiada 2 — bot salva arquivos
- Recebe foto → salva como `YYYYMMDD_HHMMSS.jpg` em `data/uploads/`
- Recebe PDF/documento → salva com timestamp + nome original
- Responde confirmando o nome do arquivo salvo
- Cria a pasta `data/uploads/` automaticamente se não existir

---

## [0.0.1] — 2026-06-25

### Fiada 1 — Bot online
- `bot.py` mínimo: /start responde "Estou online.", qualquer outra mensagem responde "Recebi."
- Segurança: só aceita mensagens do TELEGRAM_USER_ID configurado no .env
- Repositório privado criado no GitHub (dverschoor78/laura-bot)
- Primeiro commit versionado e push realizado

---

## [0.0.0] — 2026-06-25

### Adicionado
- Estrutura inicial do projeto
- Documentação de arquitetura (`docs/arquitetura.md`)
- Guia de instalação (`docs/instalacao.md`)
- Schema do banco SQLite (`app/db/migrations/001_initial.sql`)
- Script de migrations (`scripts/migrate.py`)
- Script de backup (`scripts/backup.sh`)
- `.gitignore` configurado
- `.env.example` com todas as variáveis necessárias
- `pyproject.toml` com dependências
- `README.md`
