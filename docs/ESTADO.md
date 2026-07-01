# Estado do Projeto Laura

> Atualizado em: 2026-07-01
> Sessão: Preparação para produção — migração, limpeza, auto-cadastro via Receita, organização automática de arquivos, taxas/impostos/serviços públicos

---

## Saúde do Projeto

🟢 Verde

- Fundação concluída.
- Ciclo documental completo: orçamento → PFM → A PAGAR → PIX → PAGO → NF-e vinculada.
- PC 2.0 (PDF) implementado mas ainda não validado em produção — DOCX continua funcionando.
- **`data/laura.db` (produção) migrado e pronto** — schema estava desatualizado desde antes da
  Fase 4a (faltavam `obras`, `entrega_fotos`, 12 colunas de `lancamentos`); corrigido em 2026-07-01.
- Cadastro de fornecedores limpo e validado contra a Receita Federal (27 registros).
- `documentos`/`lancamentos` de produção zerados por decisão — numeração de PFM reinicia do zero.
- **Fornecedor novo se auto-cadastra a partir do orçamento**, com dado oficial da Receita quando
  disponível; sincronização automática em segundo plano quando a consulta falha na hora.
- **Documentos organizados automaticamente na pasta OneDrive de cada obra** — orçamento, PFM,
  comprovante, NF-e e fotos de entrega arquivados com nome e pasta padronizados, sem ação manual.
- **Taxas, impostos e serviços públicos** (CREA, ONR, prefeitura, Copel, Sanepar) passam pelo
  mesmo fluxo de compra — categoria dispensa NF-e (essas entidades não emitem), fatura arquivada
  como fechamento, campos de entrega ocultos no documento gerado.
- Módulo Financeiro: fundação criada (`financeiro/`). Sem funcionalidade nova ainda.

---

## Versão Atual

**v0.6.5** — Taxas, impostos e serviços públicos no fluxo de compra

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
- Recebimento e vinculação de NF-e ao pedido pago
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

---

## Última Fiada Implementada

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

- `bot.py` monolítico com 3277+ linhas — acima do limite ADR-001 (2.500–3.000); extração do domínio entrega avaliada e **adiada por decisão** (ADR-003), com gatilho de revisão explícito — não é mais "refatoração prioritária", é "aguardando gatilho"
- `gerar_pfm()` acumula responsabilidades: geração Word + gravação no banco + criação de lançamento + arquivamento em disco
- `mime_type` não gravado no banco — inferido pela extensão do arquivo
- Deduplicação de comprovante por `identificador_comprovante` não atua quando Claude
  não extrai o ID da transação (comprovante sem número visível)
- **GGV02 sem `pasta_onedrive` configurada** — estrutura real da pasta é diferente da convenção
  nova (GGV03); decisão de onde arquivar pendente (ver Fiada "Organização automática" acima)

---

## Decisões Recentes

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

1. **Fiada 6b — Geração automática de recibo** — combinado com Dennis para avançar a seguir;
   escopo: fornecedor/prestador sem nenhum documento de fechamento (mão de obra informal etc.),
   Laura gera o recibo em PDF (serviço + pagamento + partes). Diferente das taxas/impostos/serviços
   públicos resolvidos hoje — aqueles já tinham fatura própria servindo de fechamento
2. **Colocar a Laura para rodar em produção** — banco migrado e limpo; falta decidir sobre `LAURA_ENV`
3. **Decidir onde a GGV02 arquiva documentos novos** — estrutura de pasta diferente da GGV03
4. **Usar entrega em produção real** — deixar o fluxo (foto, legenda, múltiplas fotos, edição) rodar
   no dia a dia antes de qualquer nova decisão sobre extração (ver gatilho da ADR-003)
5. **Validar PC 2.0** — testar PDF com orçamento real; remover DOCX após validação

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

*Última atualização: 2026-07-01*
*Responsáveis: Dennis + Claude*
*Próxima revisão: ao final da próxima sessão*
