# Estado do Projeto Laura

> Atualizado em: 2026-07-06 (encerramento — nome de arquivo da Lista de Compras padronizado,
> histórico de Listas de Compras por obra, bug de NF-e presa corrigido, e bug de valor do
> pedido não atualizando após revisão corrigido; bot reiniciado em produção com as mudanças)
> Sessão: **Nome de arquivo da Lista de Compras (`GGV03-list-AAAA-MM-DD-resumo-orç/ref.pdf`) +
> campo Resumo editável; "Gerar Lista de Compras" agora encerra a lista (vira registro
> histórico) em vez de reaproveitar pra sempre; picker "📝 Listas de Compras" no Cockpit da
> Obra (buscar por nome/Resumo, reabrir pra editar); NF-e sem candidato ou "Nenhum destes"
> agora descarta o documento — antes ficava presa pra sempre, bloqueando reenvio; revisão de
> pedido (rev01/rev02) agora atualiza `lancamentos` — antes o valor corrigido só aparecia no
> PDF, nunca no Cockpit da Obra/Tela do Pedido**

Continuação da mesma sessão de ontem (Consultoria de Recompra): Dennis pediu para melhorar o
nome dos PDFs da Lista de Compras — hoje saíam como "Lista de Compras - GGV03 - 2026-07-06 -
Referência.pdf", sem jeito de diferenciar listas da mesma obra por assunto. No meio do ajuste,
Dennis perguntou como voltar numa lista já gerada pra editar, filtrando por data ou localizando
por nome — investigação mostrou que esse conceito não existia: cada obra tinha só uma lista
"aberta" pra sempre, sobrescrita a cada geração. As duas perguntas viraram uma fiada só: nome
de arquivo + campo Resumo + mudança de ciclo de vida (cada "Gerar" fecha a lista) + picker de
busca. Duas rodadas de perguntas (`AskUserQuestion`) confirmaram formato exato do nome,
persistência do Resumo, escopo do picker (limite de 10, sem apagar PDFs antigos) antes do
código, como sempre.

**Nome de arquivo padronizado** (`_slug_arquivo`, `_cb_lc_gerar`) — formato confirmado com
Dennis: `{GGV}-list-{AAAA-MM-DD}-{resumo-slug}-{orç|ref}.pdf` (ex:
`GGV03-list-2026-07-06-materiais-eletricos-orç.pdf`). Sem Resumo digitado, cai no slug
`lista-compras`. `resumo TEXT` — nova coluna em `listas_compra`, editável no cabeçalho da Tela
de Conferência (botão "🏷 Resumo", mesmo mecanismo de Endereço/Observações).

**Histórico de Listas de Compras por obra** (`encerrar_lista`, `listar_listas_obra`,
`_cb_obra_listas`, `_cb_lc_abrir`, `_cb_lc_buscar`) — mudança de ciclo de vida: "Gerar Lista de
Compras" agora fecha a lista (`status=encerrada`) em vez de deixá-la `aberta` pra sempre; cada
geração vira um registro histórico próprio. Cockpit da Obra ganhou o botão "📝 Listas de
Compras" → picker com as últimas 10 (data + Resumo + nº de itens); "🔍 Buscar por nome" filtra
pelo Resumo. Tocar numa lista reabre a Tela de Conferência com itens e cabeçalho (Endereço/
Observações/Resumo) carregados do banco; "Gerar" de novo regrava a mesma `lista_id` e fecha de
novo. PDFs de gerações antigas nunca são apagados (CONSTITUICAO.md — "Dados são sagrados") —
cada geração acrescenta novos com a data do dia, decisão confirmada com Dennis.

**Testado**: lógica de banco isolada contra um sqlite temporário (duas gerações da mesma obra
viram registros distintos, filtro por Resumo funciona, reabrir carrega os itens certos) e
`_slug_arquivo()` com acentos/pontuação (ex: "Materiais Elétricos" → "materiais-eletricos").

**Bot reiniciado em produção** (`LAURA_ENV=prod`) a pedido do Dennis ("reinicia") — processo
antigo (PID 69620, rodando desde 08:50) encerrado e um novo subido (PID 75796) já com essas
mudanças. Confirmado: instância única, sem erro no log de inicialização.

**Não concluído**: validar ao vivo no Telegram (nome de arquivo, campo Resumo, picker de
histórico, reabertura de lista antiga) — só testado estruturalmente nesta sessão.

---

## Saúde do Projeto

🟢 Verde

- Fundação concluída.
- Ciclo documental completo: orçamento → PFM → A PAGAR → PIX → PAGO → NF-e vinculada (vínculo de
  NF-e agora independente do status de pagamento — ver Última Fiada Implementada).
- **DOCX removido do fluxo principal** — PC 2.0 (PDF via HTML/Playwright) é o único formato gerado
  desde 2026-07-02. Validado em produção.
- **`bot.py` parcialmente modularizado (ADR-004)**: dispatch table interna em `responder_botao()`
  (929 linhas → 59 funções nomeadas) + módulo `nfe/` extraído. `fornecedor/`, `obra/`,
  `comprovante/` avaliados e adiados com gatilho próprio (ver `docs/decisoes/ADR-004-*.md`).
- **`data/laura.db` (produção) migrado e pronto** — schema estava desatualizado desde antes da
  Fase 4a (faltavam `obras`, `entrega_fotos`, 12 colunas de `lancamentos`); corrigido em 2026-07-01.
- Cadastro de fornecedores limpo e validado contra a Receita Federal (27 registros).
- `documentos`/`lancamentos` de produção zerados por decisão — numeração de PFM reinicia do zero.
- **Fornecedor novo se auto-cadastra a partir do orçamento**, com dado oficial da Receita quando
  disponível. Job periódico (6h) resincroniza **todos** os fornecedores, não só os pendentes —
  razão social/cidade/UF/CNAE sempre atualizam com o dado mais recente; ramo, e-mail e telefone só
  preenchem se ainda estiverem vazios (Receita tem risco real de ficar desatualizada nesses três).
- **Documentos organizados automaticamente na pasta OneDrive de cada obra** — orçamento, PFM,
  comprovante, NF-e e fotos de entrega arquivados com nome e pasta padronizados, sem ação manual.
- **Taxas, impostos e serviços públicos** (CREA, ONR, prefeitura, Copel, Sanepar) passam pelo
  mesmo fluxo de compra — categoria dispensa NF-e (essas entidades não emitem), fatura arquivada
  como fechamento, campos de entrega ocultos no documento gerado.
- **Pagamento parcelado, para todos os pedidos**: cada comprovante vira uma parcela; pedido só
  fecha quando a soma das parcelas atinge o valor total. Recibo (quando aplicável) é por parcela,
  em A5 paisagem com espaço de assinatura — Dennis reenvia assinado, Laura substitui o rascunho.
- Módulo Financeiro: fundação criada (`financeiro/`). Sem funcionalidade nova ainda.
- **Base de referência de insumos SINAPI** (`insumos_sinapi`, 4.365 materiais, preço PR) importada
  via script — tabela solta, ainda **sem nenhum vínculo com `bot.py`** (decisão deliberada).
- **`LAURA_ENV=prod` ativado** — bot rodando em produção pela primeira vez nesta sessão.
  `documentos`/`lancamentos`/`parcelas_pagamento`/`entrega_fotos` zerados de novo (incluindo o
  GGV03-001/Valdir de teste) por decisão explícita, pra começar o cadastro retroativo do zero,
  100% pelo Telegram ao vivo — sem se preocupar com a numeração manual dos arquivos antigos.
- **Cadastro retroativo de GGV03 concluído**: 8 pedidos reais registrados ao vivo pelo Telegram
  (GGV03-001 a 008) — CREA, DeltaD/projetos, DeltaD/gestão (parcelado), ONR, Costaferro, Carlessi,
  Espaço Azul, Eletroluz. 7 pagos, 1 em aberto (gestão, parcial R$2.500 de R$30.000).
- **`docs/LICOES_EXTRACAO.md` criado e alimentado com 10 bugs reais** encontrados durante o
  cadastro ao vivo de hoje — leitura obrigatória antes de mexer em PROMPT/regex, referenciado em
  `docs/PROCESSO.md`.
- **Enriquecimento de fornecedor via Receita ampliado**: além de razão social/cidade/UF, agora
  também traz e-mail, telefone e CNAE (código oficial formatado + descrição da atividade
  econômica principal) — todos os 27 fornecedores já sincronizados retroativamente.
- **Tela de resumo (antes de gerar o pedido) passou a puxar o nome do fornecedor já cadastrado**
  quando só o CNPJ está no documento — antes travava em "Fornecedor não identificado" mesmo com
  o fornecedor já conhecido pela Laura.
- **Job de sincronização com a Receita passou a rodar em todos os fornecedores, sempre** (não só
  pendentes) — três políticas por tipo de campo: razão social/cidade/UF/CNAE sempre atualizam;
  ramo prioriza o texto natural do documento (CNAE só como fallback); e-mail/telefone só entram se
  ainda vazios. Avisa só quando algo muda de verdade.
- **Incidente real corrigido**: um botão "Cancelar" de mensagem antiga do Telegram apagou o
  documento raiz de um pedido já pago (GGV03-007) — `_descartar_documento()` não tinha proteção
  contra apagar documento já vinculado a um pedido de verdade. Corrigido e pedido restaurado a
  partir dos arquivos reais no OneDrive. Ver detalhes na Última Fiada Implementada.
- **Itens de compra estruturados em `itens_pedido`** (resolvido 2026-07-02/03): tabela própria
  (`descricao`, `unidade`, `quantidade`, `valor_unitario`, `valor_total`, `insumo_sinapi_codigo`
  ainda não populado), `scripts/backfill_itens_pedido.py` migrou os pedidos antigos, e
  `python scripts/consultar.py --item <termo>` busca preço de item já comprado sem ler o pedido
  inteiro — resolve o caso real que motivou a fiada (Te de redução 32x25, GGV03-006).
- **Vulnerabilidade de segurança em `responder_botao()` corrigida** (2026-07-03): checagem de
  `DONO_ID` adicionada; `atualizar()`/`atualizar_obra()` agora validam nome de coluna contra
  allowlist antes de montar o SQL dinâmico.
- **Módulo `financeiro/relatorios.py`** (novo, 2026-07-03): gera fluxo de pagamentos por obra e
  relatório consolidado em Excel (`data/relatorios/`) — ainda não tem botão/comando no Telegram,
  só roda chamado manualmente.
- **Domínio de Compras — pipeline completo da Lista de Compras, validado ao vivo**
  (2026-07-03 a 05): política, 15 casos de uso e modelo de domínio documentados; módulo
  `compras/` nasce (ADR-002). Lista de Compras acessível por três caminhos — `/lista` texto,
  `/lista` foto/PDF, botão "📝 Lista de materiais" — que **convergem pra mesma função de
  interpretação**. Pipeline: Camada 1 (interpretação JSON estruturada) → Camada 2 (SINAPI via
  FTS5 + confiança declarada) → Camada 3 (última compra própria, filtro de unidade igual) →
  Tela do Item unificada (view + menu de correção campo a campo, recálculo único ao concluir)
  → cabeçalho editável (Obra/Endereço/Observações) → gravação real em
  `listas_compra`/`lista_compra_itens`. Endereço de entrega reaproveita o mesmo mecanismo de
  presets do Pedido de Compra (`teclado_escolha_endereco`/`_cb_endsel`, princípio
  "Convergência antes de paralelismo" na CONSTITUICAO.md). Testado ao vivo no Telegram —
  "Lista de Compras da Obra GGV03 salva — 8 itens". Ainda sem geração de Pedido de Compra a
  partir da Lista nem vínculo com orçamento. Fluxo orçamento → pedido intocado.
- **"Gerar Lista de Compras" agora fecha a lista** (2026-07-06) — cada geração vira um
  registro histórico próprio (`status=encerrada`) em vez de reaproveitar a mesma lista
  `aberta` pra sempre. PDFs saem com nome padronizado
  (`GGV03-list-AAAA-MM-DD-resumo-orç/ref.pdf`, campo Resumo editável no cabeçalho). Cockpit da
  Obra ganhou o picker "📝 Listas de Compras" (últimas 10, buscar por Resumo, reabrir pra
  editar) — ainda não testado ao vivo no Telegram.
- **Banco otimizado com 9 índices** + `financeiro/consultas.py` (`obter_pedido_completo`,
  `obter_consolidado_obra`, `listar_pedidos_pendentes`, `procurar_item`) + CLI
  `scripts/consultar.py` — consultas de pedido/obra/item em <3ms. Índices existem só no banco
  vivo, não em código (ver Dívidas Técnicas).
- **`_obs()` estava quebrada desde sempre**: só reconhecia "Observações" em linhas separadas, mas
  o formato real é sempre tudo na mesma linha — corrigida pra aceitar os dois formatos.
- **Botões "Cancelar" viraram "← Voltar"**: mesmo padrão em todo lugar; ao clicar num documento já
  virado pedido, abre o cockpit direto, sem tela intermediária.

---

## Versão Atual

**v0.14.0** — Lista de Compras: nome de arquivo padronizado (slug + data + Resumo) + campo
Resumo editável; "Gerar" agora encerra a lista (histórico por obra) + picker "📝 Listas de
Compras" (buscar por nome, reabrir pra editar) no Cockpit da Obra

**v0.13.0** — Lista de Compras: Consultoria de Recompra (painel "Você já comprou isso" +
"Repetir esta compra") na Tela do Item; `LAURA_ENV=prod` reativado — Laura em produção real

**v0.12.0** — Lista de Compras: PDF em 2 variantes (referência interna / orçamento pra
fornecedor), enriquecimento de descrição genérica (histórico > SINAPI > original), bug de
duplicação ao confirmar corrigido

**v0.11.0** — Lista de Compras: correção campo a campo com recálculo único (Tela do Item
unificada), cabeçalho editável (Obra/Endereço/Observações), endereço de entrega convergido
com o Pedido de Compra — pipeline validado ao vivo no Telegram

**v0.10.0** — Módulo de Compras: Lista de Compras com interpretação por IA (texto/foto/PDF),
correspondência SINAPI, referência de última compra própria, tela de conferência em 3 níveis
e gravação real no banco

**v0.9.0** — DOCX removido (PC 2.0 é o único formato), ADR-004 (dispatch table + módulo `nfe/`),
recibo com texto narrativo e valor por extenso, matching de PIX/NF-e sem corte artificial de lista

---

## Funcionalidades Disponíveis

- Recebimento de foto e PDF via Telegram
- Seleção manual do tipo de documento antes da análise por IA
- Extração de dados por IA (Claude haiku-4-5) após tipo confirmado
- Edição de qualquer campo extraído antes de confirmar
- Seleção e correção manual de tipo e GGV
- Geração de PFM em PDF numerado (ex: GGV03-009) — DOCX não é mais gerado
- Salvamento automático do PFM na pasta OneDrive do GGV
- Criação de lançamento A PAGAR no banco
- Consulta de pedido digitando o código (ex: GGV03-009)
- Tela do pedido: dados financeiros, arquivos vinculados e histórico resumido
- Identificação de candidatos A PAGAR ao receber comprovante PIX — lista completa, ordenada por
  relevância (não só os 3 melhores), com total pendente exibido
- Confirmação de pagamento com botões por candidato
- Marcação de lançamento como PAGO com gravação de valor, data e identificador
- Proteção contra duplo pagamento e reutilização do mesmo comprovante
- Recebimento e vinculação de NF-e a qualquer pedido sem NF-e (independente do status de
  pagamento — nota pode ser emitida antes de o pedido estar totalmente pago)
- Revisão do Pedido de Compra com geração de arquivo rev01, rev02...
- Cockpit do pedido com número da NF-e, botões de comprovante e nota
- Registro de entrega: foto, /entrega, botão no cockpit, observação com sugestões
- Edição de entrega: mudar obs, trocar/remover foto, apagar entrega completa
- Entrega com múltiplas fotos por pedido, cada uma com legenda obrigatória
- Galeria de arquivos da entrega: visualizar (ícone por tipo) e remover individualmente
- Navegação padronizada: `← Voltar` e `✖ Fechar` em todos os menus, incluindo Ajuda e Obras
- Auto-cadastro de fornecedor desconhecido ao gerar PFM, validado contra a Receita Federal
  (razão social, cidade, UF); sincronização periódica em segundo plano para os que falharam na hora
- Orçamento, PFM, comprovante, NF-e e foto de entrega arquivados automaticamente na pasta OneDrive
  da obra (`04 Compras`, `01 Controle financeiro`, `05 Entrega`), com nome padronizado
- Modo teste isolado via `LAURA_ENV=test`
- Lista de Compras (`/lista` ou botão "📝 Lista de materiais"): interpretação por IA de texto,
  foto ou PDF; correspondência com SINAPI (confiança declarada, preço convertido pra unidade
  comercial); referência de última compra própria (filtro de unidade igual); enriquecimento
  de descrição genérica (sugestão do histórico próprio ou SINAPI, com botão "Usar sugestão");
  Tela de Conferência (visão rápida por item) → Tela do Item (view + menu de correção);
  correção campo a campo (Produto, Fabricante, Código, Quantidade, Unidade, Observações) com
  recálculo único ao "Concluir edição"; "Reinterpretar item" reservado a itens em fallback;
  análise técnica disponível por item ou pra lista inteira; cabeçalho editável (Obra — presets
  Obra/Casa/Escritório/Chácara/Outro, mesmo mecanismo do Pedido de Compra; Endereço; e
  Observações gerais, e Resumo — texto curto que nomeia os PDFs, opcional); gravação real da
  lista no banco ao confirmar, substituindo (não duplicando) itens de confirmações anteriores
  e **fechando a lista** (vira registro histórico); **PDF gerado automaticamente em 2
  variantes**, nome padronizado `GGV03-list-AAAA-MM-DD-resumo-orç/ref.pdf` — referência interna
  com preço e versão em branco pra pedir orçamento a fornecedores, ambas arquivadas em
  `04 Compras/00 Orçamentos/` (ainda sem gerar Pedido de Compra a partir da Lista); histórico de
  listas por obra acessível via Cockpit da Obra → "📝 Listas de Compras" (buscar por Resumo,
  reabrir uma lista antiga pra continuar editando)

---

## Última Fiada Implementada

**Pedido — Bug real corrigido: valor não atualizava após revisão** *(2026-07-06, mesmo dia,
achado ao vivo pelo Dennis testando o Cockpit da Obra)*

Dennis corrigiu o valor do pedido GGV03-012 (item com preço errado) via "Revisar", mas o
Cockpit da Obra continuou mostrando o valor antigo (R$ 745,00 em vez de R$ 820,00).

**Causa raiz**: `gerar_pfm()` tem dois caminhos — geração nova (chama `registrar_lancamento()`,
grava fornecedor/valor/data no lançamento) e revisão (`pfm_codigo_override`, botão "Revisar" →
rev01/rev02). O caminho de revisão nunca executava esse passo — o PDF saía com o valor
recalculado, mas `lancamentos` (fonte do Cockpit da Obra e da Tela do Pedido) ficava travado no
valor da geração original pra sempre. Bug de programa (critério do próprio Dennis: "conserta
uma vez, resolvido pra sempre"), não de IA.

**Corrigido**: revisão agora também executa `UPDATE lancamentos SET fornecedor=?, valor=?,
data_prevista_entrega=?` com os dados recalculados — nunca mexe em `status`, `valor_pago`,
NF-e ou qualquer campo que só a jornada de pagamento grava. Verificado no banco real antes de
corrigir (`pfm_numero=12`, `rev_numero=1`, pagamento já registrado em R$ 820,00 — só o campo
`valor` do lançamento estava desatualizado, criando uma inconsistência entre valor do pedido e
valor pago). GGV03-012 corrigido manualmente pra refletir o valor certo; bot reiniciado (PID
50212) com a correção de código, válida pra qualquer pedido revisado daqui pra frente.

---

**NF-e — Bug real corrigido: documento preso pra sempre quando não vincula** *(2026-07-06,
mesmo dia, achado ao vivo testando o bot recém-reiniciado)*

Dennis enviou uma NF-e real ("Verschoor 15.pdf"), ela não vinculou a nenhum pedido, e reenviar
o mesmo arquivo travou em "Este arquivo já foi recebido." — pediu ideia antes de qualquer
código (`me informe antes de executar qq código`).

**Causa raiz**: comparando com o fluxo equivalente de comprovante PIX (que já descarta o
documento automaticamente quando não acha candidato), o fluxo de NF-e não fazia isso em nenhum
dos dois casos — zero candidatos ou usuário tocando "Nenhum destes". Pior: o botão "Nenhum
destes" nem carregava o `doc_id` no callback (`nfe_cancelar`, sem parâmetro), então fisicamente
não tinha como descartar nada. Resultado: todo documento de NF-e que não vincula fica pra
sempre em `documentos`, com o hash bloqueando reenvio do mesmo arquivo.

**Diagnóstico confirmado no banco** (leitura, antes de qualquer mudança): doc_id 40
("Verschoor 15.pdf"), tipo `nota_fiscal`, obra GGV03, `status=recebido`, `pfm_numero=NULL`, sem
nenhum `lancamentos.doc_id_nfe` apontando pra ele — confirmado órfão e seguro de descartar.

**Corrigido** (aprovado por Dennis: "ja resolve tudo"):
- `nfe/nfe.py::teclado_candidatos_nfe()` — botão "Nenhum destes" agora carrega o `doc_id`
  (`nfe_cancelar:{doc_id}`)
- `bot.py::_cb_nfe_cancelar()` — chama `_descartar_documento(doc_id)` e avisa "Arquivo
  descartado — pode reenviar depois de corrigir o pedido." (mesma mensagem do fluxo PIX)
- `bot.py::_cb_sel_tipo_inicial()` (ramo `nota_fiscal`) — descarta automaticamente quando
  `buscar_candidatos_nfe()` não acha nenhum candidato, mesmo padrão já usado por
  `comprovante_pix`
- doc_id 40 descartado manualmente (arquivo e registro removidos) pra destravar o reenvio

**Fora de escopo, por decisão já registrada antes**: os três pontos de entrada de confirmação
de documento (`_cb_sel_tipo_inicial`, `_cb_set_tipo`, `_cb_ok`) continuam divergentes —
`_cb_ok()` nem tem ramo `nota_fiscal` (cai no `else` genérico, "Confirmado: Nota Fiscal", sem
oferecer matching). Esse problema maior já está registrado como dívida técnica/"Motor de
Interpretação e Classificação de Documentos" em `docs/ROADMAP.md`; não expandido aqui.

**Testado**: `py_compile` limpo; confirmado no banco real que doc_id 40 foi removido (registro
e arquivo físico); bot reiniciado em produção (PID 79768) com a correção.

---

**Módulo de Compras — Nome de arquivo padronizado + campo Resumo + histórico de Listas de
Compras** *(2026-07-06, mesmo dia da Consultoria de Recompra)*

Dennis pediu pra melhorar o nome dos PDFs gerados pela Lista de Compras (hoje saíam como
"Lista de Compras - GGV03 - 2026-07-06 - Referência.pdf") e, no meio do ajuste, perguntou como
voltar numa lista já gerada pra editar — filtrando por data ou localizando por nome. As duas
viraram uma fiada só, com duas rodadas de `AskUserQuestion` confirmando o desenho antes do
código (formato exato do nome, persistência do campo Resumo, limite do picker, o que fazer com
PDFs de gerações antigas).

**Nome de arquivo + campo Resumo** (`_slug_arquivo`, `_cb_lc_gerar`): formato
`{GGV}-list-{AAAA-MM-DD}-{resumo-slug}-{orç|ref}.pdf` (ex:
`GGV03-list-2026-07-06-materiais-eletricos-orç.pdf`); sem Resumo digitado, cai em
`lista-compras`. `resumo TEXT` — nova coluna em `listas_compra`, editável no cabeçalho da Tela
de Conferência (botão "🏷 Resumo"), mesmo mecanismo já usado por Endereço/Observações
(`_CAMPOS_LISTA_GERAL`).

**Histórico de Listas de Compras por obra** (`encerrar_lista`, `listar_listas_obra`,
`_cb_obra_listas`, `_cb_lc_abrir`, `_cb_lc_buscar`): investigação mostrou que o conceito de
"lista antiga" não existia — cada obra tinha só uma lista `aberta` pra sempre, sobrescrita a
cada "Gerar Lista de Compras". Mudança de ciclo de vida: "Gerar" agora fecha a lista
(`status=encerrada`); cada geração vira um registro histórico. Cockpit da Obra (já existia,
abre digitando o código da obra) ganhou o botão "📝 Listas de Compras" → picker com as últimas
10, mais recente primeiro (data + Resumo + nº de itens); "🔍 Buscar por nome" filtra pelo
Resumo (`LIKE`). Tocar numa lista reabre a Tela de Conferência com itens e cabeçalho
(Endereço/Observações/Resumo) carregados do banco; "Gerar" de novo regrava a mesma `lista_id`
(via novo `ctx.user_data["lista_id_edicao"]`) e fecha de novo — não cria um registro duplicado.
PDFs de gerações antigas nunca são apagados (CONSTITUICAO.md — "Dados são sagrados"): cada
geração só acrescenta, com a data do dia.

**Testado**: lógica de banco isolada contra um sqlite temporário — duas gerações da mesma obra
viram registros distintos (`criar_ou_buscar_lista_aberta` sempre cria novo, já que nada fica
`aberta` de verdade depois do "Gerar"), filtro por Resumo funciona, reabrir carrega os itens
certos; `_slug_arquivo()` testado com acentos/pontuação ("Materiais Elétricos" →
"materiais-eletricos").

**Bot reiniciado em produção**, a pedido do Dennis ("reinicia"): processo antigo (PID 69620,
rodando desde 08:50) encerrado, novo subido (PID 75796) já com essas mudanças. Confirmado
instância única e sem erro no log de inicialização.

**Não concluído**: validar ao vivo no Telegram — nome de arquivo, campo Resumo, picker de
histórico e reabertura de lista antiga só testados estruturalmente nesta sessão, nunca
clicados de verdade.

---

**Módulo de Compras — Consultoria de Recompra** *(2026-07-06)*

Item #1 do "Objetivo da Próxima Sessão" de ontem — mockup em texto validado com o Dennis
antes do código, como sempre: painel "Você já comprou isso" (fabricante/descrição real +
fornecedor + tempo decorrido, não só um preço solto) e comparação com a referência SINAPI
atual, sem limiar de tempo/variação pra decidir "não vale a pena" (Dennis: "sem limites por
enquanto" — a decisão continua humana). Botão "🔁 Repetir esta compra" aplica a descrição
histórica no rascunho, mesmo mecanismo de "Concluir edição" já existente.

Implementado: `_linhas_recompra()` (painel), `_preco_sinapi_item()` (extraído de
`_melhor_referencia_preco` — a Consultoria precisa do preço SINAPI mesmo quando também há
referência própria, que venceria naquela função), `_cb_lc_repetircompra()` (compartilha
`_aplicar_descricao_no_rascunho()` com `_cb_lc_usarsugestao()` de ontem — mesma ação,
origem da descrição diferente). Painel tem prioridade sobre a sugestão de descrição de
ontem quando há histórico (evita mostrar as duas ao mesmo tempo); sem histórico, cai no
comportamento de ontem (sugestão SINAPI se a descrição for genérica).

**Achado no caminho**: uma data real do banco ("25/junho/2026 às 12:41:40") não era
reconhecida por nenhum parser existente. Escrito `_parse_data_qualquer()` — parser único
(numérico, "DD/mês-nome/AAAA", "DD de mês de AAAA", ISO; retorna `None` em vez de adivinhar
quando não reconhece); `_data_para_arquivo()` refatorado pra usá-lo, sem mudar comportamento.

**Testado**: 8 cenários — parser de data (inclusive o formato quebrado real),
`_tempo_decorrido`, painel completo com/sem comparação SINAPI, fluxo "Repetir esta compra"
→ "Concluir edição" com recálculo real (dados reais do banco de teste), fallback pro
comportamento de ontem sem histórico.

**`LAURA_ENV=prod` ativado** — Dennis: "pode colocar no modelo de produção". Verificado
antes de trocar: banco real com 11 lançamentos e as 4 obras GGV, `listas_compra` ainda
vazia. Schema desatualizado desde antes de ontem (faltavam `fabricante`, `codigo`,
`sinapi_confianca`, `sinapi_preco_equivalente`, `endereco_entrega`, `observacoes`) —
`init_db()` aplicou tudo via ALTER seguro, sem tocar em dado existente.

**Não concluído**: validar a Consultoria de Recompra ao vivo em produção — só testada com
objetos simulados e dados reais fora do Telegram nesta sessão. Comparar fornecedores
diferentes e filtros ficam pra depois, por decisão explícita do Dennis.

---

**Módulo de Compras — PDF da Lista de Compras + enriquecimento de descrição + correção de
duplicação** *(2026-07-05, mesmo dia da Camada 4b)*

Continuação direta da Camada 4b, na mesma sessão. Dennis pediu a próxima etapa ("gerar a
Lista de Compras em PDF") explicitamente sem definir a implementação — pediu exploração da
infraestrutura já existente (Pedido de Compra) antes de qualquer código, seguindo o mesmo
padrão de planejamento já estabelecido.

**Geração de PDF, duas variantes do mesmo documento** (`_gerar_html_lista(lista_id,
com_precos)`, reaproveita `_PC_CSS`/`_html_para_pdf` do Pedido de Compra sem CSS novo):
- **"Referência"** (uso interno) — mostra preço unitário/total calculado a partir da
  referência SINAPI/própria já existente
- **"Orçamento"** (pra encaminhar a fornecedores via WhatsApp) — mesmos itens, campos de
  preço em branco (linha pra o fornecedor preencher), pedido de Dennis: "a ideia é a partir
  da lista pedir propostas de orçamento para os fornecedores" — nunca revela a própria
  referência de preço numa negociação que ainda não começou (mesmo espírito do Princípio 4
  da Política de Compras)
- Ambos gerados automaticamente ao confirmar "Gerar Lista de Compras", arquivados em
  `04 Compras/00 Orçamentos/` (mesma pasta do orçamento recebido do fornecedor, a pedido
  explícito do Dennis)

**Bug de dados corrigido no caminho**: `sinapi_confianca`/`sinapi_preco_equivalente` (Camada
2) nunca eram persistidos em `lista_compra_itens` — sem eles, reler a lista do banco (pro
PDF) perdia a conversão de preço pra unidade comercial em itens que precisaram dela. Mesma
classe de bug já corrigida antes com fabricante/código.

**Camada de enriquecimento de descrição genérica** — Dennis: "a Laura não deve apenas
interpretar a lista do jeito que eu escrevi... deve me ajudar a melhorar a qualidade técnica
da Lista de Compras." Exemplos reais que motivaram: "Areia", "Brita", "Tijolos", "Cimento",
"Cal" chegam genéricos demais pra cotação séria.

- Camada 1 ganhou o campo `descricao_generica` — julgamento da própria IA ("um comprador
  conseguiria pedir orçamento com isso?"), não regra mecânica de contagem de palavras
  (Dennis foi explícito: "não quero engessar demais")
- Prioridade como orientação, não regra cega: histórico real da empresa primeiro (mais
  confiável pro vocabulário real da obra); SINAPI só como apoio quando o histórico não
  resolve, e só com confiança alta/média; descrição original se nada servir ou se a
  sugestão for igual à atual (evita loop depois de aceitar uma vez)
- Não reaproveita busca nova — usa os candidatos que Camada 2 (SINAPI) e Camada 3
  (histórico) já encontram; só faltava capturar a descrição do item histórico encontrado
  (antes só o preço era aproveitado)
- Tela de Conferência: alerta 🟡 "Descrição genérica — sugestão disponível"
- Tela do Item: "💡 Descrição genérica. Sugestão: Areia média lavada (histórico)" + botão
  "✅ Usar sugestão" — aplica no rascunho, mesmo mecanismo de "Concluir edição" já existente,
  nenhuma chamada de IA extra
- Análise Técnica: quando histórico venceu, mostra a alternativa do SINAPI como "outra
  possibilidade" — só aparece se realmente útil, não polui a tela principal
- Testado com IA real: "Areia" → sugestão do histórico; "Brita 1" (sem histórico) → sugestão
  do SINAPI; "Cimento CP II 50kg Caue"/"Tijolo cerâmico 6 furos 9x19x19" → reconhecidos como
  já específicos, sem sugestão forçada

**Bug real de duplicação encontrado ao vivo no Telegram**: confirmar "Gerar Lista de
Compras" duas vezes na mesma lista aberta (ex: testar, corrigir, testar de novo) duplicava
todos os itens — `adicionar_item()` só insere, nunca substitui. Confirmado direto no banco:
lista GGV03 com 10 itens ativos, sendo 5 genéricos (09:37) e os mesmos 5 corrigidos/
enriquecidos (11:17). Corrigido com o mesmo padrão de `_salvar_itens_pedido()` (Pedido de
Compra): cada confirmação reflete a lista inteira vista agora, removendo (soft-delete, via
`remover_item()` já existente) os itens ativos anteriores antes de gravar os novos —
histórico preservado, nunca apagado de verdade. Dados de teste do Dennis corrigidos
manualmente pra refletir o estado correto.

**Investigação ao vivo — 3 casos reais testados por Dennis, diagnosticados mas SEM
correção de código ainda** (mudança de prioridade aconteceu antes de implementar):

1. **Cal Hidratada** — SINAPI achou o código certo (1106, Alta confiança), mas a Laura não
   converteu KG→SC porque não sabia o peso do saco (embalagem não informada) — recusa
   correta, mas a Tela do Item esconde a explicação (a `observacoes` do item, que já
   continha o motivo, não aparece nesse nível; `_referencia_e_correspondencia` também
   esconde "Correspondência: Alta confiança" quando o preço não pôde ser calculado, como se
   nada tivesse sido encontrado). **Correção proposta, não implementada**: mostrar
   observações na Tela do Item; separar "achou correspondência" de "calculou preço".
2. **Brita** — bug real de busca: pra "Brita" sozinha, Camada 1 gerou
   `termo_busca_sinapi: "brita"` (repetiu a palavra, não traduziu pro vocabulário técnico).
   Buscar "brita" no FTS5 traz "concreto usinado com brita" (errado); só "pedra britada"
   acha os 6 candidatos certos (Pedra Britada N.0 a N.3) que genuinamente existem no
   SINAPI. **Correção proposta, não implementada**: reforçar o prompt da Camada 1 pra
   traduzir termo coloquial → vocabulário técnico SINAPI.
3. **Tijolo** — Claude escolheu um candidato entre 6 bem diferentes (maciço comum,
   aparente, refratário, com furos, tamanhos diferentes) com "Alta confiança", mas a
   própria `observacoes` do item já dizia "tipo e dimensões devem ser confirmados" —
   confiança devia ter sido rebaixada, não "alta". Dennis: "poderia me dar mais opções, mas
   tive que escolher esta."

**Conversa importante — IA vs Programa, registrada porque muda a forma de priorizar daqui
pra frente**: Dennis questionou se valia a pena continuar "brigando" caso a caso com
problemas de vocabulário SINAPI. Esclarecido: bugs de **programa** (como os dois primeiros
achados de Cal Hidratada) são "conserta uma vez, resolvido pra sempre"; julgamento de **IA**
(Brita, Tijolo) nunca chega a "resolvido pra sempre" — melhora com prompt melhor, mas
convive com margem de erro residual, por natureza. Ofereci um glossário determinístico de
sinônimos SINAPI (programa, não IA) como mitigação — **Dennis rejeitou explicitamente**:
"não é problema meu hoje... já existe uma biblioteca com sinônimos de materiais de
construção... SINAPI é ref[erência, só uma entre várias]." Ver Decisões Recentes.

**Mudança de prioridade pra próxima fiada** — Dennis: "o que eu preciso de mais ajuda é pra
repetir a compra... se sinto que não vale mais a pena, principalmente por preço, ou indicar
outro produto (fabricante e modelo, fornecedor ou tipo)." Não é sobre vocabulário SINAPI —
é evoluir a Camada 3 (histórico próprio) de "achar um preço de referência" pra "consultora
que ajuda a decidir repetir ou trocar". Ver Próximas Fiadas/ROADMAP — vira a prioridade #1,
com escopo ainda a desenhar (mockup em texto antes de qualquer código, como sempre).

**Não concluído**: os 3 fixes de exibição diagnosticados (Cal/Brita/Tijolo) ficam pendentes,
sem prioridade definida ainda frente à consultoria de recompra; teste do fluxo de dedupe
ao vivo no Telegram (só testado com objetos simulados nesta sessão).

---

**Módulo de Compras — Camada 4b: correção campo a campo + cabeçalho editável + convergência
do endereço de entrega** *(2026-07-05)*

Continuação direta de ontem: item #1 do "Objetivo da Próxima Sessão" era validar o pipeline
completo ao vivo no Telegram; item #2 era implementar a edição campo a campo. Os dois
aconteceram juntos, em várias rodadas de mockup em texto validadas com o Dennis antes de cada
pedaço de código (Constituição — "IA é parceira": Dennis define o quê e o porquê).

**Desenho negociado em 3 rodadas, não em uma tacada só:**
1. Proposta inicial: item picker → "Corrigir campos" (tela separada) → escolher campo →
   digitar → salvar imediatamente por campo.
2. Dennis: "recalcular somente ao salvar" — rascunho por trás da tela, sem chamada de IA a
   cada campo; só uma chamada quando o usuário concluir.
3. Dennis revisou a Tela do Item inteira: "ela ainda mistura visualização, análise técnica e
   edição... deve virar muito mais um menu de edição do que uma ficha técnica." Redesenho
   final: Tela do Item = view + menu numa tela só (sem tela intermediária de "Corrigir
   campos"); Análise Técnica sai pra tela própria, acessada por botão.

**Implementado (`_texto_tela_item`/`_teclado_item_tela`/`_cb_lc_campo`/`_cb_lc_concluir`):**
cada campo (📝 Produto, 🏷 Fabricante, 🔢 Código, 📦 Quantidade, 📏 Unidade, 🗒 Observações) é
um botão direto; tocar abre um prompt isolado ("Valor atual" + instrução), digitar volta
sozinho pra Tela do Item com um rascunho atualizado. Enquanto há rascunho, Referência/
Correspondência somem da tela (nunca mostradas como se ainda fossem válidas) e aparece
"⚠️ Alterações pendentes"; o botão "⬅ Voltar" vira "💾 Concluir edição", que recalcula Camada
2+3 **uma única vez** (não importa quantos campos foram corrigidos) e volta direto pra lista
já atualizada. `_preparar_tela_item()` compara o rascunho ao item real pra decidir "pendente"
— abrir um campo e voltar sem digitar nada não marca pendência falsa.

**"Reinterpretar item" saiu da tela principal** (Dennis: "se o usuário fica em dúvida entre
dois botões, provavelmente um deles não deveria estar na tela principal") — "Concluir edição"
já recalcula tudo sozinho, então reinterpretar do zero via texto livre virou redundante pro
fluxo comum. Continua existindo só quando o item veio em fallback (string, não interpretado),
onde é o único caminho possível — verificado que não haveria como corrigir esses itens sem
ele.

**Análise técnica por item, nova** (`_texto_item_tecnico`/`_cb_lc_tecnicoitem`): extraída de
`_texto_analise_tecnica` (lista inteira) via `_linhas_analise_item()` compartilhada — sem
duplicar a formatação de SINAPI/referência/confiança. Sempre reflete o item já confirmado,
nunca o rascunho pendente.

**Botão "📍 Definir obra"** — Dennis reportou "está faltando o botão para escolher a obra"
quando `ggv` ainda não identificado; `_cb_lc_defobra`/`_cb_lc_setobra` abrem a lista real de
obras cadastradas (`_listar_obras()`, mesma fonte do `/obras`), não a lista `GGVS` antiga.

**Cabeçalho da Lista de Compras ganhou 3 campos editáveis** (Dennis: "Obra (obrigatório),
Endereço de entrega (herdado da obra, mas editável), Observações gerais da compra (opcional),
todos devem ser editáveis"): `listas_compra` ganhou duas colunas (`endereco_entrega`,
`observacoes`) via `atualizar_lista()` — só grava se o campo foi tocado nesta sessão, pra
nunca apagar um valor já salvo ao reabrir uma lista existente sem re-editar.

**Convergência do endereço de entrega com o Pedido de Compra** — a primeira versão da edição
de endereço da Lista era um prompt de texto livre simples. Dennis perguntou se eu já tinha
considerado que o Pedido de Compra já tem exatamente esse conceito (`teclado_endereco`/
`_cb_end`, presets Obra/Casa/Escritório/Chácara/Outro) — não tinha checado. Primeira correção
extraiu só `_opcoes_endereco()`/`_resolver_endereco()` (funções puras), mas teclado e callback
continuaram duplicados; Dennis testou com uma pergunta concreta ("se eu adicionar 'Depósito'
amanhã, em quantos lugares preciso mexer?") que expôs a convergência incompleta. Unificação
final: um único `teclado_escolha_endereco()` + um único `_cb_endsel()`, usados pelos dois
domínios — bifurcando só no destino final da gravação (documento vs `ctx.user_data`), que é
diferença real de domínio, não duplicação evitável. Testado com escrita real no banco pros
dois caminhos, comportamento do Pedido de Compra inalterado.

**Novo princípio permanente**: `docs/CONSTITUICAO.md` ganhou "Convergência antes de
paralelismo", formalizando a lição acima — com o teste prático "quantos lugares mexo se
adicionar uma opção nova?" como critério de verificação.

**Housekeeping de UX**: todo prompt de texto livre da Lista de Compras (campo do item,
reinterpretar, campo do cabeçalho) ganhou botão "← Voltar", incluindo as mensagens de retry de
validação (quantidade inválida, descrição em branco) — pedido do Dennis aplicado
sistematicamente, não só no primeiro lugar onde apareceu.

**Validado ao vivo no Telegram**: pipeline completo, ponta a ponta, confirmado pelo Dennis —
"Lista de Compras da Obra GGV03 salva — 8 itens".

**Não concluído**: edição do endereço/observações não testada ainda com o fluxo de "Gerar"
reabrindo uma lista já existente (só testado com objetos simulados); geração de Pedido de
Compra a partir da Lista de Compras; vínculo com orçamento.

---

**Módulo de Compras — Redesenho conceitual + Camada 1 (interpretação)** *(2026-07-04)*

Sessão de continuação: retomar o teste ao vivo das Fiadas 1/2 de ontem. O teste (foto real de
material hidráulico, 11 itens Tigre) expôs que a saída não era o que Dennis queria, e a
conversa evoluiu pra um redesenho conceitual completo, não um ajuste pontual.

**O redesenho:** a Lista de Compras deve nascer com a mesma lógica de segurança do Pedido de
Compra — IA interpreta o que for enviado (texto, foto ou PDF) de uma vez só, tenta padronizar
cada item contra o SINAPI, e só grava depois de conferência/edição humana. Princípio que
emergiu da conversa, agora orientando a arquitetura: **"Entradas diferentes podem existir.
Processos diferentes não. Sempre que o resultado esperado for o mesmo, a implementação deve
convergir para um único fluxo interno."**

**Checagem de infraestrutura antes de codar** (a pedido do Dennis, antes de qualquer camada
nova): medido contra `data/laura.db` real — busca por `LIKE '%termo%'` em `insumos_sinapi`
(4.365 linhas) já é rápida (~1-2ms), o problema real é precisão, não performance (`'tubo pvc
25'` como frase inteira dava zero resultados). Aplicado: tabela virtual `insumos_sinapi_fts`
(FTS5, busca por palavra). Achado durante a implementação: `DELETE FROM` numa tabela FTS5
externa é instável nesta versão do SQLite (3.50.4) — "database disk image is malformed" de
forma intermitente, sem corrupção real (`PRAGMA integrity_check` sempre "ok"); resolvido com
`DROP`+`CREATE`+`INSERT`, nunca `DELETE` na tabela virtual. Diagnóstico rápido do resto do
projeto: só `procurar_item()` usa `LIKE` de verdade; achado um índice morto
(`idx_fornecedores_cnpj`, nunca usado pela query real — confirmado com `EXPLAIN QUERY PLAN`,
irrelevante com 31 linhas, registrado como dívida menor).

**Snapshot histórico, dois pedidos complementares do Dennis:** `lista_compra_itens` ganhou 11
colunas — snapshot SINAPI (código, descrição, unidade, preço, mês de referência) e snapshot
da referência interna da Laura (preço, data, fornecedor, origem, grau de confiança) — ambos
congelados no momento da confirmação, nunca recalculados depois. Motivo declarado pelo Dennis:
não é só "não perder o preço antigo" — é a base de uma série histórica de 4 pontos por item
(SINAPI da época, referência da Laura da época, preço negociado, SINAPI atual) que no futuro
vai responder perguntas como "pra cimento CP-II, o preço negociado ficou 3% abaixo do SINAPI
nas últimas 28 compras" e até medir a confiabilidade do próprio SINAPI como referência de
mercado. Registrado em memória (`project_snapshots_historicos_compras`). Verificado no código
real que `adicionar_item()` ainda não gravava nenhum desses campos (função escrita antes
dessa decisão existir) — corrigido como parte da própria fiada, não como pendência futura.

**Camada 1 — Interpretação, implementada e testada:** `PROMPT_INTERPRETAR_LISTA` (dedicado,
não passa pela classificação compartilhada do orçamento) + `_interpretar_lista_texto()`/
`_interpretar_lista_arquivo()`, chamadas pelos dois pontos de entrada (`/lista` e botão "📝
Lista de materiais" no menu de documento) — testado estruturalmente que são a mesma função,
não duas cópias. `/lista` muda de papel: não abre mais edição item a item, pede "Envie a
lista — texto, foto ou PDF" e interpreta tudo de uma vez.

**Mesmo dia, reescrita pra saída JSON estruturada:** teste com tabela real (8 itens de
acabamento) expôs que pedir uma linha de texto por item forçava a IA a achatar a tabela antes
de responder — quantidade virando "1" quando a coluna dizia outro valor, código de referência
alterado ("72707/72745" → "27707/72745"). Corrigido: `PROMPT_INTERPRETAR_LISTA` reescrito em
procedimento (detectar tabela → linhas → colunas separadas) + regras (nunca inventar
quantidade/unidade, código copiado literalmente, prioridade coluna > texto lido >
interpretação); saída virou array JSON; `_itens_lista_materiais()` usa `json.loads()` com
fallback defensivo no lugar do regex antigo. Documentado como Lição #13 (nova "Família C" de
bug: formato de saída não tem a forma do dado de origem). Validado contra a tabela real como
gabarito: 8/8 com texto colado, 5/8 perfeitos com a foto real — os 3 restantes com
imperfeição de campo, mas nenhum inventando valor (pior caso retornou `null`, não "1 SC").
Dennis aceitou esse nível de qualidade pra seguir; refino adicional fica pra depois, se
necessário.

**Mesmo dia, Camada 2 — candidatos SINAPI:** `_candidatos_sinapi()` (busca FTS5) +
`_adicionar_correspondencia_sinapi()` (uma chamada ao Claude decide a lista inteira), chamadas
de dentro das próprias funções de interpretação — mesma convergência da Camada 1. Primeiro
teste achou um falso positivo real: "Revestimento Cerâmico" casado com código de porcelanato
(categoria adjacente, preço bem diferente). Dennis pediu grau de confiança (nunca esconder
incerteza) e "entender o produto antes de procurar a referência" — mas como raciocínio dentro
do prompt de decisão, não como atributos persistidos: "não quero criar uma estrutura
permanente antes de comprovar seu valor." Implementado: confiança alta/média/baixa/nenhuma,
regra contra categoria adjacente, equivalência de unidade (250 SC de cimento 50kg → 12.500 KG)
calculada só com certeza. Testado contra o mesmo gabarito: falso positivo desapareceu com o
texto colado; com a foto real o mesmo erro ainda aconteceu, mas rotulado "Média confiança" em
vez de "Alta" — de confiante-e-errado pra sinalizado-como-incerto, mesmo padrão da Camada 1.
Visão de longo prazo (atributos técnicos completos, catálogo próprio da Laura) registrada em
`docs/ROADMAP.md`, deliberadamente não implementada como entidade.

**Mesmo dia, correção de direção da equivalência de unidade:** Dennis revisou a Camada 2 recém
implementada e corrigiu o sentido da conversão — a primeira versão convertia a quantidade do
item pra unidade do SINAPI ("Equivalência: 12.500 KG"); a unidade comercial (como se compra e
negocia) não pode mudar em lugar nenhum, nem na lista, nem no pedido, nem na negociação. Regra:
"A Laura nunca converte o item comercial para a unidade do SINAPI. A Laura converte a
referência do SINAPI para a unidade comercial do item." Corrigido: `PROMPT_ESCOLHER_SINAPI`
agora pede `preco_equivalente_unidade_comercial` (preço do SINAPI convertido pra R$/unidade
comercial); exibição virou "Referência SINAPI: R$ 40,00 / SC" com "(equivalente a
R$ 0,80/KG)" como contexto secundário. Testado e corrigidos dois bugs reais expostos no
processo: o preço do candidato SINAPI nunca era enviado ao Claude (sem ele a conversão é
impossível) e o parsing do JSON quebrava quando Claude acrescentava justificativa em texto
livre após o array (trocado por extração via regex do bloco `[...]`, tolerante a texto
extra). Um terceiro problema de raciocínio apareceu no teste — Claude usou a quantidade
pedida como fator de conversão quando as unidades já eram iguais (136 × 10 em vez de manter
136) — corrigido explicitando no prompt que o fator vem do tamanho da embalagem, nunca da
quantidade pedida, e que unidade igual não gera equivalência (`null`). Validado com 3 casos:
unidade igual (sem falsa conversão), unidade diferente sem tamanho de embalagem informado
(honesto, `null`, mostra preço bruto) e unidade diferente com conversão calculável (bate
exato com o exemplo do Dennis: 250 SC de cimento 50kg, SINAPI R$0,80/KG → R$40,00/SC).

**Mesmo dia, bug real na Camada 2 — falso "unidade diferente":** Dennis reportou "M2 e m2 são
unidades iguais" após ver dois itens (Forro PVC, Revestimento Cerâmico) marcados como
"unidade diferente da comercial — conversão não calculada" quando a unidade comercial era
`m2` e a do SINAPI `M2` — a mesma unidade, metro quadrado. Causa raiz: a comparação
`und != und_sinapi` na tela era sensível a maiúsculas/minúsculas. O Claude já retornava
`preco_equivalente_unidade_comercial: null` corretamente (sem conversão porque já é a mesma
unidade); o bug estava só na exibição, que lia esse `null` como "não consegui calcular" em
vez de "não precisa calcular". Corrigido com `_mesma_unidade()` (ignora caixa/espaço).

**Mesmo dia, compreender o produto antes de concluir ausência ou buscar por texto literal:**
dois casos reais de falso negativo: "Argamassa EXT 10 EM 1 - 20KG" (Hipermassa) não casava no
SINAPI porque a busca usava o nome comercial literal, que não descreve a função técnica
(argamassa colante); "Rejunte Cinza Ártico 5kg Quartzolit" retornava "quantidade e unidade não
identificadas" descartando a informação de embalagem (5kg) junto com a quantidade que
realmente não dava pra ler. Terceiro ponto levantado durante a implementação: cada item
estava sendo interpretado isoladamente, sem usar o contexto da lista inteira ("um engenheiro
não olha item isolado, ele entende o contexto da compra primeiro"). Corrigido nos dois
prompts, sem nova entidade: `PROMPT_INTERPRETAR_LISTA` ganhou um passo de olhar a lista como
conjunto (indica a etapa de obra — revestimentos, hidráulica, elétrica) e dois campos novos —
`embalagem` (tamanho de uma unidade de venda, distinto de quantidade/unidade da compra) e
`termo_busca_sinapi` (descrição técnica genérica, sem marca, só pra buscar candidato SINAPI,
nunca exibida). `PROMPT_ESCOLHER_SINAPI` ganhou o mesmo reforço de contexto de lista e passou
a usar `termo_busca_sinapi`/`embalagem` quando disponíveis em vez de re-inferir do zero.
Testado com a lista completa do Dennis: argamassa casou em Alta confiança (antes não achava
nada buscando "ext 10 em 1"); rejunte extraiu embalagem "5 KG" com quantidade/unidade `null`
e observação própria; efeito colateral positivo — porcelanato/revestimento cerâmico juntos na
mesma lista casaram certo nos dois (Alta confiança), o falso positivo de categoria adjacente
visto na Camada 2 original não se repetiu.

**2026-07-04, redesenho de experiência em 3 níveis + gravação real da Lista de Compras:**
Dennis: "a tela de conferência está muito técnica... o objetivo não é explicar como a Laura
chegou na resposta, é eu conferir rapidamente se está correta." Proposta de UX apresentada e
validada antes de codar. Implementado: Nível 1 (Tela de Conferência, nova tela principal —
item em 3 linhas, indicador 🟢/🟡/🔴, alertas agrupados no rodapé, resumo com referência
total estimada), Nível 2 (Edição — só ao escolher um item aparecem todos os campos; edição do
item inteiro, não campo a campo, por decisão explícita de simplicidade), Nível 3 (Análise
Técnica — a tela técnica completa que já existia, virou nível opcional). Prioridade de
referência de preço definida: última compra própria > SINAPI convertido > nenhuma, sem
mostrar a origem no Nível 1. Critério de indicador ajustado por Dennis: "sem referência de
preço" é 🟡, não 🔴 — não terminar aquele item com nenhuma referência conhecida não impede
pedir orçamento. Gravação real implementada (`_cb_lc_gerar` + `criar_ou_buscar_lista_aberta`/
`adicionar_item`, já existiam sem conexão) — bloqueia sem obra definida. Achado: schema de
`lista_compra_itens` nunca tinha colunas pra fabricante/código comercial — adicionadas.
Testado com a foto real de 8 itens (soma de referência conferida manualmente), gravação
bloqueada sem obra e bem-sucedida com obra. Pendente: edição campo a campo, Pedido de Compra
a partir da Lista, vínculo com orçamento.

**Mesmo dia, Camada 3 — corrigido falso positivo por palavra isolada:** achado registrado
antes como dívida técnica (Revestimento Cerâmico casando com bloco/tijolo cerâmico, mesma
unidade de busca "cerâmica"/"cerâmico" sem verificar se era o mesmo produto). Dennis pediu
planejamento antes de mexer, depois definiu a regra: unidade do item da lista e unidade do
pedido histórico devem ser iguais, sem conversão (ao contrário da Camada 2/SINAPI) — "isso
não deveria mudar". Implementado como filtro obrigatório em `_referencia_laura_item()`
(reaproveitando `_mesma_unidade()` já criada pra Camada 2); sem a unidade do item, não
retorna referência nenhuma. Testado: falso positivo eliminado; efeito colateral aceito de
menos matches no total (precisão em troca de recall). Regressão confirmada.

**Mesmo dia, Camada 4 — tela de conferência editável:** antes desta camada, a interpretação
parava em texto puro, sem nenhuma ação possível depois de ler a lista. Investigado o padrão
já existente (`_resumo_gerar`/`teclado_orcamento` do orçamento) antes de desenhar — mesmo
padrão reaproveitado, sem inventar estilo novo de interação. Perguntado ao Dennis como tratar
edição nesta camada (já que a edição granular é a Camada 5, ainda não implementada); ele
escolheu reaproveitar o mecanismo que já existe no orçamento (`edit_itens` — reescrever a
lista inteira como texto livre, reinterpretada do zero). Implementado:
`_teclado_lista_interpretada()` (botões "✏️ Editar itens"/"✖ Fechar"), endereço da obra
adicionado ao cabeçalho de `_texto_itens_interpretados()` (via `buscar_obra()`),
`_cb_lc_editar`/`_cb_lc_fechar` no `_CB_DISPATCH`. Os três pontos de entrada da Lista de
Compras agora emitem a mesma tela com teclado. Testado com callbacks simulados e regressão
do fluxo orçamento → pedido.

**Mesmo dia, investigação — "sc" e "6,0" legíveis, Laura não lia:** Dennis reportou a linha do
Rejunte (unidade "sc", quantidade "6,0") bem legível na imagem retornando errada. Causa raiz:
a foto real tem só 631×161 pixels — Telegram compacta agressivamente uploads tipo "foto" (o
app reamplia na tela, mascarando a perda real). Confirmado repetindo a extração 3x na mesma
imagem: respostas diferentes pras mesmas duas linhas, batendo com limite de pixels, não falha
de prompt. Adicionada checagem de plausibilidade em `PROMPT_INTERPRETAR_LISTA` (releitura
quando a unidade não faz sentido técnico pro produto) — ajudou parcialmente numa rodada, mas
não resolve resolução insuficiente. Documentado em `docs/ARQUITETURA.md`: mitigação sem
código é enviar a lista como arquivo/documento no Telegram, não como foto.

**Mesmo dia, Camada 3 — referência de último preço pago (própria Laura):**
`_referencia_laura_item()` reaproveita `procurar_item()` (`financeiro/consultas.py`, já
existia, sem chamada de IA) — tenta a descrição inteira primeiro, cai pra palavra
significativa isolada se não achar nada. Grau de confiança muda conforme a estratégia:
`confirmada` na descrição inteira, `aproximada` na palavra isolada (vocabulário do Princípio 8
da Política de Compras). `_adicionar_referencia_laura()` roda depois da Camada 2, juntando as
duas referências (SINAPI + histórico próprio) na mesma tela. Exibição: "Última compra
(Aproximada): R$ 19,90/UND — Materiais Teste LTDA"; quando não há histórico, mostra "sem
referência própria encontrada" em vez de ficar em silêncio (Princípio 5). Testado com o
Cimento CP II 50kg: achou o item já cadastrado no histórico ("Cimento CP-II 50kg", fraseado
diferente) via busca por palavra, confiança aproximada, preço e fornecedor corretos.

**Bug real encontrado e corrigido (Lição #12 de `LICOES_EXTRACAO.md`):** Dennis reportou
"unidade não é quartzolit, é sc" — marca/fabricante sendo confundida com unidade de medida
quando aparece perto da quantidade no texto/foto original. Mesma classe de bug da Lição #1
(instrução implícita não basta). Corrigido nos dois PROMPTs com lista explícita de unidades
válidas e proibição nomeada; validado com 8 fraseados diferentes antes de aplicar.

**Limpeza:** todo o código das duas fiadas de ontem que ficou órfão com o redesenho foi
removido (`_tela_lista_compras`, `_teclado_lista_compras`, `_abrir_lista_compras`,
`_parse_item_lista`, `_resumo_lista_materiais`, `teclado_lista_materiais`,
`_tela_lista_finalizada`, `_cb_lista_mat_confirmar`, `_cb_lista_fechar`,
`_cb_lista_add_sug`, `_cb_lista_rem_item`); `[lista_materiais]` saiu do `PROMPT` compartilhado
de classificação. `mostrar_ajuda()` corrigida (ainda descrevia o `/lista` de ontem).

**Achado arquitetural, registrado e não corrigido agora:** ao unificar os dois caminhos de
`lista_materiais`, Dennis perguntou se `comprovante_pix`/`nota_fiscal` já convergiam do mesmo
jeito. Não convergem — três pontos de entrada (`_cb_sel_tipo_inicial`, `_cb_set_tipo`,
`_cb_ok`) fazem a mesma coisa de formas diferentes, um deles com bug real (`_cb_set_tipo()`
sempre mostra tela de orçamento, não importa o tipo escolhido). Por pedido explícito do
Dennis, **não corrigido nesta fiada** — "não é apenas trocar uma chamada por outra... toca o
coração da Laura". Registrado como dívida técnica e nova visão de longo prazo ("Motor de
Interpretação e Classificação de Documentos") em `docs/ROADMAP.md`, com o princípio geral que
emergiu da conversa e uma fiada de investigação própria a fazer antes de qualquer código.

**Não concluído:** Camadas 5-6 do módulo de Compras (edição item a item, gravação final
confirmada) — ver ROADMAP.md. Validação completa ao vivo no Telegram com a foto real que
motivou o redesenho.

---

**Módulo de Compras — Fiada 1 (comando `/lista`) e Fiada 2 (foto → Lista de Compras)** *(2026-07-03)*

> **Substituída em 2026-07-04** — não complementada. Ver entrada acima. Preservada aqui só
> como histórico da decisão original.

Primeiras duas fiadas de engenharia do domínio de Compras, na mesma sessão da fundação
conceitual (ver entrada seguinte). Aprovadas separadamente por Dennis, cada uma com seu
próprio critério de aceite (PROCESSO.md Seção 2).

**Fiada 1 — comando `/lista`:** módulo `compras/` criado do zero (`compras/lista.py` +
`compras/__init__.py`), nasce modular desde o primeiro dia (ADR-002). `/lista GGV03` cria
ou reabre a Lista de Compras da obra; Laura sugere itens recorrentes de `itens_pedido` com
o último preço pago — **critério explícito do Dennis**: sugestão só aparece com histórico
real, nunca inventada; obra sem nenhuma compra anterior recebe mensagem clara ("Ainda não
há histórico...") em vez de sugestão vazia disfarçada. Duas tabelas novas: `listas_compra`,
`lista_compra_itens`. Testado via script contra `data/laura_test.db` (sugestão real ×
sem-histórico) e regressão do fluxo orçamento → pedido confirmada.

**Fiada 2 — lista de materiais por foto:** pedido do Dennis no meio da sessão, depois de
mandar uma foto esperando encontrar a Lista de Compras no menu de tipo de documento e não
achar. Visão dele: "mesma lógica do orçamento e criação do pedido de compras" — reaproveitar
o mecanismo já provado (extração por IA → tela de revisão → confirmar) num ponto mais cedo
do processo. Implementado: novo tipo de documento `lista_materiais` no `PROMPT` (com cuidado
explícito pra não inventar preço/fornecedor, mesmo espírito da Lição #1 de
`LICOES_EXTRACAO.md`), novo botão no menu, tela de confirmação simplificada (sem
fornecedor/valor/condição — não existem nesse tipo), itens confirmados entram na Lista de
Compras via `compras.adicionar_item()` (reaproveitando a Fiada 1).

**Correção ao vivo, durante o próprio teste:** primeira versão da Fiada 2 terminava a
confirmação na tela de edição contínua da Fiada 1 (`_tela_lista_compras`, "adicionar mais
itens / fechar"). Testado com foto real do Dennis — 11 itens de material hidráulico (Tigre)
extraídos corretamente, confirmados no banco de teste — mas Dennis apontou que a saída
devia ser uma **lista finalizada**, fechada, não um convite a continuar editando. Corrigido
na hora: `_tela_lista_finalizada()`, resumo só leitura. O formato de documento oficial
(possivelmente um PDF, como o Pedido de Compra) fica para decidir depois — por hoje é texto.

**Bug real encontrado e corrigido durante a investigação:** achei (e corrigi) uma
duplicação morta em `_cb_set_ggv()` — um `if status == "confirmado": ... else: ...` cujos
dois ramos chamavam exatamente a mesma função com o mesmo resultado. Limpeza sem mudança
de comportamento, encontrada ao adaptar essa função pro tipo `lista_materiais`.

**Aprendizado registrado, não implementado:** Dennis apontou que a Lista de Compras
provavelmente precisa de um endereço — frete é parte da negociação do orçamento, e sem
saber o destino da entrega falta informação relevante pra comparar propostas. Não implementado
agora (fora do critério de aceite das duas fiadas); registrado no ROADMAP.md para quando o
Modelo de Domínio for revisitado. Pode já existir via `obras.endereco_entrega` — decidir se
a Lista de Compras herda isso da obra ou precisa de campo próprio é decisão futura.

**Não concluído:** validação completa ao vivo no Telegram. Bot subiu em `LAURA_ENV=test`
(sem afetar produção), Dennis testou parcialmente (obra não identificada → definir obra →
foto real processada), mas a sessão encerrou antes de percorrer o fluxo do início ao fim
sem interrupção. **Retomar amanhã antes de considerar as duas fiadas fechadas.**

---

**Fundação do domínio de Compras — política, casos de uso, modelo de domínio** *(2026-07-03)*

Motivado pelo gatilho real de sempre não conseguir achar preço de item comprado sem ler
o pedido inteiro (já resolvido tecnicamente por `itens_pedido`/`procurar_item()`), Dennis
quis ir além da correção pontual: definir como a Laura deveria participar do processo de
compra de ponta a ponta, antes de qualquer linha de código nova.

**Processo em três documentos, cada um construído em cima do anterior:**
1. `docs/POLITICA_COMPRAS.md` — princípios, refinados por várias rodadas de revisão
   conjunta. Núcleo: Laura é consultora de compras, nunca compradora automática; toda
   negociação e decisão comercial permanece humana; nenhuma compra planejável nasce de
   um orçamento — nasce de uma necessidade, organizada numa Lista de Compras.
2. `docs/CASOS_DE_USO_COMPRAS.md` — 15 casos de uso em linguagem de negócio (planejada,
   sem histórico, com histórico, fornecedor preferencial vence/perde, emergencial,
   obrigatória, serviço, equipamento, recorrente, e 5 casos de proatividade/erro evitado
   encontrados em revisão crítica posterior). Seção "Os Três Momentos da Laura"
   (antes/durante/depois) e 7 padrões comuns identificados no fechamento.
3. `docs/MODELO_DOMINIO_COMPRAS.md` — transição pra engenharia: objetos conceituais
   (Lista de Compras, Item da Lista, Orçamento, Alerta — cada um com ciclo de vida
   próprio; Referência de Preço e Tendência de Fornecedor como valores computados, não
   entidades), eventos, responsabilidades Laura/usuário, regras por momento. Revisão
   arquitetural final corrigiu vocabulário interno vazado (`pfm_gerado` → "emitido") e um
   estado que era na verdade relacionamento opcional, não fase de ciclo de vida.

**PROCESSO.md** ganhou o mecanismo "Políticas de Domínio" — generalizado por pedido do
Dennis pra não virar regra especial de Compras: qualquer domínio (Compras, Financeiro,
Obras, Estoque...) pode ganhar `POLITICA_<DOMINIO>.md` + documentos complementares, de
leitura obrigatória condicional ao tocar aquele domínio, mesmo padrão já usado pra
`LICOES_EXTRACAO.md`.

**GLOSSARIO.md** ganhou o termo "Lista de Compras" e reescreveu a distinção
"Orçamento vs. Pedido de Compra" como cadeia de três objetos.

**IDENTIDADE_DO_PRODUTO.md** referencia a nova política em três pontos leves (Objetos
Centrais, novo Marco de Maturidade, tabela de documentos) — sem importar detalhe de
processo, preservando a separação entre identidade de produto e política de domínio
(ajuste pedido explicitamente por Dennis durante a revisão).

**Decisão deliberada de não tocar:** `CONSTITUICAO.md` (abstrata demais pra nomear
domínio específico, mesmo padrão de nunca nomear Financeiro/NF-e) e nenhuma ADR existente
(documentos históricos — ADR-002 tem sua própria versão datada de "Os Dois Objetos
Centrais", preservada como estava na aprovação).

**Nenhum código escrito.** Decisão explícita de Dennis: entender o domínio por completo
antes de qualquer implementação, pra que "a arquitetura praticamente caia sozinha".

---

**Sincronização de documentação com o código real** *(2026-07-03)*

Sessão aberta pelo checklist obrigatório do Jeito Claude. Ao ler ROADMAP.md/ESTADO.md/ARQUITETURA.md
na ordem exigida, a prioridade 🔴 #1 do roadmap (vulnerabilidade de segurança) e a prioridade #2
(estruturar itens de compra) foram propostas como próxima fiada — mas checar o código antes de
começar mostrou que **ambas já estavam implementadas havia horas**, em commits da própria sessão
anterior (`a2077f0`, `95c4717`, `86a82cc`) que nunca foram capturados nos documentos de estado.

**Causa raiz**: os commits de encerramento de sessão (`d807b32`, `fd83224`) só registraram a parte
"Otimização de BD + CLI" da sessão anterior — o commit `a2077f0` (segurança + `financeiro/relatorios.py`,
cronologicamente ANTES da otimização de BD) ficou de fora, e ARQUITETURA.md não foi tocado desde
2026-07-02, faltando `itens_pedido`, `parcelas_pagamento` e `insumos_sinapi` na seção de banco de dados.

**Verificado diretamente no código antes de corrigir a documentação** (não apenas nos commits):
- `responder_botao()` (bot.py:4046) já retorna cedo se `update.effective_user.id != DONO_ID`
- `atualizar()`/`atualizar_obra()` já validam contra `_COLUNAS_DOCUMENTO`/`_COLUNAS_OBRA`
- `itens_pedido` já populada por `gerar_pfm()`/revisão, com backfill dos pedidos antigos e CLI de
  busca (`scripts/consultar.py --item`)

**Corrigido**: ESTADO.md, ROADMAP.md, ARQUITETURA.md e CHANGELOG.md atualizados pra remover os dois
itens já resolvidos das listas de pendência, documentar as duas entregas que faltavam (segurança +
`financeiro/relatorios.py`), e adicionar as três tabelas que faltavam na seção 3 de ARQUITETURA.md.
Nenhum código alterado nesta sessão — só documentação.

**Lição**: o checklist do Jeito Claude não serve só pra ler documentação — serve pra **desconfiar**
dela quando o código pode ter avançado mais rápido que os `.md`. "O que já construímos diz algo
sobre isso?" inclui checar o código, não só o texto.

---

**Remoção do DOCX + ADR-004 (modularização) + correções de matching PIX/NF-e** *(2026-07-02)*

Sessão iniciada com o pedido do Eric (filho do Dennis, estudando engenharia de software) de que
`bot.py` estava "bagunçado" — virou o gatilho pra uma rodada grande de limpeza e organização.

**DOCX removido do fluxo principal**: `gerar_pfm()` parou de montar `Document()` (python-docx) —
o PDF (HTML via Playwright, já era o formato entregue de verdade) passa a ser o único documento
gerado. Removidos os helpers exclusivos do Word (`_cell_bg`, `_set_col_widths`, `_secao_row`,
`_kv_row`, `_data_extenso`) e os imports de `docx`.

**Bug de segurança crítico corrigido**: `bot.py` não tinha guard `if __name__ == "__main__":` — o
bloco final (`init_db()`, `Application.builder()`, `app.run_polling()`) rodava automaticamente ao
importar o módulo, sempre com o token real do Telegram. Descoberto quando um script de teste
conectou o bot de produção por engano por alguns minutos (sem dano — nenhuma mensagem real chegou
nesse intervalo). Corrigido; `import bot` agora é seguro para scripts/testes.

**Auditoria de bibliotecas (7 agentes especializados, somente leitura)**: varredura completa do
código em busca de reinvenção de bibliotecas prontas. Achado real aplicado: conversor de número por
extenso manual (~85 linhas) trocado por `num2words` (biblioteca já madura), validado byte-a-byte
contra os mesmos casos. A auditoria também encontrou, de bônus, uma vulnerabilidade real
(`responder_botao()` sem checagem de `DONO_ID`, combinada com SQL injection via nome de coluna não
sanitizado em `atualizar()`/`atualizar_obra()`) — **ainda não corrigida**, ver Dívidas Técnicas.

**ADR-004 — modularização parcial de `bot.py`**: gatilho de linhas da ADR-003 (~3.500) disparou
(arquivo estava em 3.994). Processo de dois agentes independentes (propor + tentar derrubar, mesmo
método da ADR-003) reduziu drasticamente o escopo original — só 2 fiadas aprovadas: dispatch table
interna em `responder_botao()` (929 linhas, 59 grupos de ramos → dict, extração mecânica via script
AST, verificada byte-a-byte antes de substituir) e extração do módulo `nfe/` (`nfe/__init__.py` +
`nfe/nfe.py`, 84 linhas, importável sem `bot.py`). `fornecedor/`, `obra/`, `comprovante/` avaliados
e adiados com gatilho próprio documentado (riscos reais encontrados: quebra de atomicidade em
`_gerar_recibo()`, `_total_pago()` usando banco global em vez de parâmetro). Ver
`docs/decisoes/ADR-004-modularizacao-bot-py.md`.

**Recibo ganhou texto narrativo**: modelo antigo do Excel (GGV01, Valdir Aparecida Silveira) usava
um parágrafo tipo "Recebi de X, a importância supra de R$ Y (valor por extenso), Z. Por ser a
expressão da verdade, dou quitação..." — o recibo atual só mostrava a descrição do item, sem
quantidade. `_gerar_html_recibo()` mantém o layout em cartão mas troca a seção "Serviço Prestado"
por esse parágrafo completo, com quantidade/unidade do item e valor por extenso (`num2words`).

**Bug de parsing corrigido**: `ITEM_RE` só reconhecia unidade de compra com até 4 letras — palavra
por extenso ("blocos" em vez de "UND") caía no fallback sem preço unitário. Ampliado pra 15 letras.
Documentado como item #11 em `docs/LICOES_EXTRACAO.md`.

**Matching de comprovante PIX — lista completa**: `buscar_candidatos_pix()` cortava em top-3 com
desempate por ordem de inserção (favorecia sempre os pedidos mais antigos, escondendo pedidos
legítimos mais novos em caso de empate). Agora lista **todos** os pedidos com saldo em aberto,
ordenados por score e, em empate, por proximidade de valor — e virou também uma ferramenta de
gestão (mostra o total pendente no topo da mensagem).

**Regra de elegibilidade de NF-e mudou**: `buscar_candidatos_nfe()`/`vincular_nfe()` exigiam
`status='pago'` — um pedido em pagamento parcelado (parcial pago, entrega já feita, nota já
emitida pelo fornecedor) não aparecia como candidato. Decisão do Dennis: NF-e pode ser vinculada a
qualquer momento, independente do quanto já foi pago — pagamento (PIX) e NF-e são registros
paralelos, não um dependente do outro. Mensagem de confirmação (`_cb_nfe_confirmar`) ajustada pra
não dizer mais "Ciclo fechado" quando o pagamento ainda está em andamento.

**Deep-research restrito neste projeto**: configurado via `.claude/settings.local.json` pra não
disparar automaticamente — só sob invocação explícita (`/deep-research`). Parte de uma conversa
mais ampla sobre gestão de custo de IA entre os projetos do Dennis (ver memória `user_gestao_custos_ia`).

---

**Incidente crítico: documento de pedido pago apagado por botão antigo — corrigido** *(2026-07-02)*

Dennis relatou não conseguir acessar o GGV03-007 (já pago). Investigando, o documento raiz
(`documentos.id=28`) tinha sido apagado do banco — o lançamento continuava intacto (por isso a
lista de pedidos ainda mostrava certo), mas a busca direta pelo código não encontrava mais nada.

**Causa raiz**: o descarte automático implementado ontem (`_descartar_documento`, pro botão
"Cancelar") não verificava se o documento já tinha virado um pedido de verdade antes de apagar.
Telegram mantém botões de mensagens antigas clicáveis para sempre — um toque num "Cancelar" de
uma mensagem de quando o GGV03-007 ainda estava sendo processado (semanas atrás, na numeração
antiga) disparou o descarte num documento já pago.

**Corrigido**: `_descartar_documento()` agora verifica `pfm_numero` antes de apagar — só descarta
documentos que ainda não viraram pedido. Documentos já usados só podem ser removidos via
"🗑 Excluir pedido" (com confirmação explícita, `force=True`). Botão "Cancelar" agora mostra um
alerta claro em vez de falhar silenciosamente quando recusa.

**Recuperação**: o lançamento sobreviveu integralmente (nunca é tocado por esse descarte), e os
arquivos reais (PFM, comprovante, NF-e) continuavam intactos no OneDrive — só o vínculo interno
do banco tinha sumido. Reconstruído a partir do PDF real gerado (mesmos valores: subtotal
R$3.700, desconto R$100, total R$3.600) e da observação já registrada sobre a correção do item
com a Espaço Azul/Heliadi. Restaurado duas vezes — a primeira tentativa foi apagada de novo antes
do bot reiniciar com a correção; a segunda, já protegida, ficou estável.

**Esclarecimento paralelo**: a confusão "Base Forte" vs. "Espaço Azul" (do início do dia) se
resolveu — são a mesma empresa, "Base Forte" é o nome fantasia. O cadastro de fornecedor já
estava correto (`nome='Base Forte'`, `razao_social='ESPACO AZUL...'`); a confusão era só de nome
de arquivo no OneDrive, não do sistema.

**Segundo bug encontrado no processo**: Dennis achou que a observação que registramos sobre a
correção do item (água fria × esgoto) tinha se perdido de novo — mas ela estava salva certinha no
banco. O problema real: o cockpit do pedido (`mostrar_pedido()`, a tela que abre ao digitar o
código) nunca exibia o campo Observações — só a tela de resumo antes de confirmar, que ninguém
revisita depois de um pedido já pago. Corrigido: `Pedido` ganhou o campo `observacoes`, e o
cockpit mostra "📝 Obs: ..." quando existe algo registrado.

**Terceiro bug, mais sério que o segundo**: mesmo depois da correção acima, a observação continuou
sumindo — porque `_obs()` só capturava texto em **linhas separadas** abaixo de "Observações:", mas
o formato real, usado em 100% dos casos, sempre foi tudo **na mesma linha** ("Observações: texto
aqui"). `_obs()` pulava essa linha inteira sem capturar nada. Provavelmente estava quebrado desde
que foi escrita, silenciosamente, em qualquer lugar que dependesse dela. Corrigido pra aceitar os
dois formatos (inline e multi-linha); também passou a filtrar valores tipo "não informado" com
`_campo_vazio()` em vez de mostrar isso como se fosse uma observação real.

**Refino de UX pedido pelo Dennis**: o botão "Cancelar" (resumo pré-confirmação) que hoje já
recusa apagar um documento virado pedido, ao ser clicado numa mensagem antiga, abria uma tela
intermediária ("Mensagem antiga — esse documento já é o pedido #X" com botão "Voltar") — dois
cliques pra chegar no cockpit. Simplificado pra abrir o cockpit direto, um clique só, sem tela no
meio. Os três botões "Cancelar" do fluxo de orçamento (`teclado_orcamento()`, confirmação inicial
de outros tipos de documento) foram renomeados pra **"← Voltar"**, consistente com o resto da
Laura — a ação de fundo continua a mesma (descarta se ainda não virou pedido, navega pro pedido se
já virou), só o rótulo mudou.

**Descoberto durante uma consulta de preço**: Dennis perguntou o preço de um "Te de redução
32x25" já comprado (GGV03-006, Carlessi) — achei, mas só depois de ler o texto corrido inteiro do
pedido, porque **os itens de compra não são estruturados numa tabela própria hoje**, só existem
como texto dentro de `dados_claude`. Isso é exatamente o gatilho da fase "lista de compras" que
ficou combinada como pendente na conversa sobre SINAPI — vira a primeira prioridade da próxima
sessão.

**Conversa paralela, sem código**: exploramos como usar Claude Code Remote (app do Claude no
celular) pra consultar o banco da Laura de qualquer lugar — sem ambiente configurado ainda, e o
`data/laura.db` não está no GitHub (dado de produção, fora do repositório de propósito). Dennis
tem um servidor Proxmox em casa (Eric administra) que poderia hospedar o bot + banco sempre
ligado; ideia registrada, não iniciada.

---

**Sincronização com a Receita sempre ativa, com política por campo** *(2026-07-02)*

Depois do enriquecimento (fiada anterior), Dennis notou que o job de 6h só mexe em fornecedor
`receita_pendente=1` — como nenhum estava mais pendente, toda vez que um campo novo é adicionado
(como o CNAE) é preciso rodar um script manual pra propagar pros já cadastrados. Perguntou se não
seria melhor sincronizar sempre.

**Decisão em três partes**, refinada em conversa (não foi uma decisão única):
- **Razão social, cidade, UF, CNAE**: sempre atualiza com o dado mais recente da Receita — são
  dados oficiais de cadastro, baixo risco de estar errado
- **Ramo**: continua priorizando o texto natural já salvo (extraído de um documento real, ex:
  "Comércio de Materiais de Construção") — o CNAE da Receita (mais burocrático, ex: "Comércio
  varejista de materiais de construção em geral") só entra como fallback quando ainda não há nada.
  Achado durante o teste: sincronizar sempre trocaria o texto natural pelo burocrático a cada 6h —
  Dennis apontou que "ramo é uma coisa, CNAE é outra"
- **E-mail, telefone**: só preenchem se ainda estiverem vazios, nunca sobrescrevem — Dennis notou
  que esses dois têm risco real de estar desatualizados no cadastro da Receita (empresa atualiza
  endereço por obrigação legal, mas raramente atualiza telefone/e-mail registrado)

O job (`_sincronizar_receita_fornecedores`, renomeado de `_sincronizar_receita_pendentes`) agora
roda em todos os fornecedores com CNPJ a cada 6h, mas só grava quando algo realmente muda, e só
avisa o Dennis quando isso acontece — nada de mensagem repetida sem novidade.

---

**Enriquecimento de fornecedor via Receita — e-mail, telefone, CNAE** *(2026-07-02)*

Dennis começou a usar o DB Browser for SQLite pra olhar o banco direto, e perguntou sobre a
sincronização com a Receita. Isso levou a duas melhorias pontuais:

- **Bug corrigido**: a tela de resumo (antes de gerar o pedido) travava o nome do fornecedor como
  "Fornecedor não identificado" mesmo quando só o CNPJ era informado e o fornecedor já existia no
  cadastro — nunca consultava `buscar_fornecedor()` pra puxar a razão social. Corrigido: agora
  segue o mesmo padrão já usado em CNPJ/PIX, e no PDF/PFM final.
- **`_consultar_receita()` ampliada**: além de razão social/cidade/UF, agora também extrai e-mail,
  telefone (`ddd_telefone_1`/`ddd_telefone_2`) e CNAE (código formatado no padrão oficial do
  Cartão CNPJ, ex: "47.44-0-99", + descrição da atividade econômica principal) — tudo já vinha na
  mesma resposta da BrasilAPI, só não estava sendo aproveitado.
- Novo campo `fornecedores.cnae`, separado de `ramo` (que continua sendo o texto usado no PFM,
  geralmente vindo do documento — CNAE só entra como fallback do `ramo` quando o documento não
  especifica nada).
- **Sincronização retroativa rodada duas vezes** pra aplicar os campos novos aos 27 fornecedores já
  cadastrados (o job periódico só mexe em pendências, e nenhum estava mais marcado como pendente).
  Resultado: 22 ganharam telefone, todos os 27 ganharam CNAE; e-mail quase nunca vem preenchido na
  Receita (dado raro de existir publicamente).

**Incidente operacional**: o bot caiu com `sqlite3.OperationalError: database is locked` ao tentar
reiniciar — o DB Browser for SQLite estava aberto com o `laura.db`, segurando o arquivo. Resolvido
fechando o programa. Lição registrada: nunca deixar um visualizador de SQLite aberto enquanto o
bot roda, senão qualquer restart (por mudança de código) derruba a Laura.

---

**Ativação em produção + cadastro retroativo ao vivo de GGV03** *(2026-07-01)*

Depois de fechar a base de insumos SINAPI, Dennis pediu pra começar o cadastro retroativo de
GGV03 direto pelo Telegram, em produção de verdade, comigo acompanhando o banco em paralelo. Isso
expôs, um por um, uma série de bugs reais de extração/parsing que só apareciam com documentos de
produção de verdade (boletos, comprovantes com formatação variável) — nunca tinham surgido nos
testes com dado fictício.

**Ativação:**
- `LAURA_ENV=prod` no `.env`; banco zerado de novo por decisão explícita (incluindo o GGV03-001
  de teste do Valdir) — cadastro passa a ser 100% via Telegram ao vivo, sem numeração manual
- Achado e corrigido em seguida: dois processos `bot.py` rodando ao mesmo tempo (um meu, um aberto
  manualmente por Dennis) causavam conflito de polling no Telegram ("fora de serviço"); só uma
  instância deve rodar por vez durante a sessão

**10 bugs reais encontrados e corrigidos, catálogo completo em `docs/LICOES_EXTRACAO.md`:**
1. Claude mistura template de campos de tipos diferentes (boleto virou comprovante_pix +
   orçamento ao mesmo tempo) — PROMPT agora proíbe explicitamente
2. Fornecedor confundido com CNPJ da própria empresa em boleto (Pagador × Beneficiário) — guard
   de CNPJ próprio ampliado de um único CNPJ (VII) pra um conjunto (VII + DeltaD)
3. Unidade de medida com dígito ("m2" sem superíndice) quebrava o regex de item — ampliado pra
   aceitar dígito/superíndice
4. `_parse_brl()` interpretava "R$ 5.000" (sem vírgula) como 5,00 em vez de 5000,00 — heurística
   de 3 dígitos após o ponto pra distinguir milhar de decimal
5. Data extraída sem zero à esquerda ("5/06/2026") virava data ilegível no histórico — parser
   trocado de fatiamento de índice fixo pra regex tolerante
6. Documento que falha (cancelado, comprovante sem correspondência) ficava travado pelo hash,
   impedindo reenvio — `_descartar_documento()` limpa registro + arquivo automaticamente
7. PIX já conhecido do fornecedor não era reaproveitado em pedidos novos — tela de resumo passou
   a consultar `buscar_fornecedor()`, e o cadastro (automático ou manual) passou a persistir PIX
8. Filtro de "campo vazio" só reconhecia a forma masculina ("Não identificado") — "Não
   identificada" passava como dado real; `_campo_vazio()` agora tolera gênero e frase mais longa
9. Comprovante de pagamento parcial (R$2.500 de um pedido de R$30.000) não encontrava o pedido —
   `buscar_candidatos_pix()` só reconhecia valor exato ou ±10%; agora compara com o saldo restante
   e aceita qualquer valor parcial como candidato válido
10. Bloco de entrega do PDF sempre mostrava "Obra GGV03" fixo, nunca o endereço real salvo no
    banco — corrigido pra exibir o endereço de verdade, com fallback pro padrão da obra

**Seis melhorias de produto, pedidas durante o cadastro:**
- Botões renomeados pra refletir que aceitam foto OU arquivo ("📋 Orçamento / Fatura",
  "📦 Foto/arquivo de entrega") — rótulo antigo sugeria só cotação/foto
- **Botão "🗑 Excluir pedido"** no cockpit, com tela de confirmação — apaga lançamento, parcelas,
  entrega e documentos vinculados na Laura (nunca mexe em arquivo já arquivado no OneDrive);
  testado com pedido fictício antes de liberar
- **Endereço de entrega preenchido automaticamente** com o padrão da obra assim que o GGV é
  identificado — sem precisar clicar em "🏗 Obra" toda vez; ainda editável depois
- **Observações do pedido agora é campo editável** em "Corrigir campos" — antes só aparecia na
  tela, sem jeito de corrigir
- **Botão "✖ Cancelar" na tela de escolha de tipo de documento** — antes, se o usuário chegasse
  ali sem querer, não tinha como sair
- Limpeza retroativa de documentos "cancelado" que sobraram de antes do descarte automático
  existir, e de arquivos órfãos no OneDrive de um pedido excluído (Base Forte/GGV03-006 antigo)

Testado ao vivo com os 8 pedidos reais completos de GGV03 — 7 pagos, 1 em aberto (pagamento
parcelado em andamento).

---

**Base de insumos SINAPI (referência)** *(2026-07-01)*

Dennis quer, no futuro, que a Laura reconheça automaticamente qual insumo de referência (padrão
nacional) corresponde a um item de orçamento com descrição livre de fornecedor — e mantenha uma
coluna de fabricante separada, sem perder a especificidade comercial. Antes de qualquer
implementação, tivemos uma conversa conceitual longa (premissas, entidades do domínio, como ERPs
de construção resolvem isso, armadilhas de equivalência técnica × comercial) — não repetida aqui,
mas registrada na conclusão prática abaixo.

**Decisão de arquitetura, com agentes de engenharia/arquitetura invocados antes de implementar:**
avaliamos usar o projeto open-source `AutoSINAPI`/`autoSINAPI_API` (GitHub, stack Docker com
Postgres + API REST + Kong) contra baixar a planilha oficial que a Caixa já publica todo mês e
importar direto pro SQLite. Descartamos o stack Docker: Dennis não tem Docker instalado, o próprio
AutoSINAPI tem a URL de download quebrada (a Caixa mudou a estrutura de pastas em 2025 e o projeto
não acompanhou — confirmado baixando de verdade), a variante com API não tem nenhum modo sem
Docker (7 serviços), e ambos os repositórios são mantidos por uma única pessoa. Nada disso se
justifica para popular uma tabela de referência que hoje é só leitura.

**Implementado:**
- `scripts/import_sinapi.py` — mesmo padrão de `scripts/import_fornecedores.py` (script único,
  roda manualmente, escreve direto no `laura.db`, sem serviço externo)
- Baixa `SINAPI-{ano}-{mes}-formato-xlsx.zip` direto do site da Caixa (sem login), tenta os últimos
  6 meses até achar um publicado
- Lê a aba `ISD` (Insumos **Sem Desoneração** — regime confirmado com Dennis), filtra
  `Classificação = MATERIAL`, usa a coluna de preço do Paraná
- Nova tabela `insumos_sinapi(codigo, descricao, unidade, preco_pr, mes_referencia, fabricante,
  atualizado_em)` — reexecutar o script atualiza preço/descrição por código, mas **nunca sobrescreve
  `fabricante`**, que fica pra Dennis preencher aos poucos
- Testado de ponta a ponta contra produção: 4.365 insumos de material importados (referência
  05/2026), e testada a idempotência (setei um fabricante manualmente, reexecutei o script, valor
  preservado)

**Deliberadamente não implementado ainda:** nenhum vínculo com `bot.py` — nem matching automático
de item de orçamento, nem tela no Telegram, nem `FOREIGN KEY` com `documentos`/`lancamentos`. É
tabela de referência pura por enquanto. Dennis apontou o gatilho real: isso importa de verdade na
fase que precede o uso operacional da Laura — montar uma **lista de compras** — e essa fase só
começa depois de subir as informações pendentes de GGV03 (ver Objetivo da Próxima Sessão).

---

**Pagamento parcelado + ciclo de assinatura de recibo** *(2026-07-01)*

Testando a Fiada 6b com um orçamento real (Sabiá/Valdir Aparecida Silveira, GGV03-001, R$ 70.000
de mão de obra), veio à tona que pagamentos de mão de obra normalmente são parcelados — a cada
~14 dias, valor livre, sem cronograma fixo — e cada parcela paga precisa do próprio recibo,
assinado pelo prestador via gov.br, antes de fechar. O modelo antigo (1 pedido = 1 pagamento =
1 recibo) não suportava isso. Dennis pediu para estender pra **todos os pedidos**, não só mão
de obra — é assim que "à vista" e "parcelado" vão conviver no mesmo mecanismo.

**Implementado:**
- Nova tabela `parcelas_pagamento`: cada comprovante recebido vira uma parcela própria (valor,
  data, comprovante, recibo, recibo assinado, status) — não fecha mais o pedido de uma vez
- Pedido só fica `pago` quando a soma das parcelas atinge o valor total; até lá continua `a_pagar`,
  mas o cockpit mostra "R$X de R$Y pago" em vez de um "aguardando pagamento" genérico
- Recibo passou a ser **por parcela**, não por pedido — `_gerar_recibo()`/`_gerar_html_recibo()`
  reescritos para receber `parcela_id`
- Tela nova "💰 Ver parcelas": lista cada parcela com status (Pago sem recibo → Aguardando
  assinatura → Assinado) e a ação disponível para cada uma
- Fluxo de retorno: botão "📎 Anexar recibo assinado" — Dennis reenvia o PDF/foto assinado, Laura
  sobrescreve o rascunho em `05 Entrega` com o mesmo nome de arquivo (mesmo padrão já usado nas
  revisões de PFM) e marca a parcela como `assinado`
- Recibo em PDF ajustado após feedback direto no teste real: A5 paisagem (não A4), "RECIBO" e o
  código do pedido em linhas separadas (não concatenados), espaço de assinatura para o prestador,
  sem o bloco da VII duplicado no cabeçalho (já aparece como CONTRATANTE no corpo)
- Housekeeping: `StatusPedido.PAGO_COM_RECIBO` (mecanismo antigo, por pedido) removido do código;
  o único registro real que usava (GGV03-001) foi migrado para uma parcela

**Esclarecimento de identidade societária, mesma sessão:** Dennis explicou que "DeltaD" é o nome
fantasia de Verschoor Construções Civis Ltda (CNPJ 48.494.891/0001-06, confirmado no cartão CNPJ
em `OneDrive\DeltaD`), diferente da VII/Verschoor Investimentos Imobiliários Ltda (CNPJ
58.358.802/0001-58, dona dos empreendimentos, confirmado em `OneDrive\VII`) — a constante `DELTAD`
no código sempre teve os dados da VII, só com nome histórico errado. Por decisão de Dennis, a
DeltaD **não participa do fluxo de compras** (é só mais um fornecedor da VII) — nenhuma mudança
de dado foi necessária, só um comentário no código esclarecendo a confusão de nomes.

Testado de ponta a ponta com pedido real (GGV03-001): parcela parcial, recibo gerado, assinatura
simulada, segunda parcela completando o valor total, pedido fechando corretamente.

**Pendência real, não é da Laura**: o recibo de GGV03-001 ainda não foi enviado pro Valdir assinar
de verdade — o teste de hoje validou o mecanismo, não o ciclo completo com assinatura real.

---

**Fiada 6b — Geração automática de recibo** *(2026-07-01)*

Complementa a fiada anterior: enquanto taxa/imposto/serviço público já tem seu próprio documento
de fechamento (a fatura), fornecedor/prestador informal (mão de obra autônoma, sem CNPJ) não tem
documento nenhum — aqui a Laura precisa gerar o recibo, não só arquivar algo que já existe.

**Implementado:**
- Novo status `pago_com_recibo` (`StatusPedido.PAGO_COM_RECIBO`)
- Cockpit do pedido pago sem NF-e (fora das categorias taxa/imposto/serviço, já resolvidas)
  ganha o botão `📄 Sem NF — gerar recibo`
- Motivo da exceção com sugestões prontas (Autônomo sem CNPJ · Prestador informal · Órgão/entidade
  sem NF-e · Outro) — mesmo padrão já usado nas observações de entrega
- `_gerar_html_recibo()` + `_html_para_pdf()` (Playwright): CONTRATANTE é `DELTAD["nome"]`
  ("Verschoor Investimentos Imobiliários Ltda" — dono real do empreendimento, não "DeltaD
  Engenharia", que é só o rótulo de marca do cabeçalho do PFM), CONTRATADO é o fornecedor/prestador
- Recibo arquivado em `05 Entrega/` com a convenção já existente; registrado como `documentos`
  (tipo `recibo`) para poder ser visualizado depois pelo cockpit (`📄 Recibo`)
- `fornecedores.emite_nf` marcado automaticamente ao gerar o primeiro recibo do fornecedor
- Nova coluna `lancamentos.doc_id_recibo`

Testado de ponta a ponta com prestador fictício (Jhonatan Rogowski/MO Pintura): botão aparece só
quando deveria, PDF gerado e arquivado, status muda pra `pago_com_recibo`, `emite_nf` marcado
quando o fornecedor existe no cadastro, cockpit atualizado com "Pago · Recibo emitido".

---

**Taxas, impostos e serviços públicos no fluxo de compra** *(2026-07-01)*

Dennis levantou a dúvida de como tratar despesas sem orçamento negociado — CREA, ONR
(matrícula/emolumentos), prefeitura (IPTU/taxas), Copel (energia), Sanepar (água/esgoto). A
decisão foi reaproveitar o pipeline de compra inteiro (orçamento → PFM → pagamento), em vez de
criar um fluxo paralelo — mudando só a categoria e o critério de fechamento.

**Pesquisa antes de decidir:** antes de mudar a exigência de NF-e (regra existente por causa do
RET), pesquisei o que cada entidade realmente emite. Achado principal: **nenhuma delas tem um
documento fiscal separado da fatura** — Copel já é a própria NF (NF3e, obrigatória desde 2021);
Sanepar, CREA e prefeitura não emitem nota fiscal, só fatura/boleto/guia; ONR disponibiliza
recibo de emolumentos. Ou seja, a fatura que Dennis já envia como orçamento **é** o documento de
fechamento dessas categorias — não falta nada, só não deve ser tratada como se faltasse NF-e.
Fonte: pesquisa web, não é orientação tributária — Dennis vai confirmar com o contador se
necessário, risco avaliado como baixo.

**Implementado:**
- Prompt reconhece boleto/fatura/conta de consumo como `[orcamento]` (antes só reconhecia cotação
  de material — corria risco de cair em "não relacionado")
- Categorias `taxa`/`imposto`/`servicos` (`CATEGORIAS_SEM_NFE_OBRIGATORIA`) fecham o pedido com
  "Pago" simples — sem cobrar NF-e que a entidade não emite
- Ao confirmar o pagamento dessas categorias, a fatura original é arquivada de novo em
  `01 Controle financeiro` como "fatura" (a terceira via), junto do comprovante
- Documento do Pedido de Compra oculta campos de entrega (DATA DE ENTREGA, DADOS PARA ENTREGA,
  aviso de foto, título muda para "CONDIÇÕES DE PAGAMENTO") quando a categoria é taxa/imposto/
  serviço — não faz sentido pedir endereço de entrega pra uma anuidade do CREA
- Novo campo `categoria` no `Pedido` (antes não existia, cockpit não sabia a categoria do pedido)

Testado de ponta a ponta com fatura fictícia de CREA: rótulo de status, arquivamento da fatura
como terceira via, e documento gerado sem os campos de entrega — comparado lado a lado com um
pedido de material pra garantir zero regressão.

**Próximo passo natural, ainda não implementado:** geração automática de recibo (Fiada 6b) para
os casos onde não existe NENHUM documento de fechamento — ex: mão de obra informal sem CREA/CNPJ.
Diferente do que foi resolvido hoje (entidades que têm seu próprio documento), aqui é a Laura que
precisa criar o recibo (PDF via Playwright: serviço + pagamento + partes).

---

**Organização automática de arquivos por obra** *(2026-07-01)*

Antes de colocar a Laura para rodar, Dennis pediu que documentos passassem a se organizar sozinhos
na pasta OneDrive de cada obra, seguindo a convenção que ele já usa manualmente. Feito em 3 fiadas:

- **Fiada 1 — Orçamento + PFM → `04 Compras`**: novo campo "Resumo da compra" no PROMPT (2-4
  palavras, ex: "Espelho"); PFM salvo como `GGV03-008 - Fornecedor - Resumo.docx` (+ `.pdf`, que
  agora também é persistido, não só enviado pelo Telegram); orçamento original arquivado em
  `04 Compras/00 Orçamentos/`; revisão sobrescreve o arquivo principal mantendo o nome correto.
  Nova coluna `documentos.caminho_pfm` — resolve a dívida técnica antiga de reconstruir o caminho
  a cada consulta.
- **Fiada 2 — Comprovante + NF-e → `01 Controle financeiro`**: nome com data real do documento
  (pagamento / emissão da NF-e), não a data de hoje — `AAAA-MM-DD GGV03-002 Carlessi - comprovante.pdf`.
  Corrigido um bug pego durante o próprio teste: datas por extenso ("23 de junho de 2026") caíam
  no fallback de hoje; NF-e não tinha a mesma normalização que o comprovante já tinha.
- **Fiada 3 — Fotos de entrega → `05 Entrega`**: numeração sequencial (`foto01`, `foto02`...),
  extensão original preservada. Recibo (Fiada 6b, ainda não implementado) vai cair no mesmo lugar.

**Correção estrutural no meio do caminho**: `obras.pasta_onedrive` mudou de significado — antes
apontava direto para uma pasta específica (`04 Compras`), agora guarda a **raiz da obra**
(`00 Obras/2026-06 GGV03`), da qual `_pasta_pfm()`, `_pasta_controle_financeiro()` e
`_pasta_entrega()` derivam cada subpasta por convenção. Pego e corrigido durante a própria fiada,
antes de compor com Fiada 2/3.

**Escopo por obra**: GGV03 totalmente configurada (raiz + convenção nova). GGV00 configurada
(pasta vazia, cria a estrutura na primeira vez que precisar). GGV01 **intocada** — regra explícita
de Dennis, nunca mexer na estrutura ou arquivos dela. GGV02 (em conclusão) ainda sem `pasta_onedrive`
configurada — a pasta real dela usa uma organização bem diferente da GGV03 (sem "00 Orçamentos",
com "51 Obra - Materiais e serviços"), decisão de onde encaixar fica pendente.

Todas as três fiadas testadas de ponta a ponta com as funções reais do bot.py (sem duplicar lógica
em script à parte), incluindo múltiplas fotos, revisão de PFM e datas em formatos variados.

---

**Auto-cadastro de fornecedor via Receita Federal** *(2026-07-01)*

- Coluna `fornecedores.receita_pendente` — marca cadastro que ainda não foi validado
- `_criar_fornecedor_auto()`: ao gerar PFM com CNPJ que não bate com nenhum fornecedor conhecido,
  cadastra automaticamente. Tenta a consulta à Receita (BrasilAPI, timeout 4s) na hora; se
  responder, grava razão social/cidade/UF oficiais; se não, cadastra só com o que o Claude
  extraiu e marca `receita_pendente=1` — nunca trava a geração do PFM
- `_sincronizar_receita_pendentes()`: job do `JobQueue` (a cada 6h) tenta de novo só os pendentes.
  Silencioso quando não há pendência; manda mensagem (Jeito da Laura) só quando sincroniza algo:
  "📋 Receita sincronizada — N de M pendências resolvidas"
- Nova dependência: `python-telegram-bot[job-queue]` (traz `apscheduler`) — adicionada ao `pyproject.toml`
- Testado de ponta a ponta contra as funções reais do bot.py (CNPJ válido resolve na hora, CNPJ
  inexistente fica pendente sem travar, mensagem de sincronização parcial confere)

---

**Preparação para produção — migração + limpeza de dados** *(2026-07-01)*

- **Migração de schema em produção**: `data/laura.db` estava rodando com schema anterior à Fase 4a
  (bot só era testado via `LAURA_ENV=test`). Aplicado o mesmo `init_db()` do bot.py — criou `obras`
  (populada com GGV00-03), `entrega_fotos`, e todas as colunas de `lancamentos`/`documentos`/
  `fornecedores` que faltavam. Aditivo, sem perda de dado. Backup em `data/laura.db.backup-2026-07-01`.
- **Fornecedores validados contra a Receita Federal** (API pública BrasilAPI): 28 → 27 cadastros
  (1 duplicata removida). Corrigido CNPJ da MO Construção (estava com o CNPJ da própria DeltaD —
  é pessoa física, CPF de Valdir Aparecido Silveira), chave PIX da Costa Ferro (estava com CNPJ da
  Base Forte) e do Jhonatan Rogowski (valor inválido "pix:"), cidade/UF de 22 cadastros (UF estava
  100% vazia; 9 cadastros tinham cidade poluída com o nome do próprio Dennis/DeltaD), razão social
  truncada em 6 casos, e 6 nomes que eram descrição de item em vez de fornecedor (ex: "Aco 6_3" →
  "Frísia"; "Tubo concreto 400" → "Roma Pré-Moldados"). Cadastro de Claudemir Bueno completado com
  CNPJ confirmado pelo próprio Dennis.
- **`documentos` e `lancamentos` de produção zerados por decisão de Dennis** — os 38 documentos e
  2 lançamentos existentes eram uma mistura de teste inicial (bugs de fase 1, uploads abandonados)
  com 19 PFMs reais sem rastreamento financeiro completo (17 deles nunca ganharam lançamento, pois
  `registrar_lancamento()` não existia ainda quando foram criados). Em vez de reconciliar,
  Dennis optou por começar limpo. **Os arquivos .docx/.pdf já gerados na pasta OneDrive do GGV03
  não foram apagados** — só o rastreamento interno do banco. Numeração de PFM reinicia em 001.

---

**Fase 6 — Fiada 6c++ — Múltiplas fotos de entrega + navegação** *(2026-06-30)*

- Tabela `entrega_fotos`: suporta N fotos por pedido, cada uma com legenda própria
- Legenda obrigatória ao anexar qualquer foto ou documento de entrega
- Tela "👀 Ver arquivos" lista as fotos por legenda; ícone 📷 para foto, 📄 para PDF
- Remoção de foto individual (lista por legenda), sem afetar as demais
- Singular/plural corrigido e recalculado sempre do banco ("1 arquivo" / "N arquivos")
- `← Voltar` adicionado aos submenus Ajuda e Obras, retornando ao menu inicial
- Ícone do botão "Apagar entrega" trocado para `❌` (diferenciado de "Remover arquivo" `🗑`)
- Coluna legada `lancamentos.doc_id_entrega` parou de ser lida/escrita (substituída por `entrega_fotos`)
- **ADR-003 registrada:** avaliada e adiada a extração do domínio entrega de `bot.py` — ver `docs/decisoes/ADR-003-extracao-entrega-adiada.md`

---

**Fase 6 — Fiada 6c+ — Gestão completa de entrega** *(2026-06-30)*

- Tela de gestão `✏️ Editar entrega` acessível pelo cockpit quando entrega registrada
- Mudar observação: seletor de obs com ← Voltar; suporta texto livre
- Trocar/anexar foto: substitui `doc_id_entrega` sem alterar obs ou data
- Remover foto: limpa só o documento, mantém obs e `entregue_em`
- Apagar entrega: zera obs + foto + data; cockpit volta a exibir `📦 Entregue`
- `📎 Foto / Documento` na tela de obs permite anexar antes de confirmar observação
- Cockpit: exibe `📦 Foto de entrega` + `✏️ Editar entrega` quando há obs e foto

---

**Fase 6 — Fiada 6c — Foto de Entrega e Registro de Entrega** *(2026-06-30)*

- Novo tipo de documento `foto_entrega` — sem análise Claude, vai direto à seleção do pedido
- `/entrega`: lista pedidos pendentes → seleciona → observação → grava
- Botão `📦 Entregue` no cockpit; vira `📦 Foto de entrega` quando foto vinculada
- Sugestões de observação: Completa · Parcial · Avaria · Produto diferente · Outra
- Colunas `doc_id_entrega`, `obs_entrega`, `entregue_em` em `lancamentos`

---

**Sprint de Experiência — Jeito da Laura** *(2026-06-30)*

- **Jeito da Laura** formalizado em `IDENTIDADE_DO_PRODUTO.md` e `PROCESSO.md` como princípio de comunicação assertiva; gatilho: "Esta mensagem resolve alguma coisa?"
- Revisão completa de todos os menus pelo Jeito da Laura

---

**Sprint de Experiência — Redesign de Cockpits** *(2026-06-30)*

- Cockpit do pedido: header compacto, financeiro consolidado, sem CNPJ/labels redundantes
- Botão PDF regenera via Playwright; histórico completo com entrega prevista e valor pago
- Cockpit da obra: header limpo, placeholder financeiro, CEP removido, botão Fechar
- Lista de pedidos da obra: tela própria via "📋 Pedidos", navegação direta ao pedido

---

**Fase 5 — Fiada 5a-1 — Categoria no Lançamento** *(2026-06-30)*

- `sugerir_categoria()` integrada ao fluxo do PFM em `bot.py`
- Tela de categoria exibida antes de gerar o pedido: sugestão com [✅ Confirmar] ou grade de seleção quando sem sugestão
- `registrar_lancamento()` e `gerar_pfm()` recebem `categoria` como parâmetro
- Categoria exibida na mensagem pós-PFM e na tela Financeiro do pedido
- Modo teste: deduplicação por `identificador_comprovante` bypassada (duas ocorrências)

---

**Fase 5 — Módulo Financeiro: Fiada 0 — Fundação** *(2026-06-30)*

- ADR-002 registrada: modularização incremental por domínio
- `financeiro/__init__.py` — docstring de contrato do domínio
- `financeiro/lancamento.py` — enums (`CategoriaLancamento`, `StatusLancamento`, `TipoDocumento`), `sugerir_categoria()`, `init_db_financeiro()`
- `financeiro/conciliacao.py` — esqueleto documentado (Fase 5d)
- `app/README.md` — elimina ambiguidade sobre uso da pasta `app/`
- `bot.py`: `init_db()` chama `init_db_financeiro(DB_PATH)` ao iniciar
- Colunas adicionadas em `lancamentos`: `categoria`, `tipo_documento`, `fonte_recurso`, `conciliado_em`

---

**Fase 4b — PC 2.0 parcial + Pendências de extração** *(2026-06-30)*

- PROMPT: 4 novos campos — `Ramo de atividade`, `Número do orçamento`, `Vendedor`, `Telefone do vendedor`
- `fornecedores`: coluna `ramo` adicionada; salva automaticamente ao gerar PFM
- `_gerar_html_pc()`: gera HTML do Pedido de Compra com dados reais
- `_html_para_pdf()`: converte HTML para PDF via Playwright Chromium
- Handler `pfm`: envia PDF em vez de DOCX
- Playwright instalado como nova dependência

---

**Fase 4a — Cadastro de Obras** *(2026-06-30)*

- Tabela `obras` substitui dicts hardcoded (`GGV_ENCARREGADO`, `GGV_DESC`, `GGV_ONEDRIVE`, `ENDERECOS`)
- Cockpit da obra: digitar `GGV03` abre o card com edição campo a campo
- `/nova_obra` para cadastrar novas obras conversacionalmente
- `/help`, comando desconhecido → `/help`, menu de comandos no Telegram

---

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

**Fase 4b — Pedido de Compra 2.0** *(aguarda validação)*

HTML→PDF implementado via Playwright Chromium. Precisa ser testado em produção com orçamento real.
O DOCX ainda é gerado em paralelo (salvo na pasta OneDrive). Remoção do Word fica para depois da validação.

**Fiada 6b — Recibo como Exceção** *(próxima)*

Recibo automático para fornecedores sem NF-e (`emite_nf = false`). Exceção registrada com motivo.

---

## Marcos do Produto

- **v0.1–0.3** — Fundação de engenharia: arquitetura, processo, documentação
- **v0.4–0.5** — Ciclo financeiro completo: orçamento → pedido → a pagar → pago
- **Sprint de Produto (2026-06-29)** — Identidade definida: quem a Laura é, o que ela promete, como ela fala
- **Sprint de Experiência Fase 2 (2026-06-29)** — Tela de validação do orçamento redesenhada; processo de desenvolvimento formalizado com Sessão de Produto e etapa 2.5

---

## Dívidas Técnicas Conhecidas

- **Pipeline de confirmação de documento diverge por ponto de entrada** (2026-07-04): achado
  ao unificar `lista_materiais` — `_cb_sel_tipo_inicial()`, `_cb_set_tipo()` (bug real: sempre
  mostra tela de orçamento, não importa o tipo) e `_cb_ok()` (comprovante_pix incompleto,
  nota_fiscal nem trata) fazem o mesmo objetivo de três formas diferentes. Não corrigir dentro
  de outra fiada — ver "Motor de Interpretação e Classificação de Documentos" em `docs/ROADMAP.md`.
- **9 índices de `data/laura.db` não persistidos em código** (2026-07-03): criados diretamente no
  banco vivo, sem `CREATE INDEX` em `bot.py` ou script versionado — um banco recriado do zero não
  os recria, performance de consulta regride silenciosamente até rodar o comando manual de novo.
- `bot.py` com 4.994 linhas — parcialmente modularizado (ADR-004, 2026-07-02): dispatch table +
  módulo `nfe/` extraído. `fornecedor/`, `obra/`, `comprovante/` avaliados e adiados com gatilho
  próprio (ver ADR-004); extração do domínio `entrega/` continua adiada (ADR-003, motivo não mudou)
- `gerar_pfm()` acumula responsabilidades: gravação no banco + criação de lançamento + arquivamento
  em disco (a geração de documento em si — Word — foi removida em 2026-07-02)
- `mime_type` não gravado no banco — inferido pela extensão do arquivo
- Deduplicação de comprovante por `identificador_comprovante` não atua quando Claude
  não extrai o ID da transação (comprovante sem número visível)
- **GGV02 sem `pasta_onedrive` configurada** — estrutura real da pasta é diferente da convenção
  nova (GGV03); decisão de onde arquivar pendente (ver Fiada "Organização automática" acima)
- `buscar_candidatos_pix()` faz SQL inline direto contra `lancamentos`/`fornecedores` em vez de
  reusar função de domínio (diferente de `buscar_candidatos_nfe()`, que já faz certo) — mapeado na
  ADR-004, não corrigido
- `_gerar_recibo()` toca 4 domínios numa função de 46 linhas — maior ponto de acoplamento cruzado
  do sistema hoje, mais entrelaçado que `entrega/`; motivo pelo qual `fornecedor/`/`comprovante/`
  não foram extraídos nesta rodada (ver ADR-004)
- `_parse_nfe()` reimplementa limpeza de valor BRL na mão em vez de reusar `_parse_brl()` já
  corrigido — reintroduz o bug da Lição #4 (`docs/LICOES_EXTRACAO.md`) especificamente pra NF-e

---

## Decisões Recentes

- **`LAURA_ENV=prod` reativado (2026-07-06)** — Dennis: "pode colocar no modelo de
  produção." A Lista de Compras (correção campo a campo, PDF, enriquecimento de descrição,
  Consultoria de Recompra) passa a rodar contra `data/laura.db` real — não mais só
  `data/laura_test.db`. Schema atualizado via `init_db()` (ALTER seguro) antes da troca.
- **Consultoria de Recompra sem limiar fixo (2026-07-06)** — Dennis: "pode ser os dois [tempo
  e variação de preço], sem limites de tempo e variação por enquanto." A Tela do Item mostra
  tempo decorrido e variação vs. SINAPI atual como informação neutra, nunca como alerta
  automático — decisão de repetir ou trocar continua sempre humana. Evita engessar uma regra
  antes de aprender com o uso real.
- **Programa vs. IA — critério pra decidir onde investir esforço (2026-07-05)** — bug de
  **programa** (código determinístico: banco, cálculo, exibição) se corrige uma vez e fica
  resolvido pra sempre; julgamento de **IA** (Camada 1/2: interpretar, classificar, decidir
  confiança) nunca chega a "resolvido pra sempre" — melhora com prompt melhor, convive com
  margem de erro residual por natureza. Guia a resposta certa quando um bug aparece: "isso é
  código errado (conserta e nunca mais volta) ou é a IA não acertando sempre (melhora o
  prompt, mede, aceita a margem)?"
- **Glossário determinístico de sinônimos SINAPI — rejeitado por Dennis (2026-07-05)** —
  proposto como mitigação pro problema de "termo coloquial não bate com vocabulário técnico
  do SINAPI" (ex: Brita). Dennis: "não é problema meu hoje... já existe uma biblioteca com
  sinônimos de materiais de construção... SINAPI é referência, o cadastro de milhares de
  lojas tem modelos, tipos, fabricantes." Não construir isso sem gatilho novo.
- **Prioridade da próxima fiada: consultoria de recompra, não vocabulário SINAPI
  (2026-07-05)** — Dennis: "preciso de mais ajuda para repetir a compra... se sinto que não
  vale mais a pena, principalmente por preço, ou indicar outro produto (fabricante e
  modelo, fornecedor ou tipo)." Evoluir a Camada 3 de "achar um preço de referência" pra
  "consultora que ajuda a decidir repetir ou trocar" — Princípios 6 e 9 da Política de
  Compras. Ver Objetivo da Próxima Sessão.
- **"A Laura apresenta primeiro a informação necessária para a decisão. Os detalhes técnicos
  aparecem apenas quando solicitados." (2026-07-04)** — princípio de UX que orienta a tela de
  conferência da Lista de Compras (3 níveis: conferência → edição → análise técnica) e deve
  orientar qualquer tela futura do módulo de Compras. "A Laura deve parecer um comprador
  experiente, não um relatório técnico."
- **"A Laura nunca converte o item comercial para a unidade do SINAPI. A Laura converte a
  referência do SINAPI para a unidade comercial do item." (2026-07-04)** — regra de domínio
  pra qualquer conversão de unidade envolvendo referência externa; a unidade comercial (como
  se compra e negocia) nunca muda em lugar nenhum da interface.
- **Unidade igual é filtro obrigatório pra referência de compra própria, sem conversão
  (2026-07-04)** — diferente da regra acima (que permite converter a referência SINAPI),
  aqui não existe conversão: "comparar as unidades da lista e do pedido, estas devem ser
  iguais, isso não deveria mudar". Menos matches, mas nenhum por coincidência de palavra.
- **"Entradas diferentes podem existir. Processos diferentes não." (2026-07-04)** — princípio
  que emergiu ao redesenhar a Lista de Compras: sempre que o resultado esperado for o mesmo,
  a implementação deve convergir pra um único fluxo interno. Motivou o redesenho completo das
  Fiadas 1/2 de 2026-07-03 e a descoberta da divergência em `comprovante_pix`/`nota_fiscal`
  (ver Dívidas Técnicas). Registrado como visão de longo prazo em `docs/ROADMAP.md`.
- **Snapshot histórico é patrimônio de conhecimento, não só cache de preço (2026-07-04)** —
  `lista_compra_itens` congela SINAPI + referência da Laura por item, pensando numa série
  histórica de anos, não só "não perder o dado". Ver memória `project_snapshots_historicos_compras`.
- **Confiar mas verificar contra o código, não só contra o commit mais recente (2026-07-03)** —
  o checklist do Jeito Claude cobre a leitura da documentação; quando uma fiada proposta parece
  "óbvia demais" (prioridade 🔴 há dias na lista), checar o código real antes de implementar evita
  retrabalho. Ver Última Fiada Implementada.
- **ADR-004 (2026-07-02)** — gatilho de linhas da ADR-003 disparou (bot.py > 3.500 linhas). Processo
  de dois agentes (propor + derrubar) reduziu o escopo original (extrair fornecedor/nfe/obra/
  comprovante + dividir dispatcher) pra só 2 fiadas: dispatch table interna + módulo `nfe/`. Ver
  `docs/decisoes/ADR-004-modularizacao-bot-py.md`.

- **DOCX removido (2026-07-02)** — `gerar_pfm()` só gera PDF desde então; confirmado por Dennis
  durante teste real ("será que realmente precisa disso? eu não vou usar"). Documentos antigos em
  `data/pfms/*.docx` são histórico, não foram apagados.

- **NF-e vinculável a qualquer momento (2026-07-02)** — antes exigia `status='pago'`; caso real
  (GGV03-010, pagamento parcelado com nota já emitida) expôs que isso escondia candidatos legítimos.
  Pagamento (PIX) e NF-e passaram a ser registros paralelos e independentes.

- **Organização automática de arquivos (2026-07-01)** — `obras.pasta_onedrive` passou a guardar a
  raiz da obra, não mais uma subpasta específica; cada tipo de documento deriva sua pasta por
  convenção (`04 Compras`, `01 Controle financeiro`, `05 Entrega`). GGV01 permanece intocável por
  regra explícita; GGV02 aguarda decisão por ter estrutura própria diferente.

- **Reset de produção (2026-07-01)** — `documentos` e `lancamentos` zerados por decisão de Dennis em
  vez de reconciliar 17 PFMs sem lançamento financeiro. Arquivos já gerados no OneDrive preservados;
  só o rastreamento interno reinicia. Fornecedores (27, validados via Receita Federal) e obras
  (GGV00-03) não foram tocados.

- **ADR-003 (2026-06-30)** — Extração do domínio entrega de `bot.py` avaliada e **adiada**. Motivo: os
  dados de entrega não são independentes hoje (amarrados a `lancamentos`, do domínio Financeiro, e a
  `documentos`, do domínio Pedido), e a funcionalidade tem zero horas de uso real em produção. Plano de
  extração completo e gatilho de revisão registrados em `docs/decisoes/ADR-003-extracao-entrega-adiada.md`.

- **Obra vs. GGV (2026-06-29)** — "Obra" é o conceito; "GGV03" é o código da obra; "#GGV03-009"
  é o identificador público do Pedido de Compra. Interface usa "Obra GGV03"; banco mantém coluna
  `ggv` por compatibilidade. `pfm_codigo`, arquivos `.docx` e pastas existentes não serão alterados.
  Migração interna (`ggv` → `obra_codigo`) fica registrada como dívida futura de baixa prioridade.

- Tipo do documento é definido pelo usuário antes da IA — mais confiável e extensível
- `ID da transação` é a chave de deduplicação de comprovante, não o `obs` completo —
  mais curto e estável entre re-extrações do mesmo arquivo
- Proteção de pagamento em duas camadas: antes de listar candidatos + antes de gravar
- Modo teste implementado via variável de ambiente, não via comando Telegram — mais seguro

---

## Objetivo da Próxima Sessão

> Só entram aqui itens acionáveis numa sessão — decisão a tomar ou código a escrever. Pendências
> que resolvem sozinhas com o uso do dia a dia (pagamento de parcela, uso real de uma feature,
> gatilho arquitetural que ainda não ocorreu) não são fiada — ficam em Dívida Técnica/ADR, sem
> duplicar aqui como se fossem tarefa da próxima sessão.

1. **Validar a Consultoria de Recompra ao vivo em produção** — implementada e testada com
   objetos simulados/dados reais fora do Telegram; falta o teste ponta a ponta clicando nos
   botões de verdade, agora que `LAURA_ENV=prod` está ativo
2. **Comparar fornecedores diferentes na Consultoria de Recompra** — adiado por decisão
   explícita do Dennis ("vamos deixar tudo na mesma tela... no futuro podemos pensar em
   filtros e mais opções como comparar fornecedores")
3. **3 correções de exibição diagnosticadas ao vivo, não implementadas** (achadas testando o
   enriquecimento de descrição, ver Última Fiada Implementada de 2026-07-05):
   - Tela do Item não mostra `observacoes` do item (esconde o motivo de uma referência não
     calculada, ex: Cal Hidratada — SINAPI achou o código certo mas não sabia o peso do saco)
   - `_referencia_e_correspondencia` esconde "Correspondência: Alta confiança" quando não há
     preço computável — parece que não achou nada, mas achou
   - Prompt da Camada 1 não traduz termo coloquial pro vocabulário técnico SINAPI (ex: "brita"
     devia virar "pedra britada" na busca; hoje repete literal e erra a busca)
4. **Gerar Pedido de Compra a partir da Lista de Compras + vínculo com orçamento** — a Lista
   de Compras já interpreta, corrige, tem cabeçalho completo, gera PDF e grava de verdade no
   banco; mas ainda é uma ilha — falta o próximo elo da cadeia até virar negociação/pedido real
5. **Testar o fix de deduplicação (Gerar Lista de Compras 2x) e edição de endereço/
   observações reabrindo uma lista já existente** — ambos só testados com objetos simulados
6. **Decidir onde a GGV02 arquiva documentos novos** — estrutura de pasta diferente da GGV03
7. **Alimentar `docs/LICOES_EXTRACAO.md`** sempre que aparecer um novo bug de parsing/extração —
   não só corrigir e seguir (ver [[feedback_documentar_padroes_bugs]] na memória)
8. **Limpeza opcional no OneDrive** — 2 arquivos órfãos do pedido excluído Base Forte/GGV03-006
   antigo (`.docx`, `.pdf` em `04 Compras`); a `- Copy.jpeg` foi feita pelo próprio Dennis
   (backup pessoal) — perguntar se ele quer manter essa antes de apagar
9. **Acesso via Claude Code Remote (celular)** — sem ambiente configurado ainda; ideia de hospedar
   Laura + banco num servidor Proxmox em casa (Eric administra) registrada, não iniciada
10. **Persistir os 9 índices de `data/laura.db` em código** — hoje só existem no banco vivo
11. **Integrar `financeiro/relatorios.py` a `bot.py`** — hoje só roda chamado manualmente, sem
    botão/comando no Telegram
12. **Popular `itens_pedido.insumo_sinapi_codigo`** — coluna existe no schema, nada grava nela
    ainda; é o vínculo real que falta entre item comprado e `insumos_sinapi`
13. **Fiada de investigação — Motor de Interpretação e Classificação de Documentos** — não
    priorizada ainda, mas registrada; entender por que os 3 caminhos de confirmação de
    documento divergiram antes de qualquer código (ver ROADMAP.md)
14. **Aplicar "← Voltar" nos ~25 prompts de texto do resto do bot** — Obra, entrega, recibo,
    `/nova_obra` etc. ainda não têm saída quando aguardam texto livre; feito só na Lista de
    Compras, a pedido explícito do Dennis de tratar o resto como fiada própria

> **Explicitamente rejeitado, não entra na lista**: glossário determinístico de sinônimos
> SINAPI (ex: "brita" → "pedra britada"). Ver Decisões Recentes.

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

*Última atualização: 2026-07-06*
*Responsáveis: Dennis + Claude*
*Próxima revisão: ao final da próxima sessão*
