# Estado do Projeto Laura

> Atualizado em: 2026-07-03 (revisão de documentação — Jeito Claude)
> Sessão: **Sincronização de documentação com o estado real do código**

Implementado nesta revisão: leitura do checklist obrigatório (CONSTITUICAO → PROCESSO → ESTADO →
ROADMAP → ARQUITETURA) expôs que **duas prioridades 🔴 do topo do ROADMAP já estavam resolvidas
havia horas**, sem nenhum documento refletir isso — a vulnerabilidade de segurança e a
estruturação de itens de compra. Ambas corrigidas no código antes desta sessão (commits `a2077f0` e
`95c4717`/`86a82cc`), mas nunca capturadas em ESTADO.md/ROADMAP.md/ARQUITETURA.md/CHANGELOG.md.
Documentos corrigidos; nenhum código novo escrito nesta sessão (ver detalhes na Última Fiada
Implementada). **Sessão anterior (checklist Jeito Claude):** Checklist obrigatório de inicialização
de sessão formalizado em PROCESSO.md Seção 1.0. Memória criada em
`jeito_claude_checklist_obrigatorio.md`. **Sessão anterior a essa (mesmo dia, primeira parte):**
Estratégia de banco otimizado com 9 índices + CLI instantânea (`scripts/consultar.py`) + extrato de
pagamentos consolidado com descrições por categoria, número de ART, valor unitário destacado,
comparação com SINAPI. Laura agora é uma **memória rápida e acessível** (consultas <3ms). **Não foi
implementada** automação de pagamento — aguarda os 3 gatilhos de ADR-004 (dono de
`parcelas_pagamento`, `_total_pago()` com `db_path`, atomicidade de `_gerar_recibo()`). Sessão
2026-07-02: remoção do DOCX, ADR-004 (dispatch table + módulo `nfe/`), recibo com texto narrativo,
correções de matching PIX/NF-e, restrição de custo de IA

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

---

## Última Fiada Implementada

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

- **9 índices de `data/laura.db` não persistidos em código** (2026-07-03): criados diretamente no
  banco vivo, sem `CREATE INDEX` em `bot.py` ou script versionado — um banco recriado do zero não
  os recria, performance de consulta regride silenciosamente até rodar o comando manual de novo.
- `bot.py` com 4.068 linhas — parcialmente modularizado (ADR-004, 2026-07-02): dispatch table +
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

1. **Fechar o GGV03-003** — pagamento parcelado em andamento; falta o restante das parcelas
2. **Decidir onde a GGV02 arquiva documentos novos** — estrutura de pasta diferente da GGV03
3. **Usar entrega em produção real** — deixar o fluxo (foto, legenda, múltiplas fotos, edição) rodar
   no dia a dia antes de qualquer nova decisão sobre extração (ver gatilho da ADR-003)
4. **Considerar revisitar `fornecedor/`/`obra/`/`comprovante/`** quando os gatilhos específicos da
   ADR-004 ocorrerem (dono de `parcelas_pagamento` decidido, `_total_pago()` aceitar `db_path`,
   atomicidade de `_gerar_recibo()` resolvida) — não propor antes disso
5. **Alimentar `docs/LICOES_EXTRACAO.md`** sempre que aparecer um novo bug de parsing/extração —
   não só corrigir e seguir (ver [[feedback_documentar_padroes_bugs]] na memória)
6. **Limpeza opcional no OneDrive** — 2 arquivos órfãos do pedido excluído Base Forte/GGV03-006
   antigo (`.docx`, `.pdf` em `04 Compras`); a `- Copy.jpeg` foi feita pelo próprio Dennis
   (backup pessoal) — perguntar se ele quer manter essa antes de apagar
7. **Acesso via Claude Code Remote (celular)** — sem ambiente configurado ainda; ideia de hospedar
   Laura + banco num servidor Proxmox em casa (Eric administra) registrada, não iniciada
8. **Persistir os 9 índices de `data/laura.db` em código** — hoje só existem no banco vivo
9. **Integrar `financeiro/relatorios.py` a `bot.py`** — hoje só roda chamado manualmente, sem
   botão/comando no Telegram
10. **Popular `itens_pedido.insumo_sinapi_codigo`** — coluna existe no schema, nada grava nela
    ainda; é o vínculo real que falta entre item comprado e `insumos_sinapi`

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

*Última atualização: 2026-07-02*
*Responsáveis: Dennis + Claude*
*Próxima revisão: ao final da próxima sessão*
