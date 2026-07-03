# Roadmap do Projeto Laura

> Atualizado em: 2026-07-03 (produção migrada e limpa; auto-cadastro via Receita; arquivos organizados por obra; taxas/impostos/serviços públicos; recibo automático; pagamento parcelado; base de insumos SINAPI; produção ativada + correções de cadastro ao vivo; enriquecimento de fornecedor via Receita — e-mail, telefone, CNAE; incidente crítico de exclusão de documento + correção; DOCX removido, ADR-004 (modularização), recibo narrativo, matching PIX/NF-e corrigido; **vulnerabilidade de segurança corrigida, itens de compra estruturados (`itens_pedido`), módulo `financeiro/relatorios.py`, BD otimizado (9 índices) + CLI de consultas rápidas**)

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

## Fase — Módulo de Compras

**Fundação conceitual** ✓ *(concluída 2026-07-03)*

Antes de qualquer código, três documentos em sequência constroem o domínio:
- `docs/POLITICA_COMPRAS.md` — princípios: Laura como consultora de compras, nunca
  compradora automática; negociação e decisão comercial sempre humanas; compra planejável
  nasce de necessidade organizada em Lista de Compras, não de orçamento
- `docs/CASOS_DE_USO_COMPRAS.md` — 15 casos de uso em linguagem de negócio + "Três
  Momentos da Laura" (antes/durante/depois) + 7 padrões comuns identificados
- `docs/MODELO_DOMINIO_COMPRAS.md` — objetos conceituais (Lista de Compras, Item da
  Lista, Orçamento, Alerta — cada um com ciclo de vida próprio), eventos,
  responsabilidades Laura/usuário, regras por momento — sem banco de dados/classes/APIs

**Fiada 1 — Criar e consultar Lista de Compras** ✓ *(implementada 2026-07-03, aguardando teste real no Telegram)*

Primeira fiada de engenharia, nasce em módulo próprio `compras/` (ADR-002: todo novo
domínio nasce modular). Escopo: só o momento "antes da compra" — `/lista GGV03` cria ou
reabre a lista da obra, Laura sugere itens recorrentes de `itens_pedido` com o último
preço pago, Dennis adiciona (por botão ou texto livre) e remove itens, lista fica
consultável. Sem vínculo com orçamento, sem alertas proativos (Casos 11-15), sem tocar o
fluxo existente de `gerar_pfm()`.

- `compras/lista.py`: `StatusLista`/`StatusItem`, `init_db_compras()`, `sugerir_itens()`
  (retorna lista vazia se não houver histórico — nunca inventa), `criar_ou_buscar_lista_aberta()`,
  `adicionar_item()`, `remover_item()`, `listar_itens()` — todas recebendo `db_path`
- `bot.py`: comando `/lista`, três callbacks (`lista_add_sug`, `lista_rem_item`,
  `lista_fechar`), parser tolerante de item por texto livre (`_parse_item_lista()`,
  mesmo espírito de `_itens()` — nunca bloqueia)
- Testado via script contra `data/laura_test.db`: sugestão real para GGV03 (histórico
  existente) e "sem histórico" explícito para obra sem nenhum item — critério do Dennis
  cumprido; regressão do fluxo orçamento → pedido confirmada com
  `scripts/teste_gerar_pedido.py`, sem alteração de comportamento

**Fiada 2 — Lista de materiais por foto → Lista de Compras** ✓ *(implementada 2026-07-03, teste real adiado para amanhã)*

Pedido de Dennis no meio da sessão: reaproveitar a mesma lógica já usada pra orçamento
(extração por IA → tela de revisão → confirmar) num ponto mais cedo do processo — a partir
de uma lista de materiais fotografada ou impressa, sem preço nem fornecedor.

- Novo tipo de documento reconhecido: **Lista de materiais** (`lista_materiais`), com
  classificação e template de extração próprios no `PROMPT` — explícito que preço/fornecedor
  nunca devem ser inventados nesse tipo (mesmo cuidado da Lição #1 de `LICOES_EXTRACAO.md`)
- Novo botão no menu de tipo de documento, ao lado de Orçamento/Comprovante/NF-e
- Tela de confirmação (`_resumo_lista_materiais()`) reaproveita o padrão de revisão do
  orçamento, mais simples (sem fornecedor/valor/condição — não existem nesse tipo)
- Ao confirmar, os itens entram na Lista de Compras da obra via `compras.adicionar_item()`
  — mesma função da Fiada 1
- **Ajuste feito ainda hoje, depois do primeiro teste real:** a saída da confirmação
  originalmente caía na tela de edição da Fiada 1 (`_tela_lista_compras`, "adicionar mais
  itens / fechar"). Dennis pediu que a saída fosse uma **lista finalizada**, fechada, sem
  virar modo de edição contínua — implementado como `_tela_lista_finalizada()`, resumo só
  leitura. O modelo/PDF oficial da lista fica para decidir depois; por hoje é texto.
- Testado com dado real do Dennis: 11 itens de material hidráulico (Tigre) extraídos
  corretamente de uma foto real, incluindo obra não identificada → fluxo de definir obra
  → lista finalizada. Confirmado direto no banco de teste, não só por script.
- **Pendente:** Dennis retoma o teste ao vivo amanhã antes de considerar a fiada fechada

**Aprendizado registrado hoje, não implementado:** Dennis apontou que a Lista de Compras
provavelmente precisa de um endereço — o frete faz parte da negociação do orçamento, e sem
saber pra onde entrega, falta informação relevante pra comparar propostas. Não é
prioridade agora (a `Fiada 1`/`2` não usam isso); registrado aqui para quando o Modelo de
Domínio for revisitado. Pode já existir via `obras.endereco_entrega` — decidir se a Lista
de Compras herda isso da obra ou precisa de campo próprio é decisão de implementação futura.

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

**Fase 4b — Pedido de Compra 2.0** ✓ *(concluída — validada e DOCX removido em 2026-07-02)*

Design aprovado em 2026-06-30. Referência: `prints/pc_alternativa_a.html`

Implementado em 2026-06-30:
- `_PC_CSS` — CSS do documento como constante Python
- `_gerar_html_pc(doc_id)` — gera HTML com dados reais do banco
- `_html_para_pdf(html)` — converte para PDF via Playwright Chromium (async)
- PROMPT: 4 novos campos — Ramo de atividade, Número do orçamento, Vendedor, Telefone do vendedor
- `fornecedores.ramo` — coluna adicionada, salva automaticamente ao gerar PFM

Concluído em 2026-07-02:
- Validado em produção; DOCX removido do fluxo principal (`gerar_pfm()` só gera PDF) — confirmado
  por Dennis durante teste real ("será que realmente precisa disso? eu não vou usar")
- Data da negociação: ainda usa `criado_em` como proxy (dívida técnica de baixa prioridade, não
  bloqueante)

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

**Fiada 6b — Geração automática de recibo** ✓ *(concluída 2026-07-01)*

Escopo refinado após a Fiada "Taxas/impostos/serviços públicos": aquela fiada resolveu o caso de
entidades que já emitem seu próprio documento de fechamento (fatura vira a terceira via). Fiada 6b
cobre o caso restante: fornecedor/prestador **sem nenhum documento** (mão de obra informal,
autônomo sem CNPJ) — aqui a Laura gera o recibo, não só arquiva algo que já existe.

- Botão `📄 Sem NF — gerar recibo` no cockpit quando o pedido está pago sem NF-e (categoria fora
  de taxa/imposto/serviço, já resolvidas) — usuário declara explicitamente a exceção com motivo
- Recibo gerado em PDF via Playwright (`_gerar_html_recibo()`): CONTRATANTE é `DELTAD["nome"]`
  ("Verschoor Investimentos Imobiliários Ltda", dono do empreendimento — não "DeltaD Engenharia",
  que é só a marca do cabeçalho do PFM), CONTRATADO é o fornecedor/prestador
- Status novo: `pago_com_recibo`
- Coluna `emite_nf` em `fornecedores` (marcada automaticamente ao gerar o primeiro recibo) e
  `doc_id_recibo` em `lancamentos`
- Recibo arquiva em `05 Entrega/` — mesma convenção já implementada; registrado como `documentos`
  para poder ser visualizado depois pelo cockpit (`📄 Recibo`)

> **Superado em 2026-07-01** pela Fiada "Pagamento parcelado" abaixo: o status `pago_com_recibo`
> e `lancamentos.doc_id_recibo` foram substituídos pelo modelo de parcelas (`parcelas_pagamento`),
> que trata o recibo por parcela, não por pedido inteiro. O mecanismo de geração descrito acima
> (PDF via Playwright, CONTRATANTE = VII) continua o mesmo — só a granularidade mudou.

**Pagamento parcelado + ciclo de assinatura de recibo** ✓ *(concluída 2026-07-01)*

Descoberta ao validar o recibo de GGV03-001 com Dennis: pagamento de mão de obra não é um evento
único. Prestadores como o Valdir recebem em parcelas de valor e período livres ("14 em 14 dias",
"pode me pagar 3.500 amanhã?") até quitar o total combinado — e cada parcela paga precisa do seu
próprio recibo assinado. Por decisão explícita, o modelo vale para **todos os pedidos**, não só
mão de obra: a forma de pagamento já é declarada na criação do pedido, à vista ou parcelado é só
como a Laura entende o mesmo fluxo.

- Nova tabela `parcelas_pagamento`: cada linha é um pagamento parcial vinculado ao `pfm_codigo`,
  com seu próprio ciclo `pago` → `aguardando_assinatura` → `assinado`
- `lancamentos.status` só vira `pago` quando `SUM(parcelas_pagamento.valor) >= lancamentos.valor`;
  antes disso o pedido continua `a_pagar`, mostrando o progresso: "Aguardando pagamento · R$ 3.500,00
  de R$ 70.000,00 pago"
- `pix_pagar` reescrito: cada comprovante recebido vira uma nova parcela (dedup de comprovante
  agora por parcela, não mais por pedido); ao completar o total, o pedido fecha normalmente
- `_gerar_recibo()` passa a ser por parcela (`parcela_id`, não `pfm_codigo`) — cada parcela paga
  gera seu próprio PDF, arquivado em `05 Entrega/` com sufixo `recibo-parcelaN`
- Tela nova "Ver parcelas" no cockpit do pedido: lista cada parcela com valor, data e status;
  botão para gerar recibo, ver recibo pendente de assinatura, ou anexar a versão assinada
- Ciclo de assinatura fechado: Dennis manda o recibo pro prestador assinar fora da Laura (ex:
  gov.br), recebe de volta assinado e reenvia pra Laura via "📎 Anexar assinado" — o arquivo em
  `05 Entrega/` é substituído pela versão assinada e a parcela vira `assinado`
- Recibo em A5 paisagem com espaço de assinatura no rodapé — layout ajustado a partir de feedback
  direto no PDF gerado para GGV03-001 (cabeçalho só "RECIBO" + código + data; nome/CPF do prestador
  como linha de assinatura, não no cabeçalho)
- Status obsoleto `pago_com_recibo` removido do `StatusPedido` (housekeeping — a granularidade
  correta é a parcela, não o pedido)

**Esclarecimento DeltaD × VII** — confirmado via CNPJ oficial (Receita Federal): DeltaD Engenharia
é a marca da Verschoor Construções Civis Ltda (CNPJ 48.494.891/0001-06, responsável técnica pela
obra), enquanto a `DELTAD` no código sempre guardou os dados da Verschoor Investimentos Imobiliários
Ltda — VII (CNPJ 58.358.802/0001-58), dona real dos empreendimentos e CONTRATANTE correta no recibo.
Por decisão de Dennis, a DeltaD não participa do fluxo de compras da Laura — é só mais um fornecedor
da VII quando prestar serviço técnico. Nenhuma restruturação de código, apenas comentário explicativo
sobre a constante `DELTAD`.

Testado de ponta a ponta com o pedido real GGV03-001 (Valdir Aparecida Silveira, R$ 70.000,00):
parcela parcial → progresso exibido corretamente → recibo gerado → assinatura simulada → segunda
parcela completando o total → pedido corretamente marcado `pago`.

**Pendência real, não é da Laura:** o recibo de GGV03-001 ainda não foi enviado pro Valdir assinar
de verdade — o teste de hoje validou o mecanismo, não o ciclo completo com assinatura real.

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

**Auto-cadastro de fornecedor via Receita Federal** ✓ *(concluída 2026-07-01)*

- `_criar_fornecedor_auto()`: fornecedor com CNPJ desconhecido é cadastrado ao gerar o PFM,
  enriquecido com dado oficial da Receita (BrasilAPI) quando a consulta responde a tempo
- Falha na consulta não trava a geração do PFM — fornecedor fica marcado `receita_pendente=1`
- `_sincronizar_receita_pendentes()`: job periódico (6h) tenta de novo os pendentes; avisa
  Dennis só quando resolve algo de fato
- Nova dependência: `python-telegram-bot[job-queue]`

**Organização automática de arquivos por obra** ✓ *(concluída 2026-07-01, em 3 fiadas)*

- `obras.pasta_onedrive` agora guarda a raiz da obra; `_pasta_pfm()`, `_pasta_controle_financeiro()`
  e `_pasta_entrega()` derivam cada subpasta por convenção (`04 Compras`, `01 Controle financeiro`,
  `05 Entrega`)
- Orçamento + PFM arquivados em `04 Compras` com nome `{pfm_codigo} - {Fornecedor} - {Resumo}`;
  novo campo "Resumo da compra" no PROMPT; nova coluna `documentos.caminho_pfm`
- Comprovante + NF-e arquivados em `01 Controle financeiro` com data real do documento
- Fotos de entrega arquivadas em `05 Entrega`, numeração sequencial (`foto01`, `foto02`...)
- GGV03 e GGV00 configuradas; GGV01 intocável por regra; GGV02 pendente (estrutura própria diferente)

**Taxas, impostos e serviços públicos no fluxo de compra** ✓ *(concluída 2026-07-01)*

- Prompt reconhece boleto/fatura/conta de consumo (CREA, ONR, prefeitura, Copel, Sanepar) como `[orcamento]`
- Categorias `taxa`/`imposto`/`servicos` fecham com "Pago" — sem exigir NF-e que essas entidades
  não emitem (pesquisado: nenhuma tem documento fiscal separado da fatura; Copel já é a própria NF)
- Fatura arquivada de novo em `01 Controle financeiro` como "fatura" (terceira via) ao confirmar pagamento
- Documento do Pedido de Compra oculta campos de entrega para essas categorias
- Novo campo `categoria` no `Pedido`; nova constante `CATEGORIAS_SEM_NFE_OBRIGATORIA`

---

**Base de insumos SINAPI (referência)** ✓ *(concluída 2026-07-01)*

Objetivo de longo prazo: reconhecer automaticamente qual insumo de referência (padrão nacional)
corresponde a um item de orçamento com descrição livre de fornecedor, mantendo fabricante como
dado comercial separado. Antes de implementar, houve uma sessão conceitual (não técnica) sobre
premissas, entidades do domínio e armadilhas de equivalência — decisão prática registrada aqui.

- Agentes de engenharia/arquitetura invocados antes de decidir a fonte de dado: descartado o stack
  open-source `AutoSINAPI`/`autoSINAPI_API` (Docker + Postgres + API REST) — Dennis não tem Docker
  instalado, o projeto tem a URL de download oficial quebrada (confirmado testando), a variante API
  não tem modo sem Docker, e é mantido por uma única pessoa
- `scripts/import_sinapi.py`: baixa a planilha oficial que a Caixa publica todo mês, sem login,
  mesmo padrão de `scripts/import_fornecedores.py` (script único, sem serviço externo)
- Nova tabela `insumos_sinapi`: aba "Sem Desoneração", `Classificação = MATERIAL`, preço do Paraná;
  reexecutar atualiza preço/descrição por código mas nunca sobrescreve `fabricante`
- 4.365 materiais importados (referência 05/2026), testado contra produção, idempotência confirmada
- **Deliberadamente sem vínculo com `bot.py` ainda** — tabela de referência pura; o gatilho real
  para conectar isso ao fluxo da Laura é a futura fase "lista de compras" (ver Próximas Fiadas)

**Produção ativada + cadastro retroativo completo de GGV03** ✓ *(concluída 2026-07-01)*

`LAURA_ENV=prod` ativado; banco zerado de novo (incluindo o GGV03-001 de teste do Valdir) pra
começar o cadastro retroativo 100% pelo Telegram, com acompanhamento em paralelo pelo banco.
8 pedidos reais registrados (GGV03-001 a 008): CREA, DeltaD/projetos, DeltaD/gestão (parcelado),
ONR, Costaferro, Carlessi, Espaço Azul, Eletroluz — 7 pagos, 1 em aberto (pagamento parcelado em
andamento, R$2.500 de R$30.000).

- **10 bugs reais** de parsing/extração encontrados e corrigidos ao vivo, catalogados em
  `docs/LICOES_EXTRACAO.md`: template de campos misturado em boleto, fornecedor confundido com
  CNPJ próprio (guard ampliado pra cobrir VII + DeltaD), unidade "m2" sem superíndice quebrando
  regex de item, `_parse_brl` interpretando "R$ 5.000" como 5,00, data sem zero à esquerda virando
  ilegível, documento que falha travando o hash e impedindo reenvio, PIX do fornecedor não
  reaproveitado em pedido novo, filtro de campo vazio só reconhecendo gênero masculino, matching de
  comprovante não reconhecendo pagamento parcial, bloco de entrega do PDF ignorando o endereço real
- Novo botão **"🗑 Excluir pedido"** no cockpit (com confirmação) — apaga lançamento, parcelas,
  entrega e documentos vinculados; nunca mexe em arquivo já arquivado no OneDrive
- **Endereço de entrega preenchido automaticamente** com o padrão da obra assim que o GGV é
  identificado — sem clique manual; ainda editável depois
- Observações do pedido virou campo editável; botão "✖ Cancelar" adicionado na tela de escolha de
  tipo de documento (antes não tinha saída)
- Descoberto e corrigido: dois processos `bot.py` simultâneos causam conflito de polling no
  Telegram — só uma instância por vez
- Botões renomeados pra refletir aceitação de foto ou arquivo, não só um dos dois

**Enriquecimento de fornecedor via Receita — e-mail, telefone, CNAE** ✓ *(concluída 2026-07-02)*

- Bug corrigido: tela de resumo travava "Fornecedor não identificado" mesmo com o fornecedor já
  cadastrado, quando só o CNPJ estava no documento novo — agora consulta `buscar_fornecedor()`
  pra puxar a razão social, no mesmo padrão já usado pra CNPJ/PIX
- `_consultar_receita()` ampliada: além de razão social/cidade/UF, agora extrai e-mail, telefone
  e CNAE (código formatado no padrão oficial do Cartão CNPJ + descrição da atividade principal) —
  tudo já vinha na mesma resposta da BrasilAPI
- Novo campo `fornecedores.cnae`, separado de `ramo` (que continua vindo do documento, com CNAE
  como fallback só quando o documento não especifica)
- Sincronização retroativa aplicada aos 27 fornecedores já cadastrados — 22 ganharam telefone,
  todos os 27 ganharam CNAE (e-mail raramente vem preenchido na Receita)
- Incidente operacional resolvido: bot caiu com "database is locked" porque o DB Browser for
  SQLite estava aberto com o `laura.db` — nunca deixar visualizador de banco aberto com o bot rodando

**Sincronização com a Receita sempre ativa, com política por campo** ✓ *(concluída 2026-07-02)*

Job periódico deixou de mexer só em fornecedor `receita_pendente=1` — agora resincroniza todos os
fornecedores com CNPJ a cada 6h, com três políticas diferentes por tipo de campo:

- Razão social, cidade, UF, CNAE: sempre atualiza com o dado mais recente (oficial, baixo risco)
- Ramo: prioriza o texto natural do documento; CNAE só como fallback quando vazio — "ramo é uma
  coisa, CNAE é outra"
- E-mail, telefone: só preenche se vazio, nunca sobrescreve — risco real de a Receita estar
  desatualizada nesses dois

Função renomeada `_sincronizar_receita_pendentes` → `_sincronizar_receita_fornecedores`. Só grava
e avisa quando algo muda de verdade — sem mensagem repetida a cada 6h sem novidade.

**Incidente crítico: documento de pedido pago apagado por botão antigo — corrigido** ✓ *(2026-07-02)*

`_descartar_documento()` (criado ontem pro botão "Cancelar") apagou o documento raiz do GGV03-007
(já pago) — um botão "Cancelar" de mensagem antiga do Telegram, ainda clicável, disparou o
descarte num documento que já tinha virado pedido de verdade. A função nunca verificava isso.

- Corrigido: `_descartar_documento()` agora recusa apagar documento com `pfm_numero` preenchido,
  a menos que `force=True` (usado só por "🗑 Excluir pedido", com confirmação explícita)
- Botão "Cancelar" mostra alerta claro quando recusa, em vez de falhar silenciosamente
- Lançamento sobreviveu intacto (nunca é tocado por esse descarte); arquivos reais (PFM,
  comprovante, NF-e) continuavam no OneDrive — só o vínculo interno do banco tinha sumido
- Documento reconstruído a partir do PDF real gerado (mesmos valores exatos); restaurado duas
  vezes — a primeira foi apagada de novo antes do bot subir com a correção
- Esclarecimento paralelo: "Base Forte" e "Espaço Azul" são a mesma empresa (nome fantasia); o
  cadastro do fornecedor já estava correto, a confusão era só de nome de arquivo no OneDrive
- Bug adicional: `_obs()` só reconhecia "Observações" em linhas separadas — o formato real sempre
  foi tudo na mesma linha; provavelmente quebrada silenciosamente desde que foi escrita. Corrigida
  pra aceitar os dois formatos, mais `_campo_vazio()` pra não mostrar "não informado" como real
- Navegação simplificada: "Cancelar" virou "← Voltar" nos três lugares onde aparecia; ao clicar
  numa mensagem antiga já vinculada a um pedido, abre o cockpit direto (um clique, não dois)

**DOCX removido + ADR-004 (modularização) + correções de matching PIX/NF-e** ✓ *(concluída 2026-07-02)*

Sessão motivada por um comentário do Eric (filho do Dennis, estudando engenharia de software) de
que `bot.py` parecia "bagunçado".

- `gerar_pfm()` parou de gerar Word — PDF (HTML via Playwright) é o único documento desde então
- Bug de segurança corrigido: `bot.py` não tinha guard `if __name__ == "__main__":` — importar o
  módulo disparava o polling real do Telegram. Corrigido; `import bot` agora é seguro
- Auditoria de bibliotecas (7 agentes, somente leitura): conversor de número por extenso manual
  (~85 linhas) trocado por `num2words`, validado byte-a-byte. Auditoria também encontrou uma
  vulnerabilidade real não corrigida — ver Dívida Técnica
- **ADR-004**: gatilho de linhas da ADR-003 disparou (bot.py em 3.994 linhas). Processo de dois
  agentes (propor + derrubar) reduziu o escopo original — só dispatch table interna em
  `responder_botao()` (929 linhas → 59 funções + dict) e extração do módulo `nfe/` (84 linhas,
  importável sem `bot.py`). `fornecedor/`/`obra/`/`comprovante/` adiados com gatilho próprio
- Recibo ganhou parágrafo narrativo (modelo do Excel antigo do GGV01) com quantidade do item e
  valor por extenso, mantendo o layout em cartão
- `ITEM_RE` corrigido pra aceitar unidade por extenso ("blocos"), não só abreviação — item #11 em
  `docs/LICOES_EXTRACAO.md`
- `buscar_candidatos_pix()` parou de cortar em top-3 — lista todos os pedidos com saldo aberto,
  ordenados por score e proximidade de valor, com total pendente exibido
- Regra de elegibilidade de NF-e mudou: não exige mais `status='pago'` — pagamento (PIX) e NF-e
  são registros paralelos e independentes (caso real: GGV03-010, parcelado, nota já emitida)

---

## Próximas Fiadas

> Só entram aqui itens acionáveis numa sessão — decisão a tomar ou código a escrever. Pendências
> que resolvem sozinhas com o uso do dia a dia (pagamento de parcela, uso real de uma feature,
> gatilho arquitetural que ainda não ocorreu) não são fiadas — ficam registradas em Dívida Técnica
> ou no ADR correspondente, sem duplicar aqui como se fossem tarefa da próxima sessão.

1. **Decidir onde a GGV02 arquiva documentos novos** — estrutura de pasta diferente da GGV03
2. Alimentar `docs/LICOES_EXTRACAO.md` a cada novo bug de parsing/extração encontrado
3. Limpeza opcional de 2 arquivos órfãos no OneDrive (pedido Base Forte/GGV03-006 antigo, excluído)
   — perguntar sobre a `- Copy.jpeg` antes, é backup pessoal do Dennis
4. Acesso via Claude Code Remote do celular — sem ambiente configurado; ideia de hospedar Laura +
   banco num servidor Proxmox em casa (Eric administra) registrada, não iniciada
5. Persistir os 9 índices de `data/laura.db` em código — hoje só existem no banco vivo (nenhum
   `CREATE INDEX` em `bot.py`/scripts); um `init_db()` contra um banco novo não os recria
6. Integrar `financeiro/relatorios.py` a `bot.py` — hoje as funções só rodam chamadas manualmente,
   sem botão ou comando no Telegram
7. Popular `itens_pedido.insumo_sinapi_codigo` — coluna já existe no schema, mas nada grava nela
   ainda; é o vínculo real entre item comprado e `insumos_sinapi` que falta pra fase "lista de compras"

---

### Concluídas fora de ordem, não capturadas antes desta revisão (2026-07-03)

**Correção de segurança** ✓ — `responder_botao()` agora verifica `DONO_ID`; `atualizar()` e
`atualizar_obra()` validam colunas contra allowlist (`_COLUNAS_DOCUMENTO`/`_COLUNAS_OBRA`). Ver
CHANGELOG "[Segurança + módulo financeiro/relatorios.py]".

**Itens de compra estruturados** ✓ — tabela `itens_pedido` (criada em 2026-07-02, junto da
modularização) + `scripts/backfill_itens_pedido.py` (popula pedidos antigos) +
`financeiro/consultas.py::procurar_item()` + `scripts/consultar.py --item <termo>` resolvem o
gatilho original (consultar preço de item já comprado sem ler o texto inteiro do pedido).

---

## Dívida Técnica

- **Baixa — 9 índices de `data/laura.db` não persistidos em código**
  Criados diretamente no banco vivo durante a sessão "Otimização de BD" (2026-07-03) — não existe
  nenhum `CREATE INDEX` em `bot.py` ou em script versionado. Se o banco for recriado do zero
  (`init_db()` contra um arquivo novo), a performance de consulta (<3ms) regride silenciosamente
  até alguém rodar o mesmo comando manual de novo. Baixo risco hoje (banco de produção já tem os
  índices), mas deveria virar parte de `init_db()` ou de um script de migração versionado.

- **Baixa — Separar conceito de Obra do código GGV internamente**
  Decisão 2026-06-29: a mudança é de linguagem e domínio, não de migração imediata.
  Interface já usa "Obra GGV03"; banco mantém coluna `ggv` por compatibilidade.
  `pfm_codigo` (ex: GGV03-009) e links existentes não serão alterados.
  Dívida futura: migrar domínio interno `ggv` → `obra_codigo` em fiada específica.

- **Média — `gerar_pfm()` acumula responsabilidades**
  Grava no banco, cria lançamento e arquiva em disco (a geração do documento em si — Word — foi
  removida em 2026-07-02). Justificativa: dificulta testes e futuras extensões.

- **Baixa — GGV02 sem `pasta_onedrive` configurada**
  Estrutura real da pasta (sem "00 Orçamentos", com "51 Obra - Materiais e serviços") não
  mapeia direto na convenção nova da GGV03. Justificativa: obra em conclusão, decisão de onde
  arquivar documentos novos ainda pendente — ver `ESTADO.md`.

- **Média — `mime_type` não gravado no banco**
  Inferido pela extensão do arquivo ao reprocessar.
  Justificativa: funciona para o MVP; pode falhar para arquivos sem extensão clara.

- **Baixa — deduplicação de comprovante incompleta**
  Se o Claude não extrair `ID da transação`, a proteção por identificador não atua.
  Justificativa: afeta apenas comprovantes sem número de transação visível; raro no MP.

- **Média — `bot.py` com 4.068 linhas, parcialmente modularizado**
  ADR-004 (2026-07-02) extraiu dispatch table + módulo `nfe/`. `fornecedor/`/`obra/`/`comprovante/`
  avaliados e adiados com gatilho próprio (schema de `parcelas_pagamento` não decidido,
  `_total_pago()` usa banco global, atomicidade de `_gerar_recibo()`). Extração de `entrega/`
  continua adiada (ADR-003) — motivo substantivo não mudou, só o contador de linhas.

- **Baixa — `buscar_candidatos_pix()` faz SQL inline direto contra `lancamentos`/`fornecedores`**
  Diferente de `buscar_candidatos_nfe()`, que já reusa função de domínio. Mapeado na ADR-004.

- **Média — `_gerar_recibo()` toca 4 domínios numa função de 46 linhas**
  Maior ponto de acoplamento cruzado do sistema hoje (parcelas, fornecedores, documentos, pedido).
  Motivo pelo qual `fornecedor/`/`comprovante/` não foram extraídos na ADR-004.

- **Baixa — `_parse_nfe()` não reusa `_parse_brl()` já corrigido**
  Reimplementa limpeza de valor BRL na mão — reintroduz o bug da Lição #4 especificamente pra NF-e
  (valores sem centavos, ex: "R$ 10.99", seriam interpretados errado).

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
