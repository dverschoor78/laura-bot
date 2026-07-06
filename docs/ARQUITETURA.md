# Arquitetura do Projeto Laura

> Versão: 2026-07-06 — reflete o estado real do sistema (pós ADR-004: dispatch table + módulo
> `nfe/`; DOCX removido; segurança de `responder_botao()`/`atualizar()`/`atualizar_obra()`
> corrigida; `itens_pedido`/`parcelas_pagamento`/`insumos_sinapi` documentadas; `financeiro/consultas.py`
> e `financeiro/relatorios.py` adicionados; **módulo `compras/` — Lista de Compras com pipeline
> completo de interpretação (Camadas 1-3), Camada de enriquecimento de descrição genérica,
> Tela do Item unificada (view + menu de correção campo a campo, recálculo único ao concluir),
> cabeçalho editável (Obra/Endereço/Observações), gravação real em `listas_compra`/
> `lista_compra_itens` (substitui, não duplica, a cada confirmação), geração de PDF em 2
> variantes (`_gerar_html_lista`); endereço de entrega convergido entre Pedido de Compra e
> Lista de Compras via `teclado_escolha_endereco()`/`_cb_endsel()` único; **Consultoria de
> Recompra** (2026-07-06) — painel "🔁 Você já comprou isso" e botão "🔁 Repetir esta compra"
> na Tela do Item, sem limiar de tempo/preço; parser de data unificado (`_parse_data_qualquer`);
> **nome de arquivo padronizado** (`_slug_arquivo`, `GGV03-list-AAAA-MM-DD-resumo-orç/ref.pdf`)
> + campo `resumo`; "Gerar Lista de Compras" agora **encerra a lista** (`encerrar_lista`) em
> vez de reaproveitar uma `aberta` pra sempre — histórico por obra acessível via picker "📝
> Listas de Compras" no Cockpit da Obra (`listar_listas_obra`, `_cb_obra_listas`,
> `_cb_lc_abrir`, `_cb_lc_buscar`)**)
>
> **`LAURA_ENV=prod` ativo** — Laura em produção real desde 2026-07-06.

---

## 1. Visão Geral

A Laura é um bot Telegram pessoal para gestão de compras de obras GGV.

Dennis envia fotos ou PDFs de orçamentos pelo Telegram. O bot extrai os dados
com IA, apresenta para confirmação, gera o PFM em PDF numerado, salva no OneDrive
e registra o lançamento A PAGAR no banco.

**Tecnologias em uso:** Python 3.12 · python-telegram-bot 22 (+ `job-queue`/APScheduler) · SQLite ·
Claude API (Anthropic) · Playwright Chromium (HTML → PDF) · num2words (valor por extenso) ·
BrasilAPI (Receita Federal) · OneDrive (pasta local mapeada) · openpyxl (relatórios `.xlsx`,
`financeiro/relatorios.py`)

`python-docx` não é mais dependência de `bot.py` (DOCX removido em 2026-07-02) — continua usado só
por `scripts/import_fornecedores.py` (leitura de .docx legado, não geração).

---

## 2. Componentes

```
Telegram ──────► bot.py ──────► Claude API (haiku-4-5)
                   │
                   ├──────────► data/laura.db  (SQLite)
                   ├──────────► data/uploads/  (arquivos recebidos, staging)
                   ├──────────► Playwright Chromium (HTML → PDF em memória)
                   ├──────────► BrasilAPI (consulta CNPJ na Receita Federal)
                   └──────────► OneDrive/00 Obras/{AAAA-MM} {GGVxx}/
                                (orçamento, PFM, comprovante, NF-e, foto de entrega)
```

- **`bot.py`** — parcialmente modularizado (ADR-004, 2026-07-02): banco, IA, PFM e a maior parte
  dos handlers Telegram continuam aqui; `nfe/` (parsing/exibição de NF-e) e `financeiro/`
  (lançamento financeiro) já são módulos próprios, importáveis sem inicializar o bot. Único
  handler de callback (`responder_botao()`) verifica `DONO_ID` antes de rotear qualquer ação
  (corrigido 2026-07-03); helpers de UPDATE dinâmico (`atualizar()`, `atualizar_obra()`) validam
  nome de coluna contra allowlist antes de montar o SQL
- **`nfe/`** — parsing e exibição de NF-e (`nfe/nfe.py`); matching (`buscar_candidatos_nfe`) e
  vinculação (`vincular_nfe`) continuam em `financeiro/lancamento.py`. **Bug real corrigido
  (2026-07-06)**: nem "Nenhum destes" nem zero candidatos descartavam o documento (ao contrário
  do fluxo equivalente de comprovante PIX, que já descartava) — a NF-e ficava presa em
  `documentos` pra sempre, bloqueando reenvio do mesmo arquivo (hash já "recebido"). Corrigido:
  `teclado_candidatos_nfe()` embute `doc_id` no callback `nfe_cancelar:{doc_id}`,
  `_cb_nfe_cancelar()` chama `_descartar_documento(doc_id)`, e `_cb_sel_tipo_inicial()` (ramo
  `nota_fiscal`) descarta automaticamente quando `buscar_candidatos_nfe()` não acha nenhum
  candidato — mesmo padrão já usado por `comprovante_pix`.
- **`financeiro/consultas.py`** (2026-07-03) — 4 funções de leitura consolidada, sempre recebendo
  `db_path` explícito (ADR-002): `obter_pedido_completo()`, `obter_consolidado_obra()`,
  `listar_pedidos_pendentes()`, `procurar_item()`. Usadas por `scripts/consultar.py` (CLI) e por
  `financeiro/relatorios.py`
- **`financeiro/relatorios.py`** (2026-07-03) — gera fluxo de pagamentos por obra e relatório
  consolidado em Excel (`data/relatorios/*.xlsx`); ainda sem botão/comando no Telegram, só roda
  chamado manualmente
- **`compras/`** (2026-07-03) — domínio de Compras, nasce modular desde o primeiro dia (ADR-002).
  `compras/lista.py`: Lista de Compras e Item da Lista (Modelo de Domínio: `docs/MODELO_DOMINIO_COMPRAS.md`),
  todas as funções recebendo `db_path`. Três pontos de entrada em `bot.py` — comando `/lista`
  por texto, `/lista` por foto/PDF, e o tipo de documento `lista_materiais` — convergem pra
  mesma função de interpretação (`_interpretar_lista_texto`/`_interpretar_lista_arquivo`),
  nunca implementações separadas (ver Fluxo C). Pipeline completo: Camada 1 (interpretação
  JSON estruturada, com contexto da lista inteira) → Camada 2 (candidatos SINAPI via FTS5 +
  Claude decide, com termo técnico de busca e conversão de preço pra unidade comercial) →
  Camada 3 (última compra própria, filtro obrigatório de unidade igual) → **Camada de
  enriquecimento de descrição** (`_adicionar_sugestao_descricao`, 2026-07-05 — não faz busca
  nova, reaproveita os candidatos que Camada 2/3 já encontraram; sugestão histórico > SINAPI
  > original, como orientação, nunca aplicada sem ação explícita do usuário) → **Tela do Item
  unificada** (view + menu de correção campo a campo, recálculo único ao "Concluir edição" —
  ver Fluxo C) → **cabeçalho editável** (Obra/Endereço/Observações, 2026-07-05) → gravação
  real em `listas_compra`/`lista_compra_itens` ao confirmar, **substituindo (soft-delete) os
  itens ativos de confirmações anteriores** (2026-07-05 — confirmar 2x na mesma lista aberta
  duplicava itens; mesmo padrão de `_salvar_itens_pedido()`) → **PDF em 2 variantes**
  (`_gerar_html_lista(lista_id, com_precos)`, reaproveita `_PC_CSS`/`_html_para_pdf` do
  Pedido de Compra) gerado e arquivado em `04 Compras/00 Orçamentos/` automaticamente.
  Endereço de entrega reaproveita o mesmo mecanismo de presets do Pedido de Compra
  (`teclado_escolha_endereco()`/`_cb_endsel()` único, 2026-07-05 — princípio "Convergência
  antes de paralelismo", `docs/CONSTITUICAO.md`). Ainda sem geração de Pedido de Compra a
  partir da Lista nem vínculo com orçamento — ver ROADMAP.md
- **`data/laura.db`** — banco SQLite com dez tabelas (ver seção 3); 9 índices estratégicos
  criados em 2026-07-03, mas só no banco vivo — não persistidos em nenhum `CREATE INDEX` versionado
- **`data/uploads/`** — todo arquivo recebido pelo Telegram cai aqui primeiro (pasta única,
  achatada); é a partir daqui que os documentos são copiados para a pasta certa da obra
- **Claude API** — extração de dados dos documentos; modelo `claude-haiku-4-5-20251001`
- **Playwright Chromium** — geração de PDF a partir de HTML via `_html_para_pdf()`; roda
  headless em memória. Usado pelo Pedido de Compra 2.0 (`_gerar_html_pc`), pelo Recibo
  (`_gerar_html_recibo`, A5 paisagem) e pela Lista de Compras (`_gerar_html_lista`, 2 variantes,
  2026-07-05) — mesma função, formato/orientação por parâmetro
- **BrasilAPI** — consulta pública e gratuita de CNPJ na Receita Federal; usada por
  `_criar_fornecedor_auto()` e pelo job periódico `_sincronizar_receita_pendentes()`; falha
  silenciosamente (timeout 4s) sem travar o fluxo do bot
- **OneDrive** — destino final de todos os documentos de uma obra; ver seção 2.1
- **`prints/pc_alternativa_a.html`** — protótipo aprovado do PC 2.0; referência de design

---

## 2.1 Organização de arquivos por obra (2026-07-01)

Cada obra tem uma pasta raiz no OneDrive, cadastrada em `obras.pasta_onedrive`
(ex: `00 Obras/2026-06 GGV03`). A partir dessa raiz, o bot deriva cada subpasta por
convenção — não há necessidade de configurar cada subpasta manualmente:

| Tipo de documento | Subpasta (derivada por `_pasta_*()`) | Nome do arquivo |
|---|---|---|
| Orçamento original | `04 Compras/00 Orçamentos/` | `{pfm_codigo} - {Fornecedor} - {Resumo}.{ext}` |
| PFM gerado (.pdf) | `04 Compras/` | `{pfm_codigo} - {Fornecedor} - {Resumo}.pdf` |
| Comprovante de pagamento | `01 Controle financeiro/` | `{AAAA-MM-DD} {pfm_codigo} {Fornecedor} - comprovante.{ext}` |
| NF-e | `01 Controle financeiro/` | `{AAAA-MM-DD} {pfm_codigo} {Fornecedor} - NFe {numero}.{ext}` |
| Foto de entrega | `05 Entrega/` | `{AAAA-MM-DD} {pfm_codigo} {Fornecedor} - foto{NN}.{ext}` |
| Recibo (Fiada 6b, ainda não implementado) | `05 Entrega/` | `{AAAA-MM-DD} {pfm_codigo} {Fornecedor} - recibo.{ext}` |

A data usada é sempre a **data real do documento** (data de pagamento, data de emissão da NF-e),
não a data em que o arquivo foi processado — `_data_para_arquivo()` entende `DD/MM/AAAA` e
`DD de mês de AAAA`. "Resumo" vem de um campo novo do PROMPT ("Resumo da compra", 2-4 palavras)
que resume o item principal do orçamento, ex: "Espelho", "aço".

`_arquivar_documento()` é o helper compartilhado — recebe o `pfm_codigo`, o sufixo do nome, o
caminho original (em `data/uploads/`) e uma função que resolve a pasta de destino. Falha
silenciosamente (não bloqueia nenhum fluxo do Telegram) se o arquivo original não existir mais.

**Escopo por obra:**
- **GGV03** — raiz configurada, convenção nova completa
- **GGV00** — raiz configurada (pasta vazia; estrutura é criada quando o primeiro documento chegar)
- **GGV01** — `pasta_onedrive` vazia de propósito. Regra explícita: nunca escrever na estrutura
  antiga dela
- **GGV02** — `pasta_onedrive` vazia. Em conclusão; estrutura real da pasta é diferente (sem
  "00 Orçamentos", com "51 Obra - Materiais e serviços") — decisão de onde arquivar pendente

Se `pasta_onedrive` estiver vazia para uma obra, os documentos caem em `data/pfms/` (local, não
sincronizado) em vez de falhar — evita gravar no lugar errado por engano.

---

## 3. Banco de Dados

**`documentos`** — registro de cada arquivo recebido e seu ciclo de vida

| Campo | Propósito |
|---|---|
| `id` | Chave primária |
| `hash` | SHA256 do arquivo — detecta duplicatas |
| `tipo` | Classificação: orcamento · comprovante_pix · extrato_mp |
| `ggv` | GGV identificado: GGV00–GGV03 ou nao_identificado |
| `dados_claude` | Texto bruto retornado pelo Claude; campos extraídos via `_campo()` na leitura |
| `condicao_pgto`, `data_entrega`, `endereco_entrega`, `desconto_rs` | Dados coletados durante o fluxo de confirmação |
| `vencimento_pgto` | Data/condição de vencimento — editável pelo usuário |
| `encarregado` | Encarregado por documento — sobrescreve padrão do dict `GGV_ENCARREGADO` |
| `pfm_numero` | Número sequencial por GGV (ex: 9 → GGV03-009) |
| `status` | Ciclo de vida: recebido → confirmado → pfm_gerado → cancelado |
| `caminho_pfm` | Caminho real do .pdf gerado (2026-07-01; DOCX removido em 2026-07-02) — lido direto, não reconstruído por convenção de nome |

---

**`lancamentos`** — registros financeiros A PAGAR / PAGO

| Campo | Propósito |
|---|---|
| `doc_id` | Referência lógica ao documento de origem (sem FK explícita) |
| `pfm_codigo` | Chave do lançamento (ex: GGV03-009) — UNIQUE |
| `fornecedor`, `valor` | Dados financeiros principais |
| `status` | a_pagar · pago · pendente_revisao · substituido |

Relação: um documento origina um lançamento. `pfm_codigo` é a chave de cruzamento.

---

**`entrega_fotos`** — fotos/documentos de entrega vinculados a um pedido (Fase 6, Fiada 6c++)

| Campo | Propósito |
|---|---|
| `id` | Chave primária |
| `pfm_codigo` | Pedido ao qual a foto pertence — sem FK explícita com `lancamentos` |
| `doc_id` | Referência lógica a `documentos.id` — sem FK explícita |
| `legenda` | Obrigatória ao anexar; identifica a foto na galeria ("👀 Ver arquivos") |
| `criado_em` | Timestamp de inserção |

Um pedido pode ter N fotos. O estado "entrega registrada" continua em `lancamentos.obs_entrega`
(não nesta tabela) — ver `docs/decisoes/ADR-003-extracao-entrega-adiada.md` para a discussão
sobre por que esse acoplamento entre tabelas de domínios diferentes ainda existe.

---

**`fornecedores`** — cadastro de fornecedores, validado contra a Receita Federal (2026-07-01)

Campos relevantes: `nome`, `razao_social`, `cnpj`, `cpf`, `chave_pix`, `email`,
`whatsapp`, `logradouro`, `bairro`, `cidade`, `uf`, `ramo`, `receita_pendente`.

Uso: `buscar_fornecedor()` tenta primeiro por CNPJ, depois pelo primeiro token do nome.
Quando encontrado, os dados do cadastro prevalecem sobre os dados extraídos pelo Claude.
Campo `ramo` é salvo automaticamente quando extraído do orçamento e o fornecedor ainda não o tem.

Quando um orçamento traz um CNPJ que não bate com nenhum cadastro (`buscar_fornecedor()` retorna
`None`), `_criar_fornecedor_auto()` cadastra um novo fornecedor automaticamente e tenta enriquecer
com dado oficial da Receita (BrasilAPI). Se a consulta falhar, `receita_pendente=1` e o job
`_sincronizar_receita_pendentes()` tenta de novo a cada 6h.
Sem relação de FK com as demais tabelas.

---

**`obras`** — cadastro das obras GGV (adicionada na Fase 4a)

| Campo | Propósito |
|---|---|
| `codigo` | Chave primária (ex: GGV03) |
| `descricao` | Descrição completa da obra/matrícula |
| `endereco_entrega` | Endereço padrão de entrega dos materiais |
| `encarregado_nome`, `encarregado_fone` | Encarregado da obra |
| `responsavel_nome`, `responsavel_fone` | Responsável (Dennis por padrão) |
| `pasta_onedrive` | Caminho local da pasta OneDrive do GGV |
| `ativa` | Flag de obra ativa (1/0) |

Pré-populada com GGV00–GGV03 via `_migrar_obras()` (idempotente).
Substitui os dicts hardcoded `GGV_ENCARREGADO`, `GGV_DESC`, `GGV_ONEDRIVE` e `ENDERECOS`.

---

**`itens_pedido`** — itens de compra estruturados por pedido (criada em 2026-07-02)

| Campo | Propósito |
|---|---|
| `id` | Chave primária |
| `pfm_codigo` | Pedido ao qual o item pertence — sem FK explícita com `lancamentos` |
| `numero` | Ordem do item dentro do pedido |
| `descricao`, `unidade`, `quantidade`, `valor_unitario`, `valor_total` | Dados do item, extraídos via `ITEM_RE`/`_itens()`; item que o regex não conseguiu parsear é salvo só com `descricao` |
| `insumo_sinapi_codigo` | Coluna já existe no schema, mas nada grava nela ainda — vínculo futuro com `insumos_sinapi` |

`_salvar_itens_pedido()` substitui (DELETE + INSERT) todos os itens de um `pfm_codigo` a cada
geração ou revisão do PFM, sempre refletindo a lista mais recente. `scripts/backfill_itens_pedido.py`
populou os pedidos já existentes antes desta tabela existir. Consultada por
`financeiro/consultas.py::procurar_item()` (busca por descrição parcial) e `obter_pedido_completo()`.

---

**`parcelas_pagamento`** — cada pagamento parcial de um pedido (Fase 6, "Pagamento parcelado")

| Campo | Propósito |
|---|---|
| `id` | Chave primária |
| `pfm_codigo` | Pedido ao qual a parcela pertence — sem FK explícita com `lancamentos` |
| `valor`, `data_pagamento` | Dados do pagamento |
| `doc_id_comprovante`, `identificador_comprovante` | Comprovante vinculado + chave de deduplicação |
| `doc_id_recibo`, `doc_id_recibo_assinado` | Recibo gerado e, depois, a versão assinada anexada |
| `status` | Ciclo por parcela: `pago` → `aguardando_assinatura` → `assinado` |

`lancamentos.status` só vira `pago` quando `SUM(parcelas_pagamento.valor) >= lancamentos.valor`.
Escrita ainda 100% em `bot.py` (`_registrar_parcela()`) — dono do domínio não decidido, gatilho
pendente da ADR-004 (ver Dívida Técnica em ROADMAP.md). `financeiro/consultas.py` só lê.

---

**`insumos_sinapi`** — tabela de referência de preços SINAPI, sem vínculo operacional (2026-07-01)

| Campo | Propósito |
|---|---|
| `codigo` | Código oficial SINAPI |
| `descricao`, `unidade`, `preco_pr` | Dados do insumo, preço de referência do Paraná |
| `mes_referencia` | Mês/ano da planilha importada |
| `fabricante` | Nunca sobrescrito por reimportação — preenchido manualmente aos poucos |
| `atualizado_em` | Timestamp da última importação |

Populada por `scripts/import_sinapi.py` (baixa a planilha oficial da Caixa, sem login). Tabela solta
— nenhuma FK com `itens_pedido` ou `documentos`; `itens_pedido.insumo_sinapi_codigo` existe no schema
mas nada grava nela ainda.

**`insumos_sinapi_fts`** (2026-07-04) — tabela virtual FTS5, busca por palavra (não por frase
inteira) contra `descricao`. "External content" — não duplica dado, só indexa; `content_rowid`
aponta pro `codigo` já existente. Reconstruída do zero (`DROP` + `CREATE` + `INSERT`, nunca
`DELETE` — instável nesta versão do SQLite, ver comentário em `scripts/import_sinapi.py`) a cada
reimportação, via `reconstruir_indice_fts()`. Motivo: `LIKE '%termo%'` falha quando a ordem das
palavras muda (ex: "tubo pvc 25" não batia com "PVC, SOLDAVEL, DE 25 MM"); FTS5 tokeniza e resolve.

---

**`listas_compra`** — Lista de Compras, momento "antes da compra" (domínio Compras, 2026-07-03)

| Campo | Propósito |
|---|---|
| `id` | Chave primária |
| `ggv` | Obra à qual a lista pertence — sem FK explícita |
| `status` | `aberta` / `encerrada` / `descartada` (Modelo de Domínio) — desde 2026-07-06, `_cb_lc_gerar()` sempre fecha a lista (`encerrar_lista()`) depois de gravar; `aberta` só existe no intervalo entre a criação do registro e o fim daquela mesma chamada |
| `endereco_entrega` | Override de endereço só desta lista (2026-07-05) — herdado de `obras.endereco_entrega` na tela, nunca sobrescreve o cadastro da obra; `NULL` até o usuário editar |
| `observacoes` | Observações gerais da compra, opcional (2026-07-05) — instrução geral, não por item |
| `resumo` | Texto curto digitado pelo usuário (2026-07-06) — nomeia os PDFs gerados (`_slug_arquivo()`) e é o campo de busca do picker "📝 Listas de Compras"; opcional, `NULL` vira slug `lista-compras` no nome do arquivo |
| `criado_em` | Timestamp de criação |

**Ciclo de vida mudou em 2026-07-06** — até então, uma obra tinha no máximo uma lista `aberta`
por vez (`buscar_lista_aberta()`), reaproveitada indefinidamente a cada `/lista` novo. Dennis
perguntou como voltar numa lista já gerada pra editar (filtrar por data, localizar por nome) —
resposta exigiu que cada geração virasse um registro histórico, não uma edição in-place da
mesma linha. Agora `_cb_lc_gerar()` sempre chama `encerrar_lista(db_path, lista_id)` depois de
gravar; `criar_ou_buscar_lista_aberta()` continua existindo (usado quando não há
`lista_id_edicao` na sessão) mas na prática sempre cria um registro novo, porque nada fica
`aberta` de verdade entre uma sessão e outra. `listar_listas_obra(db_path, ggv, limite=10,
busca_resumo=None)` lista o histórico, mais recente primeiro, com contagem de itens ativos por
lista (subquery contra `lista_compra_itens`).

`atualizar_lista(db_path, lista_id, **kwargs)` grava `endereco_entrega`/`observacoes`/`resumo`
(allowlist `_COLUNAS_LISTA_EDITAVEIS`, mesmo padrão de segurança de
`atualizar()`/`atualizar_obra()`) — `_cb_lc_gerar()` só chama quando o campo foi tocado na
sessão corrente, pra nunca apagar um valor já salvo ao reabrir uma lista existente.

**Reabrir uma lista antiga pra editar** (`_cb_lc_abrir`, callback `lc_abrir:{lista_id}` a partir
do picker no Cockpit da Obra) carrega `listar_itens()` + o próprio registro (`buscar_lista()`)
de volta em `ctx.user_data` — mesma Tela de Conferência de uma interpretação nova, e
`ctx.user_data["lista_id_edicao"]` sinaliza pra `_cb_lc_gerar()` regravar essa mesma `lista_id`
em vez de criar outra. Os 4 pontos que iniciam uma interpretação nova (`/lista` texto/foto,
botão no menu de documento) resetam `lista_id_edicao` pra `None`, pra nunca confundir uma
sessão nova com uma reabertura.

**Cada confirmação substitui os itens ativos, não acumula** (2026-07-05) — achado real:
confirmar "Gerar Lista de Compras" 2x na mesma lista aberta (ex: testar, corrigir, testar de
novo) duplicava todos os itens, porque `adicionar_item()` só insere. `_cb_lc_gerar()` agora
marca (soft-delete, via `remover_item()`) todos os itens ativos daquela `lista_id` antes de
gravar os novos — mesmo padrão de `_salvar_itens_pedido()` (Pedido de Compra): a versão mais
recente sempre substitui a anterior, histórico preservado (não apagado de verdade).

---

**`lista_compra_itens`** — itens de uma Lista de Compras, antes de qualquer fornecedor definido

| Campo | Propósito |
|---|---|
| `id` | Chave primária |
| `lista_id` | Lista à qual o item pertence — sem FK explícita |
| `descricao`, `unidade`, `quantidade` | Dados do item — quantidade pode ser `NULL` |
| `fabricante`, `codigo` | Identidade comercial do item (marca e código de referência do fabricante) — adicionadas 2026-07-04 junto com a primeira gravação real; mesma categoria de descricao/unidade/quantidade, não são "snapshot" de referência externa |
| `sinapi_codigo` | Vínculo/rastreabilidade com `insumos_sinapi` — não usar pra exibição histórica |
| `sinapi_descricao_referencia`, `sinapi_unidade_referencia`, `sinapi_preco_referencia`, `sinapi_mes_referencia` | **Snapshot** SINAPI congelado no momento da confirmação — `insumos_sinapi` muda todo mês, a leitura de uma lista antiga não pode mudar de valor sozinha (CONSTITUICAO.md, "Dados são sagrados") |
| `sinapi_confianca`, `sinapi_preco_equivalente` | Adicionadas 2026-07-05 — já calculadas pela Camada 2 desde o início, mas não eram persistidas; sem elas, reler a lista do banco (ex: pro PDF) perdia o grau de confiança e o preço já convertido pra unidade comercial |
| `laura_preco_referencia`, `laura_data_referencia`, `laura_fornecedor_referencia`, `laura_origem_referencia`, `laura_grau_confianca_referencia` | **Snapshot** da referência interna da Laura (último preço pago/média/item semelhante/sem referência), mesmo motivo — nunca recalculado depois. Vocabulário de confiança do Princípio 8 da Política de Compras |
| `observacoes` | Texto livre por item |
| `status` | `pendente` / `comprado` / `removido` — hoje só `pendente`/`removido` são alcançáveis (vínculo com Pedido de Compra é fiada futura) |
| `criado_em` | Timestamp de inserção |

2026-07-04: `_cb_lc_gerar()` (bot.py, botão "✅ Gerar Lista de Compras" da tela de conferência)
chama `criar_ou_buscar_lista_aberta()` + `adicionar_item()` com todos os campos, incluindo os
snapshots SINAPI/Laura já calculados pelas Camadas 2 e 3 — a Lista de Compras passa a existir
de verdade no banco a partir da confirmação do usuário. Bloqueia se a obra não estiver
definida (`ggv NOT NULL`). Ainda não gera Pedido de Compra nem cria vínculo com orçamento —
ver ROADMAP.md, Fase — Módulo de Compras.

---

## 4. Fluxos

**Fluxo A — Orçamento → PFM → Lançamento**

```
Dennis envia foto ou PDF
  → bot calcula SHA256, detecta duplicatas
  → salva em data/uploads/
  → envia para Claude API com PROMPT estruturado
  → Claude retorna tipo, GGV e campos extraídos
    (inclui: Ramo, Número do orçamento, Vendedor, Telefone do vendedor)
  → bot exibe para confirmação (botões inline)
  → Dennis confirma (ou edita tipo, GGV, campos)
  → bot coleta condição de pagamento e endereço de entrega
  → Dennis aciona "Gerar PFM"
  → gerar_pfm() define o código do pedido, salva itens, registra lançamento A PAGAR
  → _gerar_html_pc() monta HTML do Pedido de Compra 2.0
  → _html_para_pdf() converte HTML → PDF via Playwright Chromium (único documento gerado)
  → envia o .pdf para Dennis no Telegram, salvo também na pasta OneDrive da obra
```

**Fluxo B — Consulta de pedido por código**

```
Dennis digita o código (ex: GGV03-009)
  → regex PFM_CODIGO_RE detecta o código no texto
  → buscar_pedido() consulta documentos + lancamentos
  → preparar_visualizacao_pedido() verifica arquivos em disco
  → mostrar_pedido() formata a tela
  → bot exibe tela do pedido com botões de ação
```

**Fluxo C — Lista de Compras: interpretação, conferência e gravação** *(2026-07-04/05)*

```
Dennis dispara por três caminhos, que convergem pras mesmas funções:
  (a) /lista [GGV opcional] envia texto → bot pede "Envie a lista — texto, foto ou PDF"
  (b) /lista envia foto/PDF
  (c) envia foto/PDF → escolhe "📝 Lista de materiais" no menu de tipo de documento

  → texto: _interpretar_lista_texto() | foto/PDF: _interpretar_lista_arquivo()
    Camada 1 — PROMPT_INTERPRETAR_LISTA (nunca passa pelo PROMPT de classificação
    compartilhado; nunca inventa preço/quantidade; considera a lista inteira como
    conjunto pra reduzir ambiguidade — ex: "argamassa" numa lista de revestimentos é
    colante, não reboco; separa embalagem (tamanho de uma unidade de venda) de
    quantidade/unidade da compra; código copiado literalmente — Lições #12/#13)
    → _itens_lista_materiais() faz json.loads() com fallback defensivo (Lição #13)
  → Camada 2 — _adicionar_correspondencia_sinapi(): busca candidatos por termo técnico
    inferido (não pelo nome comercial) via FTS5, uma chamada ao Claude decide a lista
    inteira; grau de confiança sempre declarado; preço do SINAPI convertido pra unidade
    comercial do item (nunca o contrário — "A Laura nunca converte o item comercial para
    a unidade do SINAPI")
  → Camada 3 — _adicionar_referencia_laura(): última compra própria via procurar_item(),
    só aceita candidato com unidade igual à comercial (sem conversão, ao contrário da
    Camada 2) — filtro que existe pra evitar casar produtos diferentes por palavra isolada
  → Enriquecimento de descrição — _adicionar_sugestao_descricao() (2026-07-05): não busca
    nada novo, reaproveita os candidatos que Camada 2/3 já encontraram. Se a Camada 1 marcou
    a descrição como genérica demais pra cotação (campo `descricao_generica`, julgamento da
    IA), sugere a descrição do histórico próprio (prioridade) ou do SINAPI (apoio, só com
    confiança alta/média) — nunca decide sozinha, só anota `descricao_sugerida` pra tela
    apresentar
  → Nível 1 — Tela de Conferência (_texto_lista_conferencia/_teclado_lista_conferencia):
    item/quantidade/referência em 3 linhas, indicador 🟢🟡🔴, alertas agrupados, resumo.
    "A Laura apresenta primeiro a informação necessária para a decisão." Cabeçalho com 3
    campos editáveis (2026-07-05): 🏗 Obra, 📍 Endereço (herdado da obra, override só desta
    lista), 🗒 Observações gerais (opcional) — ctx.user_data["lista_ggv"/"lista_endereco"/
    "lista_observacoes"] guardam o estado de trabalho
  → Nível 2 — Tela do Item (_texto_tela_item/_teclado_item_tela, redesenhada 2026-07-05):
    view + menu de correção numa tela só, não mais ficha técnica com edição misturada.
    Cada campo (Produto/Fabricante/Código/Quantidade/Unidade/Observações) abre um prompt
    isolado (_cb_lc_campo) que grava num rascunho (ctx.user_data["lista_item_rascunho"]),
    nunca no item real; Referência/Correspondência somem da tela enquanto há rascunho
    pendente. "💾 Concluir edição" (_cb_lc_concluir) roda Camada 2+3 uma única vez sobre o
    rascunho e volta pra Nível 1 já atualizado — nunca uma chamada de IA por campo
    corrigido. "🔄 Reinterpretar item" (Camada 1+2+3 completa via texto livre) só aparece
    pra itens em fallback (string, não interpretado) — não compete mais com "Concluir
    edição" na tela principal. "✅ Usar sugestão" (_cb_lc_usarsugestao, 2026-07-05) aplica a
    descrição sugerida no rascunho, mesmo mecanismo de "Concluir edição" — sem IA extra
  → Consultoria de Recompra (_linhas_recompra, 2026-07-06): quando o item tem referência
    própria (`laura_preco_referencia`), a Tela do Item mostra o painel "🔁 Você já comprou
    isso" (descrição/fornecedor/unidade/preço históricos + "há quanto tempo" via
    _tempo_decorrido, e a variação % contra o preço SINAPI atual via _preco_sinapi_item) no
    lugar da sugestão de descrição genérica — sem limiar de tempo/preço fixo, é sinal pra
    decisão humana, nunca bloqueio. Botão "🔁 Repetir esta compra" (_cb_lc_repetircompra)
    aplica a descrição histórica no rascunho, mesmo mecanismo de "Usar sugestão"
    (_aplicar_descricao_no_rascunho compartilhada entre os dois). Comparar fornecedores
    diferentes fica pra depois (decisão do Dennis)
  → Análise Técnica (_texto_analise_tecnica para a lista inteira, _texto_item_tecnico por
    item — mesma formatação via _linhas_analise_item compartilhada): confiança, SINAPI
    bruto, histórico, e a alternativa não escolhida quando histórico venceu SINAPI — opcional,
    acessada por botão, nunca a tela principal
  → botão "✅ Gerar Lista de Compras" (_cb_lc_gerar): remove (soft-delete) os itens ativos de
    confirmações anteriores dessa lista (2026-07-05 — evita duplicação ao confirmar 2x), grava
    de verdade via criar_ou_buscar_lista_aberta() (ou a lista_id em edição, se reaberta pelo
    picker) + adicionar_item() (itens) + atualizar_lista() (endereço/observações/resumo, só se
    tocados nesta sessão) — bloqueia se a obra não estiver definida — encerra a lista
    (encerrar_lista(), 2026-07-06) — e gera + envia 2 PDFs automaticamente (_gerar_html_lista,
    "Referência" com preço e "Orçamento" em branco pra fornecedor), nome
    `{GGV}-list-{data}-{resumo-slug}-{orç|ref}.pdf` (_slug_arquivo()), arquivados em
    `04 Compras/00 Orçamentos/` (PDFs de gerações antigas nunca são apagados)
```

**Fluxo D — Reabrir uma Lista de Compras antiga pra editar** *(2026-07-06)*

```
Dennis digita o código da obra (ex: GGV03) → Cockpit da Obra
  → botão "📝 Listas de Compras" (_cb_obra_listas): listar_listas_obra() mostra as últimas 10,
    mais recente primeiro (data + Resumo + nº de itens)
  → "🔍 Buscar por nome" (_cb_lc_buscar): filtra listar_listas_obra() pelo Resumo (LIKE)
  → tocar numa lista (_cb_lc_abrir, callback lc_abrir:{lista_id}): carrega listar_itens() +
    buscar_lista() (endereço/observações/resumo) de volta em ctx.user_data — mesma Tela de
    Conferência de uma interpretação nova; ctx.user_data["lista_id_edicao"] guarda qual
    lista_id está sendo editada
  → edição normal (Tela do Item, cabeçalho) → "✅ Gerar Lista de Compras" regrava a mesma
    lista_id (não cria outra) e encerra de novo — ver Fluxo C
```

Endereço de entrega (Nível 1 e Pedido de Compra) usa o **mesmo mecanismo** —
`teclado_escolha_endereco(destino, param, ggv, voltar_callback)` + `_cb_endsel()` único,
bifurcando só no destino final da gravação (`documentos` vs `ctx.user_data`). Ver seção 2 e
princípio "Convergência antes de paralelismo" em `docs/CONSTITUICAO.md`.

Pendente: geração de Pedido de Compra a partir da Lista de Compras; vínculo com orçamento —
ver ROADMAP.md, Fase — Módulo de Compras.

⚠️ **Divergência conhecida, fora do escopo desta fiada**: o pipeline de confirmação de
`comprovante_pix`/`nota_fiscal` (Fluxo A) tem três pontos de entrada que não convergem
entre si — ver Dívida Técnica e "Motor de Interpretação e Classificação de Documentos" em
`docs/ROADMAP.md`.

---

## 5. Estrutura do bot.py

Referências para navegação no arquivo (4.994 linhas):

| Bloco | Referência | O que faz |
|---|---|---|
| Imports e inicialização | `load_dotenv()`, `claude = anthropic...` | Dependências, variáveis de ambiente, cliente Claude |
| Constantes e configuração | `TIPOS`, `DELTAD`, `GGV_ONEDRIVE` | Mapeamentos de tipos, GGVs, dados DeltaD, endereços |
| Domínio — Pedido | `StatusPedido`, `Pedido` | Enum de status e dataclass com 17 campos |
| Integração Claude | `PROMPT` | Prompt de extração estruturada (inclui template `lista_materiais`, 2026-07-03) |
| Banco de dados | `init_db()`, `buscar_fornecedor()` | Criação de tabelas, CRUD |
| Geração de PFM | `gerar_pfm()`, `_campo()`, `_itens()` | Helpers de parsing/formatação; define código, salva itens, registra lançamento (não gera documento — ver `_gerar_html_pc()`) |
| Domínio — consulta | `buscar_pedido()`, `mostrar_pedido()` | Pipeline de visualização do pedido |
| Domínio — Lista de Compras | `lista_cmd()`, `_interpretar_lista_texto/arquivo()`, `_adicionar_correspondencia_sinapi()`, `_adicionar_referencia_laura()`, `_adicionar_sugestao_descricao()`, `_texto_lista_conferencia()`, `_texto_tela_item()`, `_gerar_html_lista()`, `_slug_arquivo()`, `_cb_lc_*()`, `_cb_obra_listas()` | Comando `/lista` + fluxo de foto (`lista_materiais`); Camadas 1-3 de interpretação, enriquecimento de descrição, Tela do Item (view + correção campo a campo), cabeçalho editável (Obra/Endereço/Observações/Resumo), gravação (substitui, não duplica, encerra a lista) via `compras.*`, PDF em 2 variantes com nome padronizado; picker "📝 Listas de Compras" no Cockpit da Obra (buscar por nome, reabrir lista antiga) |
| Teclados | `parse_resposta()`, `teclado_confirmacao()` | Parse da resposta Claude e botões inline |
| Handlers Telegram | `receber_arquivo()`, `receber_texto()` | Handlers de mensagens |
| Dispatch de callback | `responder_botao()`, `_CB_DISPATCH`, `_cb_*()` | Um único `CallbackQueryHandler`; roteia por dict `acao → função` (ADR-004, 2026-07-02) em vez de if/elif — 59 funções `_cb_*`, cada uma cobrindo os ramos que antes viviam soltos dentro de uma função de 929 linhas |
| Inicialização | `if __name__ == "__main__": ... app.run_polling()` | Registro dos handlers e loop principal — protegido por guard desde 2026-07-02 (importar `bot.py` não inicia mais o bot) |

---

## 6. Limitações Conhecidas

- **Tela do Item esconde a razão de uma referência não calculada** — quando o SINAPI acha um
  código com confiança alta mas não converte a unidade (ex: Cal Hidratada: KG→SC sem
  embalagem conhecida), a Tela do Item mostra só "Referência: ainda não conhecida" — a
  `observacoes` do item, que já explica o motivo, não aparece nesse nível (só na Análise
  Técnica), e `_referencia_e_correspondencia()` esconde "Correspondência: Alta confiança"
  junto com o preço ausente, como se nada tivesse sido encontrado. Achado 2026-07-05, ao
  vivo; correção diagnosticada, não implementada — ver ROADMAP.md.

- **`termo_busca_sinapi` não traduz termo coloquial pro vocabulário técnico SINAPI** — pra
  descrições muito curtas (ex: "Brita" sozinha), a Camada 1 às vezes repete a palavra
  literal em vez de inferir o termo técnico correto (deveria ser "pedra britada" — buscar
  "brita" no FTS5 traz concreto usinado, não as referências de pedra britada que realmente
  existem no SINAPI). Achado 2026-07-05, ao vivo; correção diagnosticada (reforçar o
  prompt), não implementada.

- **Grau de confiança do SINAPI nem sempre reflete ambiguidade real detectada pela própria
  IA** — achado com "Tijolos": Claude escolheu 1 candidato entre 6 bem diferentes com "Alta
  confiança", mas a própria `observacoes` gerada na mesma resposta já sinalizava que
  tipo/dimensão precisavam ser confirmados — inconsistência interna que devia ter rebaixado
  a confiança. Achado 2026-07-05, ao vivo; não corrigido.

- **Confirmação de documento diverge por ponto de entrada** — `_cb_sel_tipo_inicial()` (fluxo
  automático), `_cb_set_tipo()` (correção manual — bug real: chama `_resumo_gerar()` sempre,
  não importa o tipo) e `_cb_ok()` (confirmação genérica — trata `comprovante_pix` incompleto,
  `nota_fiscal` nem trata) implementam o mesmo objetivo de três formas diferentes. Achado
  2026-07-03; fiada de investigação própria antes de mexer — ver "Motor de Interpretação e
  Classificação de Documentos" em `docs/ROADMAP.md`.

- **Monólito parcial** — `bot.py` com 4.994 linhas, acima do teto da ADR-001 (2.500–3.000).
  ADR-004 (2026-07-02) extraiu dispatch table + módulo `nfe/`; `fornecedor/`/`obra/`/`comprovante/`
  avaliados e adiados com gatilho próprio; `entrega/` continua adiada (ADR-003, motivo não mudou).
  Crescimento recente concentrado no pipeline de Compras (Camadas 1-3 + tela de 3 níveis,
  2026-07-04) — candidato natural a módulo próprio quando o teto for revisitado.

- **`responder_botao()` é um único handler** — agora roteia por dispatch table (`_CB_DISPATCH`,
  66 funções `_cb_*`) em vez de if/elif, mas continua sendo um único `CallbackQueryHandler` com um
  único `try/except` — um erro em qualquer ramo ainda aparece como "Erro inesperado" genérico,
  sem isolamento por domínio. `sel_tipo_inicial` continua misturando 4 domínios (entrega, pix,
  nfe, pfm) internamente, não coberto pela divisão em `_cb_*`. Ver ADR-004.

- **`gerar_pfm()` acumula responsabilidades** — grava no banco, cria o lançamento e arquiva em
  disco na mesma função (a geração do documento em si — Word — foi removida em 2026-07-02).

- **Bug real corrigido (2026-07-06)**: `gerar_pfm()` no modo revisão (`pfm_codigo_override`,
  botão "Revisar" → rev01/rev02) nunca atualizava `lancamentos` — o PDF saía com o valor
  corrigido, mas o Cockpit da Obra e a Tela do Pedido (que leem `lancamentos.valor`) ficavam
  travados no valor da geração original pra sempre. Achado ao vivo com um caso real
  (GGV03-012: revisão corrigiu o item pra R$ 820,00, lançamento continuava em R$ 745,00 — o
  pagamento já registrado já estava certo em R$ 820,00, só o campo `valor` do lançamento
  estava desatualizado). Corrigido: revisão agora também executa
  `UPDATE lancamentos SET fornecedor=?, valor=?, data_prevista_entrega=?` — nunca mexe em
  `status`, `valor_pago`, NF-e ou qualquer campo da jornada de pagamento.

- **`dados_claude` armazena texto bruto** — campos não são estruturados no banco;
  toda extração ocorre na leitura via `_campo()`. Mudanças no formato do Claude
  podem afetar a leitura de documentos antigos.

- **`pfm_caminho` não existe como coluna** — o path do arquivo .docx é reconstruído
  a cada consulta com base em `GGV_ONEDRIVE` + `pfm_codigo`. Inconsistente se a
  estrutura de pastas mudar.

- **BD fornecedores com dados incorretos** — MO Construção com CNPJ errado;
  PRUDENTÓPOLIS com split incorreto. Afeta `buscar_fornecedor()`.

- **Camada de parsing frágil contra variação real do Claude** — vários bugs de 2026-07-01
  (template misturado, unidade com dígito, valor com milhar ambíguo, data sem zero à esquerda)
  nasceram de suposições de formato fixo. Catálogo completo e lição geral em
  `docs/LICOES_EXTRACAO.md` — ler antes de mexer em PROMPT ou qualquer regex de extração.

- **Fotos enviadas como "photo" no Telegram chegam com resolução baixa demais pra tabela
  densa** — descoberto 2026-07-04: uma foto real de lista de materiais (8 itens) chegou ao bot
  com apenas **631×161 pixels**, mesmo parecendo legível no app do Telegram (o app reamplia
  pra exibição). Nessa resolução, colunas próximas (ex: "m2" vs "m", "sc" vs valor da linha
  vizinha) ficam genuinamente ambíguas pro Claude — confirmado repetindo a mesma extração 3x
  e obtendo respostas diferentes a cada vez pras mesmas duas linhas problemáticas. Não é bug
  de prompt: `receber_arquivo()` já baixa exatamente o que o Telegram fornece
  (`update.message.photo[-1].get_file()`, sem recompressão própria) — a perda de qualidade é
  do Telegram, que compacta agressivamente uploads do tipo "foto" (mais ainda em imagens
  simples tipo tabela em fundo branco). **Mitigação disponível sem código**: enviar a lista
  como arquivo/documento no Telegram (anexo, não como foto) — `receber_arquivo()` já trata
  esse caminho via `update.message.document`, que preserva a resolução original sem
  compressão. `PROMPT_INTERPRETAR_LISTA` ganhou uma checagem de plausibilidade (releitura
  quando a unidade lida não faz sentido técnico pro produto) que ajuda parcialmente, mas não
  substitui ter pixels suficientes pra ler a tabela.

---

## 7. Decisões Arquiteturais Registradas

- **ADR-001** — manter o monólito em `bot.py`, com gatilhos de revisão explícitos (já atingidos)
- **ADR-002** — domínio Financeiro nasce modular em `financeiro/`; reserva `app/` para extração futura
- **ADR-003** — extração do domínio entrega de `bot.py` avaliada e adiada, com gatilho de revisão próprio
- **ADR-004** (2026-07-02) — gatilho da ADR-003 disparou (bot.py > 3.500 linhas); processo de dois
  agentes (propor + derrubar) reduziu o escopo original pra dispatch table + módulo `nfe/`;
  `fornecedor/`/`obra/`/`comprovante/` adiados com gatilho próprio

Ver `docs/decisoes/` para o texto completo de cada uma.
