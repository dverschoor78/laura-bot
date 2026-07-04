# Roadmap do Projeto Laura

> Atualizado em: 2026-07-04 (**módulo de Compras redesenhado — Camada 1 interpretação
> unificada, snapshot histórico SINAPI+Laura, FTS5 de busca, Lição #12 corrigida; achado
> arquitetural registrado — Motor de Interpretação e Classificação de Documentos**); histórico
> anterior: produção migrada e limpa; auto-cadastro via Receita; arquivos organizados por obra;
> taxas/impostos/serviços públicos; recibo automático; pagamento parcelado; base de insumos
> SINAPI; produção ativada + correções de cadastro ao vivo; enriquecimento de fornecedor via
> Receita — e-mail, telefone, CNAE; incidente crítico de exclusão de documento + correção;
> DOCX removido, ADR-004 (modularização), recibo narrativo, matching PIX/NF-e corrigido;
> vulnerabilidade de segurança corrigida, itens de compra estruturados (`itens_pedido`),
> módulo `financeiro/relatorios.py`, BD otimizado (9 índices) + CLI de consultas rápidas

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

**Fiada 1 — Redesenhada em 2026-07-04, depois do primeiro teste real**

As duas fiadas separadas implementadas em 2026-07-03 (`/lista` item-a-item + foto→confirmar)
foram **substituídas**, não complementadas, depois que Dennis testou ao vivo e pediu um
redesenho conceitual: a Lista de Compras deve nascer com a mesma lógica de segurança do
Pedido de Compra — a IA interpreta o que for enviado (texto, foto ou PDF) de uma vez só,
tenta padronizar cada item contra o SINAPI, e só grava depois de conferência/edição humana.
Nada do código de 2026-07-03 sobreviveu à reescrita; as duas fiadas antigas ficam registradas
aqui só como histórico da decisão, não como estado atual — ver ESTADO.md para a crônica
completa do que mudou e por quê.

Escopo confirmado do redesenho:
- Entrada única (texto/foto/PDF) por dois pontos de disparo (`/lista` ou botão no menu de
  documento) que **convergem pra mesma função** — não duas implementações paralelas
- Cada item tenta casar com SINAPI (busca de candidatos + Claude escolhe ou declara "sem
  correspondência confiável") — abordagem em duas etapas (FTS5 filtra, IA decide), não
  substring simples
- Referência de último preço pago da própria Laura, mostrada ao lado, não misturada com
  sugestão de item novo
- Dois **snapshots** por item, congelados no momento da confirmação e nunca recalculados
  depois (`CONSTITUICAO.md` — "Dados são sagrados"): snapshot SINAPI (código, descrição,
  unidade, preço, mês de referência) e snapshot da referência interna da Laura (preço, data,
  fornecedor, origem, grau de confiança) — ver memória `project_snapshots_historicos_compras`
  pro raciocínio completo (série histórica de preço, medir confiabilidade do SINAPI ao longo
  do tempo)
- Endereço de entrega herdado da obra na tela de conferência, sem virar atributo novo do
  objeto Lista de Compras (evita reabrir o Modelo de Domínio, que Dennis marcou como encerrado)
- Ainda fora de escopo: vínculo com orçamento recebido, qualquer mudança no fluxo
  orçamento → pedido

**Camada 1 — Interpretação** ✓ *(implementada e testada 2026-07-04)*

- `PROMPT_INTERPRETAR_LISTA`: prompt dedicado, não passa pela classificação compartilhada
  do orçamento — sabe de antemão que é uma lista, nunca inventa preço
- `_interpretar_lista_texto()`/`_interpretar_lista_arquivo()`: mesma função pros dois pontos
  de entrada (`/lista` e botão "📝 Lista de materiais" no menu de documento) — testado
  estruturalmente que chamam o mesmo código, não duas cópias
- Testado com texto digitado e com a foto real de material hidráulico (11 itens Tigre) que
  motivou o redesenho — extração correta nos dois formatos
- **Bug real encontrado e corrigido (Lição #12 de `LICOES_EXTRACAO.md`):** marca/fabricante
  (ex: "Quartzolit") sendo confundida com unidade de medida quando aparece perto da
  quantidade no texto original. Prompt corrigido nos dois lugares que ainda tinham essa
  falta (o novo dedicado e o antigo compartilhado, antes de esse último ser aposentado)
- **Limpeza feita junto:** removido todo o código das duas fiadas de 2026-07-03 que ficou
  órfão com o redesenho — `_tela_lista_compras`, `_teclado_lista_compras`,
  `_abrir_lista_compras`, `_parse_item_lista`, `_resumo_lista_materiais`,
  `teclado_lista_materiais`, `_tela_lista_finalizada`, `_cb_lista_mat_confirmar`,
  `_cb_lista_fechar`, `_cb_lista_add_sug`, `_cb_lista_rem_item`, e `[lista_materiais]` saiu
  do `PROMPT` compartilhado de classificação
- Ainda não grava nada em `listas_compra`/`lista_compra_itens` — é leitura/interpretação,
  pré-confirmação

**Camada 1 — Reescrita pra saída estruturada (JSON)** ✓ *(2026-07-04, mesmo dia)*

Teste com tabela real (planilha de 8 itens: cimento, argamassa, forro PVC, cal, porcelanato,
revestimento, rejunte, acabamento) expôs que o formato de saída original — uma linha de texto
por item, casada por regex — forçava a IA a "achatar" uma tabela em texto corrido antes de
responder. Sintomas: quantidade virando "1" quando a coluna real dizia outro valor, unidade
errada, fabricante nunca separado, código de referência alterado (`72707/72745` virou
`27707/72745`).

- `PROMPT_INTERPRETAR_LISTA` reescrito em duas partes: **procedimento** (detectar tabela →
  identificar linhas → separar colunas de descrição/unidade/quantidade → só então interpretar
  semanticamente) e **regras** (quantidade/unidade nunca inventadas — `null` em vez de
  chute; código de referência é identificador, copiado literalmente, nunca "corrigido";
  prioridade explícita: coluna da tabela > texto lido > interpretação da IA)
- Saída agora é array JSON (`numero`, `descricao`, `fabricante`, `codigo`, `unidade`,
  `quantidade`, `observacoes`) em vez de uma linha de texto por item
- `_itens_lista_materiais()` reescrita: `json.loads()` no lugar do regex antigo
  (`_ITEM_LISTA_MATERIAIS_RE`, removido), com fallback defensivo — JSON malformado vira
  itens em string, nunca perde item silenciosamente
- `_texto_itens_interpretados()` mostra fabricante e código quando existirem, e diz
  explicitamente "quantidade não identificada"/"unidade não identificada" em vez de omitir
- **Validado contra a tabela real como gabarito**: com o texto colado (garbled), 8/8 itens
  corretos — quantidade, unidade e código batendo, incluindo o código do porcelanato. Com a
  foto real, 5/8 perfeitos; os 3 restantes têm imperfeição de campo (unidade "m" em vez de
  "m2" num item, fabricante vazio em outro, um item com quantidade/unidade genuinamente
  ilegível na foto) — mas **nenhum inventou valor errado**: o pior caso retornou `null` e
  disse isso claramente, em vez de "1 SC" como acontecia antes. Mudança de natureza do erro:
  de "confiante e errado" para "incerto e visível". Aceito por Dennis nesse nível — refino
  adicional do prompt fica pra depois, se necessário

**Camada 2 — Candidatos SINAPI (busca FTS5 + Claude decide)** ✓ *(2026-07-04, mesmo dia)*

Uma única chamada extra ao Claude decide a correspondência da lista inteira (não uma por
item): `_candidatos_sinapi()` busca por palavra-chave via `insumos_sinapi_fts` (recall alto,
não precisão — é só o filtro inicial), `_adicionar_correspondencia_sinapi()` manda os
candidatos + a descrição de cada item pro Claude escolher o melhor ou declarar que nenhum
serve. Anota os itens com os 5 campos de snapshot já previstos no schema (`sinapi_codigo`,
`sinapi_descricao_referencia`, `sinapi_unidade_referencia`, `sinapi_preco_referencia`,
`sinapi_mes_referencia`) — prontos pra Camada 6 gravar sem tradução.

Depois do primeiro teste (que casou "Revestimento Cerâmico" com um código de porcelanato —
falso positivo de categoria adjacente), Dennis pediu evolução: em vez de comparar só
descrição, a Laura deve **entender o produto antes de procurar a referência**. Implementado
como raciocínio dentro da própria etapa de decisão (`PROMPT_ESCOLHER_SINAPI`), não como
atributos persistidos — decisão explícita do Dennis: "não quero criar uma estrutura
permanente antes de comprovar seu valor."

- Grau de confiança por correspondência (alta/média/baixa/nenhuma) — "errar com confiança é
  pior que admitir dúvida"; toda correspondência mostra o nível, nunca esconde incerteza
- Regra explícita contra categorias adjacentes mas tecnicamente diferentes (o caso real:
  porcelanato ≠ revestimento cerâmico comum, mesmo aparecendo juntos na busca por palavra-chave)
- Equivalência de unidade quando a unidade comercial diverge da unidade SINAPI (ex: 250 SC de
  cimento de 50 kg → 12.500 KG) — calculada pelo Claude a partir do próprio contexto da
  descrição, só quando há certeza; `null` caso contrário
- **Validado contra a mesma tabela real:** com o texto colado, o falso positivo do
  porcelanato desapareceu — casou certo com "REVESTIMENTO EM CERÂMICA ESMALTADA", Alta
  confiança, e as 4 equivalências de unidade calculadas bateram exatas (12.500 KG, 1.200 KG,
  4.000 KG, 30 KG). Com a foto real (onde a Camada 1 perde o fabricante desse item), o mesmo
  match errado de porcelanato ainda aconteceu, mas agora rotulado **"Média confiança"** em
  vez de "Alta" — mudança de natureza do erro, mesmo padrão da Camada 1: de confiante-e-errado
  pra sinalizado-como-incerto

**Correção de direção da equivalência de unidade** *(2026-07-04, mesmo dia)* — a primeira
versão convertia a quantidade do item pra unidade do SINAPI (ex: mostrava "Equivalência:
12.500 KG"). Dennis corrigiu: a unidade comercial (como se compra e negocia — SC, LT, CX...)
nunca muda, em lugar nenhum — nem na lista, nem no pedido, nem na negociação. É o preço do
SINAPI que deve ser convertido pra unidade comercial do item, nunca o contrário. Regra final:
"A Laura nunca converte o item comercial para a unidade do SINAPI. A Laura converte a
referência do SINAPI para a unidade comercial do item." `PROMPT_ESCOLHER_SINAPI` agora pede
`preco_equivalente_unidade_comercial` (preço por SC, não quantidade em KG); exibido como
"Referência SINAPI: R$ 40,00 / SC" com "(equivalente a R$ 0,80/KG)" como contexto secundário.
Dois bugs reais apareceram e foram corrigidos no processo: (1) o preço do candidato SINAPI
nunca era enviado pro Claude — sem ele, a conversão é impossível de calcular; (2) o parsing
do JSON quebrava quando Claude acrescentava um parágrafo de justificativa depois do array,
apesar da instrução contrária — trocado por extração via regex do array `[...]`, robusta a
texto extra antes/depois. Um terceiro problema de raciocínio também apareceu no teste (Claude
usava a quantidade pedida como se fosse o fator de conversão, ex: 136 × 10 quando a unidade já
era a mesma) — corrigido explicitando no prompt que o fator vem do tamanho da embalagem, nunca
da quantidade pedida, e que unidades iguais não geram equivalência nenhuma (`null`).

**Visão de longo prazo registrada, não implementada:** ver seção própria mais abaixo —
"Compreensão de Produto antes da Correspondência SINAPI".

**Bug real na Camada 2 — falso "unidade diferente"** *(2026-07-04, mesmo dia)* — Dennis
reportou dois itens com unidade comercial `m2` e unidade SINAPI `M2` (mesma unidade, metro
quadrado) mostrando "unidade diferente da comercial — conversão não calculada". Causa: a
comparação de unidades na tela (`und != und_sinapi`) era sensível a maiúsculas/minúsculas —
`"m2" != "M2"` dá `True` em Python mesmo sendo a mesma unidade fisicamente. O Claude já tinha
retornado `preco_equivalente_unidade_comercial: null` corretamente (nenhuma conversão é
necessária quando a unidade já é a mesma); o problema estava só na camada de exibição, que
interpretava esse `null` como "não consegui calcular" em vez de "não precisa calcular".
Corrigido com `_mesma_unidade(a, b)` (compara ignorando caixa e espaço nas pontas), usado na
única checagem de igualdade de unidade que existia no código.

**Compreender o produto antes de concluir ausência ou buscar por texto literal** ✓
*(2026-07-04, mesmo dia)* — Dennis trouxe dois casos reais de falso negativo:

1. **"Argamassa EXT 10 EM 1 - 20KG" (Hipermassa)** não casava bem no SINAPI porque a busca
   usava a descrição comercial literalmente ("EXT 10 EM 1" é só o nome de venda do produto,
   não descreve sua função — argamassa colante pra porcelanato em área externa). "A descrição
   comercial é um meio de identificação, não o significado do produto."
2. **"Rejunte Cinza Ártico 5kg Quartzolit"** retornava "quantidade e unidade não
   identificadas" quando na verdade "5kg" quase certamente é o tamanho da embalagem comercial
   do produto, não a quantidade comprada — informação útil que estava sendo descartada junto
   com a quantidade que de fato não dava pra ler.

Terceiro ponto, chegado durante a implementação: **cada item estava sendo interpretado
isoladamente.** "A Laura não deve interpretar apenas o item. Ela deve interpretar também o
conjunto dos itens... Isso é muito parecido com a forma como um engenheiro faz a leitura de
uma lista: ele não olha um item isolado, ele entende primeiro o contexto da compra."

Implementado nos dois prompts (Camada 1 e Camada 2), sem criar nenhuma entidade nova:

- **Contexto da lista inteira**: novo passo no `PROMPT_INTERPRETAR_LISTA` (e reforço no
  `PROMPT_ESCOLHER_SINAPI`, que já recebe a lista inteira numa única chamada) pra olhar os
  itens como conjunto antes de decidir cada um — os itens juntos indicam a etapa de obra
  (revestimentos, hidráulica, elétrica...) e isso reduz ambiguidade individual
- **Campo novo `embalagem`**: tamanho de UMA unidade de venda, inferido da própria descrição
  (ex: "5 KG"), sempre que identificável — mesmo quando `quantidade`/`unidade` (característica
  da compra, não do produto) ficam `null` por falta de leitura confiável na tabela. As duas
  coisas nunca se confundem: saber a embalagem não autoriza inventar a quantidade
- **Campo novo `termo_busca_sinapi`**: descrição técnica genérica (categoria + função +
  aplicação), sem marca nem nome comercial, inferida usando o contexto da lista — usada só
  internamente pra buscar candidatos SINAPI (`_candidatos_sinapi()` passou a buscar por esse
  termo, com fallback pra descrição crua quando não inferido); nunca aparece na tela
- `embalagem` também reaproveitado na Camada 2: quando presente, vira o fator de conversão do
  preço equivalente direto, sem o Claude precisar re-inferir do zero a cada chamada

**Testado** com a lista completa do Dennis (cimento, cal, a argamassa Hipermassa, o rejunte
Quartzolit, porcelanato e revestimento cerâmico juntos): argamassa casou com "ARGAMASSA
COLANTE AC II" em Alta confiança (antes buscava por "ext 10 em 1" e não achava nada
relevante); rejunte extraiu embalagem "5 KG" com quantidade/unidade corretamente `null` e
observação própria "quantidade não especificada"; efeito colateral positivo do contexto de
lista — o par porcelanato/revestimento cerâmico (que antes gerava falso positivo de categoria
adjacente) casou certo nos dois, Alta confiança nos dois, porque a lista contendo os dois
juntos ajudou a distinguir um do outro. Regressão do fluxo orçamento → pedido confirmada.

**Investigação — "sc" e "6,0" claramente legíveis, Laura não lia"** *(2026-07-04, mesmo dia)*
— Dennis reportou a linha do Rejunte com unidade "sc" e quantidade "6,0" bem legíveis na
imagem, mas a Laura retornando `null`/valor errado. Causa raiz encontrada: a foto real
enviada tem só **631×161 pixels** (Telegram compacta agressivamente uploads tipo "foto",
mesmo parecendo nítida no app) — testado repetindo a mesma extração 3x na mesma imagem e
obtendo respostas diferentes pras mesmas duas linhas problemáticas, confirmando que é limite
de pixels disponíveis, não falha de lógica. `PROMPT_INTERPRETAR_LISTA` ganhou uma checagem de
plausibilidade (se a unidade lida não faz sentido técnico pro produto — ex: rejunte por metro
linear — releia a coluna antes de decidir) que ajudou parcialmente numa das rodadas de teste,
mas o problema de fundo é a resolução da imagem, não o prompt. Documentado em
`docs/ARQUITETURA.md` (Limitações Conhecidas) com a mitigação sem código: enviar a lista como
arquivo/documento no Telegram, não como foto — `receber_arquivo()` já trata os dois caminhos,
e documento preserva resolução original.

**Camada 3 — Referência de último preço pago (própria Laura)** ✓ *(2026-07-04, mesmo dia)*

Reaproveita `procurar_item()` (`financeiro/consultas.py`), sem chamada de IA — busca
determinística, já existia antes desta fiada, só nunca tinha sido conectada ao fluxo de
Compras. `_referencia_laura_item()` tenta a descrição inteira primeiro (mais precisa, mas rara
de bater por fraseado diferente entre compras — "Cimento CP II 50 kg" vs "Cimento CP-II
50kg" já cadastrado); cai pra busca por palavra significativa isolada se não achar nada.
Grau de confiança (Princípio 8 da Política de Compras) muda conforme a estratégia que
funcionou: `confirmada` na descrição inteira, `aproximada` na palavra isolada — nunca
apresenta um achado aproximado como se fosse exato. `_adicionar_referencia_laura()` roda
depois da Camada 2, juntando as duas referências (SINAPI + histórico próprio) na mesma tela,
cada uma com origem e confiança declaradas.

Exibição: "Última compra (Aproximada): R$ 19,90/UND — Materiais Teste LTDA" (data omitida
quando desconhecida, em vez de mostrar um traço vazio). Quando não há nenhum item parecido no
histórico, mostra "sem referência própria encontrada" — ausência de informação é informação,
nunca fica em silêncio (Princípio 5: "Quando não existir qualquer referência disponível, a
Laura deve informar isso explicitamente").

Unidade da compra histórica é mostrada como veio gravada, sem conversão pra unidade comercial
do item atual — mesmo princípio de honestidade da Camada 2 (não inventar uma equivalência sem
certeza), só que aqui nem se tenta calcular ainda; fica registrado como possível evolução
futura, não como pendência desta fiada.

**Camada 4 — Tela de conferência editável** ✓ *(2026-07-04, mesmo dia)*

Antes desta camada, a interpretação parava em texto puro — sem teclado, sem nenhuma ação
possível depois de ler a lista. Investigado o padrão já existente pra telas de revisão
(`_resumo_gerar`/`teclado_orcamento` do orçamento) antes de desenhar: texto + teclado inline,
estado em `ctx.user_data`, reemissão da tela a cada edição — mesmo padrão reaproveitado aqui,
sem inventar um novo estilo de interação.

Decisão de escopo (perguntada ao Dennis antes de implementar, já que "edição item a item" é
explicitamente a Camada 5, ainda não implementada): a "edição" desta camada reaproveita o
mesmo mecanismo que já existe no orçamento (`edit_itens`) — reescrever a lista inteira como
texto livre, reinterpretada do zero pelas Camadas 1+2+3. Dennis escolheu essa opção em vez de
esperar a edição granular: "reaproveitar padrão do orçamento".

Implementado: `_teclado_lista_interpretada(ggv)` (botões "✏️ Editar itens" e "✖ Fechar",
mesmo estilo visual do resto do bot); `_texto_itens_interpretados()` ganhou o endereço da obra
(via `buscar_obra()`, mesmo dado já usado no cockpit de obra) no cabeçalho, quando a obra tem
`endereco_entrega` cadastrado; `_cb_lc_editar`/`_cb_lc_fechar` registrados em `_CB_DISPATCH`.
Os três pontos de entrada da Lista de Compras (`/lista` por texto, `/lista` por foto/PDF, e o
botão "📝 Lista de materiais") agora emitem a mesma tela com teclado, em vez de só texto — sem
duplicar lógica entre eles (mesmo princípio de convergência da Camada 1). Estado da edição
fica só em `ctx.user_data` (obra selecionada) — a lista de itens em si não precisa persistir
entre telas, porque editar sempre reconstrói do zero a partir do texto novo enviado.

**Camada 3 — corrigido falso positivo por palavra isolada** ✓ *(2026-07-04, mesmo dia)* —
achado real registrado antes como dívida técnica: "Revestimento Cerâmico HD 32x57,5" casava
com um item histórico de **bloco/tijolo cerâmico** (R$0,87/BLOCOS) via fallback de busca por
palavra isolada ("cerâmica"/"cerâmico"), sem nenhuma verificação de que era o mesmo tipo de
produto. Dennis pediu pra planejar antes de mexer (dado que `procurar_item()`/`itens_pedido`
são dados de produção compartilhados com o fluxo de pedido/financeiro) e definiu a regra:
"comparar as unidades da lista e do pedido, estas devem ser iguais, isso não deveria mudar" —
ao contrário da Camada 2 (SINAPI), aqui **não existe conversão de unidade**, é um filtro
obrigatório binário. Implementado em `_referencia_laura_item()`: candidato só é aceito se a
unidade do pedido histórico for igual (via `_mesma_unidade()`, já criada pra Camada 2) à
unidade comercial do item atual; sem a unidade do item pra comparar, não retorna referência
nenhuma — melhor admitir ausência do que arriscar comparar produtos diferentes. Efeito
colateral esperado e aceito: menos matches no total (ex: um Cimento de teste comprado em
"UND" no histórico não bate mais com o mesmo item pedido em "SC"), mas nenhum falso positivo
por coincidência de palavra. Testado: Revestimento Cerâmico não casa mais com BLOCOS;
regressão do fluxo orçamento → pedido confirmada.

**Redesenho de experiência em 3 níveis + gravação real** ✓ *(2026-07-04)* — Dennis: "a tela de
conferência está muito técnica... o objetivo não é explicar como a Laura chegou na resposta,
é eu conferir rapidamente se a Lista de Compras está correta." Princípio adotado: "A Laura
apresenta primeiro a informação necessária para a decisão. Os detalhes técnicos aparecem
apenas quando solicitados." Proposta de UX apresentada e validada antes de codar (mockups das
3 telas), com 4 decisões de desenho fechadas por ele antes da implementação:

1. **Nível 1 — Tela de Conferência** (`_texto_lista_conferencia`/`_teclado_lista_conferencia`,
   nova tela principal): cabeçalho com obra+endereço (destaque ⚠️ quando faltando), cada item
   em 3 linhas (descrição, quantidade+unidade+fabricante, referência de preço já na unidade
   comercial), indicador 🟢/🟡/🔴 por item, alertas agrupados por tipo no rodapé (sem repetir
   por item), e um resumo (itens, referência total estimada, contagem de alertas)
2. **Nível 2 — Edição** (`_texto_item_detalhe`/item picker): só ao escolher um item aparecem
   todos os campos (fabricante, código, embalagem, SINAPI, última compra, observações).
   Decisão: edição do item inteiro (reescrever a descrição como texto livre, reinterpretado
   pelas Camadas 1+2+3), não campo a campo — "prefiro uma solução simples funcionando do que
   uma edição extremamente refinada agora"; granularidade por campo fica pra fiada futura
3. **Nível 3 — Análise Técnica** (`_texto_analise_tecnica`, ex-`_texto_itens_interpretados`
   renomeada): a tela técnica completa que já existia, agora um nível opcional acessado por
   botão, não mais a primeira coisa mostrada

**Prioridade de referência de preço** (`_melhor_referencia_preco`): 1) última compra própria
(Camada 3), 2) referência própria consolidada (não existe ainda), 3) SINAPI convertido pra
unidade comercial, 4) nenhuma. Nível 1 mostra só "Referência: ~R$ xx,xx/SC" sem dizer a
origem — quem quer saber de onde veio consulta o Nível 3.

**Critério dos indicadores** (`_avaliar_item`) — ajustado por Dennis em relação à primeira
proposta: 🔴 é reservado pro que **impede uma boa cotação** (quantidade ou unidade comercial
desconhecida, item não interpretado) — "se a Laura nunca viu aquele item, isso não impede
pedir orçamento, só significa que ela ainda não possui conhecimento suficiente"; portanto
"sem referência de preço" é 🟡, não 🔴 (correção explícita da minha proposta original). 🟡
cobre confiança SINAPI média/baixa, referência própria aproximada, observação da IA, ou
ausência de referência de preço. 🟢 quando nada disso se aplica.

**Gravação real da Lista de Compras** (`_cb_lc_gerar`) — "Quero implementar a gravação real.
Essa já é a finalidade da Fiada 1... a Lista de Compras deve existir definitivamente no
banco" (ainda sem gerar Pedido de Compra nem vínculo com orçamento). Usa
`criar_ou_buscar_lista_aberta()` + `adicionar_item()` (já existiam, nunca conectados ao fluxo
de interpretação). Bloqueia com mensagem clara se a obra não estiver definida (schema exige
`ggv NOT NULL`). Achado no processo: `lista_compra_itens` nunca teve colunas pra fabricante e
código comercial — dados que a Camada 1 já extrai desde o início — corrigido com duas colunas
novas (`fabricante`, `codigo`) via o mesmo padrão ALTER-seguro das colunas de snapshot,
category diferente (identidade do item, não referência externa congelada).

**Estado de sessão**: `ctx.user_data["lista_itens"]`/`["lista_ggv"]` guardam a lista de
trabalho entre telas (Nível 1 ↔ 2 ↔ 3, edição de um item) — não é persistência, só estado de
interação; a gravação de verdade só acontece no clique em "Gerar Lista de Compras".

**Testado**: os 3 níveis renderizados com a foto real de 8 itens (soma da referência estimada
conferida manualmente — bate exato); item não interpretado (fallback string) não quebra a
tela; gravação bloqueada sem obra e bem-sucedida com obra, todos os campos (incluindo
fabricante) persistidos corretamente; fluxo de correção de item testado com objetos
simulados. Regressão do fluxo orçamento → pedido confirmada.

**Pendente** (fica pra fiada futura, escopo definido por Dennis): edição campo a campo
(escolher item → escolher campo → digitar valor); geração de Pedido de Compra a partir da
Lista de Compras; vínculo com orçamento.

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

- **Alta — três caminhos divergentes para confirmar o mesmo tipo de documento**
  Achado em 2026-07-03, durante a unificação de `lista_materiais` (ver Fase — Módulo de Compras).
  Existem hoje 3 pontos de entrada que terminam confirmando um documento e não convergem:
  `_cb_sel_tipo_inicial()` (classificação automática, trata `comprovante_pix`/`nota_fiscal`
  corretamente), `_cb_set_tipo()` (correção manual de tipo — **bug real**: chama `_resumo_gerar()`
  sempre, não importa o tipo escolhido; `_resumo_gerar()` é feita só pra orçamento) e `_cb_ok()`
  (confirmação genérica pós-correção — trata `comprovante_pix` de forma incompleta, sem checagem
  de duplicidade e sem `reply_markup` com os botões de candidato; não trata `nota_fiscal` de jeito
  nenhum, cai no genérico "Confirmado: Nota Fiscal" sem buscar candidato). **Não corrigir dentro de
  outra fiada** — ver "Motor de Interpretação e Classificação de Documentos" abaixo; merece fiada
  própria de investigação antes de qualquer mudança (Dennis, 2026-07-03: "não é apenas trocar uma
  chamada por outra... toca o coração da Laura").

---

## Visão de Longo Prazo — Motor de Interpretação e Classificação de Documentos

*Registrado em 2026-07-03, a partir do achado de divergência acima. Não implementar dentro de
outra fiada — merece investigação própria antes de qualquer mudança de código.*

### O princípio

> **Entradas diferentes podem existir. Processos diferentes não.** Sempre que o resultado
> esperado for o mesmo, a implementação deve convergir para um único fluxo interno.

A leitura, interpretação e condução de documentos (orçamento, comprovante PIX, NF-e, lista de
compras, taxas, documentos obrigatórios) é um dos núcleos da Laura — não um detalhe de
implementação. Cada tipo de documento hoje tem sua própria variação de "quem processa" dependendo
de qual caminho o usuário seguiu (classificação automática, correção manual, tipo vindo de um
comando explícito como `/lista`) — o achado acima é o primeiro sintoma concreto disso, mas
provavelmente não o único.

### Antes de mudar qualquer código, uma fiada de investigação precisa responder

- Por que esses caminhos ficaram separados (arqueologia: qual foi adicionado depois de qual, e
  por quê a atualização não se propagou pros outros)
- Quais tipos de documento existem hoje, de fato, no código (não só os documentados)
- Quais etapas são realmente comuns entre eles (recepção, dedup por hash, chamada à IA,
  apresentação pro usuário, confirmação, gravação) vs. quais são específicas de cada tipo
- Onde a convergência deve ocorrer (um único dispatcher de pós-classificação? uma função por
  etapa comum, chamada de todos os pontos de entrada?)
- Quais riscos existem em mexer nisso — este é o código mais atravessado do sistema, tocado por
  toda fiada de tipo de documento desde o início do projeto
- Qual seria o menor redesenho seguro — não uma reescrita completa

### Direção de longo prazo — para além da convergência

Hoje o usuário ainda diz do que se trata cada documento antes da IA processar. A visão de longo
prazo é a Laura evoluir gradualmente para:

1. Receber qualquer documento
2. Ler o conteúdo
3. Classificar o tipo provável
4. Declarar o grau de confiança da classificação (mesmo vocabulário do Princípio 8 da Política de
   Compras — confirmada/aproximada/ausente)
5. Apresentar para conferência humana
6. Permitir correção
7. Aprender com a correção
8. Encaminhar para o pipeline correto

A Laura não precisa acertar tudo sozinha desde o começo — precisa de uma arquitetura que permita
melhorar continuamente. Sair de "o usuário informa o tipo" para "a Laura sugere o tipo com base no
conteúdo e pede confirmação humana" é o horizonte; a convergência dos caminhos hoje divergentes é
o primeiro passo necessário antes disso ser sequer possível.

---

## Visão de Longo Prazo — Compreensão de Produto antes da Correspondência SINAPI

*Registrado em 2026-07-04, a partir da Camada 2 do módulo de Compras. Tratado por enquanto como
raciocínio de interpretação, não como entidade nova — ver restrição do Dennis abaixo.*

### O que já muda hoje

A Camada 2 já deixou de comparar só "descrição parecida" — o `PROMPT_ESCOLHER_SINAPI` pede pro
Claude considerar internamente categoria, aplicação, material e especificação técnica antes de
decidir uma correspondência, e declarar um grau de confiança (alta/média/baixa/nenhuma) em vez
de um sim/não binário.

### A visão maior — ainda não implementada

Dennis: "Hoje fazemos Descrição → SINAPI. Quero caminhar para Descrição → Compreensão do
produto → SINAPI." A ideia é que a Laura extraia atributos técnicos completos de cada item antes
de procurar a referência — não só pra casar melhor com o SINAPI, mas como base pra um catálogo
técnico-comercial próprio, do qual o SINAPI seria uma referência entre outras, não a única fonte.

Atributos que a visão completa cobre: categoria, é material ou ferramenta, aplicação (piso,
parede, teto, estrutura...), material predominante, dimensões, acabamento, fabricante, código
comercial, embalagem, unidade comercial, características técnicas da descrição.

### Restrição explícita do Dennis — por que isso não virou schema novo agora

> "Não quero criar um 'Produto Laura' como uma nova entidade do sistema agora... Esses atributos
> não precisam necessariamente ser persistidos agora. Eles podem existir apenas durante o
> processo de interpretação... Por enquanto, quero evitar criar uma estrutura permanente antes
> de comprovar seu valor."

Isso é aplicação direta de "Aprender antes de otimizar" (CONSTITUICAO.md). Enquanto essa visão
não vira entidade, os atributos considerados durante o raciocínio da Camada 2 não aparecem como
campos de saída — só influenciam a decisão final (código escolhido + confiança + equivalência de
unidade, quando aplicável). Se algum desses atributos comprovar valor próprio pra consultas,
estatísticas ou comparação entre marcas, aí sim vira candidato a persistência — não antes.

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
