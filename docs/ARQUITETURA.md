# Arquitetura do Projeto Laura

> Versão: 2026-07-03 — reflete o estado real do sistema (pós ADR-004: dispatch table + módulo
> `nfe/`; DOCX removido; segurança de `responder_botao()`/`atualizar()`/`atualizar_obra()`
> corrigida; `itens_pedido`/`parcelas_pagamento`/`insumos_sinapi` documentadas; `financeiro/consultas.py`
> e `financeiro/relatorios.py` adicionados)

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
  vinculação (`vincular_nfe`) continuam em `financeiro/lancamento.py`
- **`financeiro/consultas.py`** (2026-07-03) — 4 funções de leitura consolidada, sempre recebendo
  `db_path` explícito (ADR-002): `obter_pedido_completo()`, `obter_consolidado_obra()`,
  `listar_pedidos_pendentes()`, `procurar_item()`. Usadas por `scripts/consultar.py` (CLI) e por
  `financeiro/relatorios.py`
- **`financeiro/relatorios.py`** (2026-07-03) — gera fluxo de pagamentos por obra e relatório
  consolidado em Excel (`data/relatorios/*.xlsx`); ainda sem botão/comando no Telegram, só roda
  chamado manualmente
- **`data/laura.db`** — banco SQLite com oito tabelas (ver seção 3); 9 índices estratégicos
  criados em 2026-07-03, mas só no banco vivo — não persistidos em nenhum `CREATE INDEX` versionado
- **`data/uploads/`** — todo arquivo recebido pelo Telegram cai aqui primeiro (pasta única,
  achatada); é a partir daqui que os documentos são copiados para a pasta certa da obra
- **Claude API** — extração de dados dos documentos; modelo `claude-haiku-4-5-20251001`
- **Playwright Chromium** — geração de PDF do Pedido de Compra 2.0 a partir de HTML; roda headless em memória
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

---

## 5. Estrutura do bot.py

Referências para navegação no arquivo (4.068 linhas):

| Bloco | Referência | O que faz |
|---|---|---|
| Imports e inicialização | `load_dotenv()`, `claude = anthropic...` | Dependências, variáveis de ambiente, cliente Claude |
| Constantes e configuração | `TIPOS`, `DELTAD`, `GGV_ONEDRIVE` | Mapeamentos de tipos, GGVs, dados DeltaD, endereços |
| Domínio — Pedido | `StatusPedido`, `Pedido` | Enum de status e dataclass com 17 campos |
| Integração Claude | `PROMPT` | Prompt de extração estruturada |
| Banco de dados | `init_db()`, `buscar_fornecedor()` | Criação de tabelas, CRUD |
| Geração de PFM | `gerar_pfm()`, `_campo()`, `_itens()` | Helpers de parsing/formatação; define código, salva itens, registra lançamento (não gera documento — ver `_gerar_html_pc()`) |
| Domínio — consulta | `buscar_pedido()`, `mostrar_pedido()` | Pipeline de visualização do pedido |
| Teclados | `parse_resposta()`, `teclado_confirmacao()` | Parse da resposta Claude e botões inline |
| Handlers Telegram | `receber_arquivo()`, `receber_texto()` | Handlers de mensagens |
| Dispatch de callback | `responder_botao()`, `_CB_DISPATCH`, `_cb_*()` | Um único `CallbackQueryHandler`; roteia por dict `acao → função` (ADR-004, 2026-07-02) em vez de if/elif — 59 funções `_cb_*`, cada uma cobrindo os ramos que antes viviam soltos dentro de uma função de 929 linhas |
| Inicialização | `if __name__ == "__main__": ... app.run_polling()` | Registro dos handlers e loop principal — protegido por guard desde 2026-07-02 (importar `bot.py` não inicia mais o bot) |

---

## 6. Limitações Conhecidas

- **Monólito parcial** — `bot.py` com 4.068 linhas, acima do teto da ADR-001 (2.500–3.000).
  ADR-004 (2026-07-02) extraiu dispatch table + módulo `nfe/`; `fornecedor/`/`obra/`/`comprovante/`
  avaliados e adiados com gatilho próprio; `entrega/` continua adiada (ADR-003, motivo não mudou).

- **`responder_botao()` é um único handler** — agora roteia por dispatch table (`_CB_DISPATCH`,
  59 funções `_cb_*`) em vez de if/elif, mas continua sendo um único `CallbackQueryHandler` com um
  único `try/except` — um erro em qualquer ramo ainda aparece como "Erro inesperado" genérico,
  sem isolamento por domínio. `sel_tipo_inicial` continua misturando 4 domínios (entrega, pix,
  nfe, pfm) internamente, não coberto pela divisão em `_cb_*`. Ver ADR-004.

- **`gerar_pfm()` acumula responsabilidades** — grava no banco, cria o lançamento e arquiva em
  disco na mesma função (a geração do documento em si — Word — foi removida em 2026-07-02).

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

---

## 7. Decisões Arquiteturais Registradas

- **ADR-001** — manter o monólito em `bot.py`, com gatilhos de revisão explícitos (já atingidos)
- **ADR-002** — domínio Financeiro nasce modular em `financeiro/`; reserva `app/` para extração futura
- **ADR-003** — extração do domínio entrega de `bot.py` avaliada e adiada, com gatilho de revisão próprio
- **ADR-004** (2026-07-02) — gatilho da ADR-003 disparou (bot.py > 3.500 linhas); processo de dois
  agentes (propor + derrubar) reduziu o escopo original pra dispatch table + módulo `nfe/`;
  `fornecedor/`/`obra/`/`comprovante/` adiados com gatilho próprio

Ver `docs/decisoes/` para o texto completo de cada uma.
