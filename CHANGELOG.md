# CHANGELOG

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versionamento baseado em [Semantic Versioning](https://semver.org/).

---

## [Não lançado]

### Próximas fiadas (priorizadas)

> Só itens acionáveis numa sessão (decisão a tomar ou código a escrever) — pendências que resolvem
> sozinhas com o uso do dia a dia não entram aqui (ex: fechar um pedido parcelado esperando
> pagamento). Ver Dívida Técnica em `docs/ROADMAP.md`.

1. Camadas 4-6 do módulo de Compras — tela de conferência editável, edição item a item,
   gravação final confirmada
2. Decidir onde a GGV02 arquiva documentos novos (estrutura de pasta diferente da GGV03)
3. Alimentar `docs/LICOES_EXTRACAO.md` a cada novo bug de parsing/extração
4. Limpeza opcional de 2 arquivos órfãos no OneDrive (pedido Base Forte/GGV03-006 antigo, excluído)
5. Acesso via Claude Code Remote do celular — ideia registrada, servidor Proxmox em casa (Eric)
6. Persistir os 9 índices de `data/laura.db` em código (hoje só existem no banco vivo — um `init_db()`
   contra um banco novo não os recria; ver Dívida Técnica em `docs/ROADMAP.md`)

> Fiadas próprias, não priorizadas ainda: "Motor de Interpretação e Classificação de Documentos"
> (convergência dos três caminhos divergentes de confirmação de documento) e "Compreensão de
> Produto antes da Correspondência SINAPI" (atributos técnicos completos antes de casar com
> SINAPI — deliberadamente não persistido ainda, ver Visão de Longo Prazo em `docs/ROADMAP.md`).

> Concluído desde a última revisão: Camada 2 do módulo de Compras (candidatos SINAPI, grau de
> confiança, equivalência de unidade) — ver entrada abaixo; endereço da Lista de Compras
> resolvido (herda da obra, não vira atributo novo); Fiadas 1/2 de 2026-07-03 substituídas pelo
> redesenho em camadas de 2026-07-04 (Camada 1 concluída, depois reescrita pra saída JSON
> estruturada no mesmo dia) — ver `docs/ROADMAP.md`.

---

## [Camada 2 — Corrige falso "unidade diferente" (m2 vs M2)] — 2026-07-04 (mesmo dia)

### Motivação

Dennis reportou dois itens reais (Forro PVC em `m2`, Revestimento Cerâmico em `m2`) marcados
como "unidade diferente da comercial — conversão não calculada" contra candidatos SINAPI em
`M2` — a mesma unidade (metro quadrado), só com caixa diferente.

### Corrigido

- `_mesma_unidade(a, b)`: nova função de comparação de unidade, ignora maiúsculas/minúsculas e
  espaço nas pontas
- `_texto_itens_interpretados()`: troca a comparação direta `und != und_sinapi` (sensível a
  caixa) por `not _mesma_unidade(und, und_sinapi)`

### Diagnóstico

O Claude já retornava `preco_equivalente_unidade_comercial: null` corretamente pros dois itens
(nenhuma conversão é necessária quando a unidade já é a mesma) — o bug estava só na camada de
exibição, que interpretava esse `null` como "não consegui calcular" em vez de "não precisa
calcular". Nenhuma mudança necessária em `PROMPT_ESCOLHER_SINAPI`.

---

## [Camada 3 — Referência de último preço pago (própria Laura)] — 2026-07-04 (mesmo dia)

### Motivação

Próxima camada natural depois da SINAPI: além da referência de mercado (SINAPI), a Laura já
tem o histórico real de compras da própria empresa — Princípio 5 da Política de Compras cita
"último preço pago" como referência de primeira classe. `procurar_item()`
(`financeiro/consultas.py`) já existia pra isso, só nunca tinha sido conectado ao fluxo de
Compras.

### Adicionado

- `_referencia_laura_item()`: tenta `procurar_item()` com a descrição inteira primeiro; se não
  achar nada, cai pra busca por palavra significativa isolada (mesmo extrator de palavras já
  usado na Camada 2). Retorna o item mais recente encontrado (já ordenado por
  `data_pagamento DESC`), sem chamada de IA — busca determinística
- `_adicionar_referencia_laura()`: roda depois da Camada 2, anota cada item com preço/unidade/
  data/fornecedor da última compra própria e a origem/confiança da referência
- Grau de confiança (`confirmada` na descrição inteira, `aproximada` na palavra isolada) —
  mesmo vocabulário do Princípio 8, nunca apresenta um achado aproximado como exato
- Exibição: "Última compra (Aproximada): R$ 19,90/UND — Materiais Teste LTDA"; quando não há
  histórico, "sem referência própria encontrada" em vez de silêncio (Princípio 5: ausência de
  informação também é informação)
- `compras/__init__.py` passou a exportar `GrauConfianca` e `OrigemReferencia`

### Testado

Cimento CP II 50 kg: achou o item já cadastrado no histórico com fraseado diferente ("Cimento
CP-II 50kg") via busca por palavra, confiança aproximada, preço (R$19,90) e fornecedor
corretos. Item sem histórico (ex: Prego 18x30) mostrou corretamente "sem referência própria
encontrada". Regressão do fluxo orçamento → pedido confirmada.

---

## [Camada 2 — Correção de direção da equivalência de unidade] — 2026-07-04 (mesmo dia)

### Motivação

Dennis revisou a equivalência de unidade recém-implementada e corrigiu o sentido da conversão:
"A Lista de Compras deve manter sempre a unidade comercial... A Laura nunca converte o item
comercial para a unidade do SINAPI. A Laura converte a referência do SINAPI para a unidade
comercial do item." A primeira versão fazia o oposto — convertia a quantidade do item pra
unidade do SINAPI ("Equivalência: 12.500 KG").

### Alterado

- `PROMPT_ESCOLHER_SINAPI`: pede `preco_equivalente_unidade_comercial` (preço do SINAPI
  convertido pra R$/unidade comercial do item) no lugar de `quantidade_equivalente`/
  `unidade_equivalente`
- `_adicionar_correspondencia_sinapi()`: envia o preço de cada candidato SINAPI pro Claude
  (faltava — sem ele a conversão de preço é impossível de calcular); anota
  `item["sinapi_preco_equivalente"]` no lugar dos dois campos antigos
- `_texto_itens_interpretados()`: exibe "Referência SINAPI: R$ 40,00 / SC" com
  "(equivalente a R$ 0,80/KG)" como contexto secundário; unidade comercial nunca aparece
  convertida em lugar nenhum da tela

### Corrigido

- Parsing do JSON da escolha SINAPI quebrava quando Claude acrescentava um parágrafo de
  justificativa em texto livre após o array, apesar da instrução de responder só com JSON —
  trocado por extração via regex do bloco `[...]`, tolerante a texto antes/depois
- Prompt não distinguia "unidade igual → sem conversão" de "unidade diferente → converter";
  Claude chegou a usar a quantidade pedida como fator de conversão quando a unidade já era
  igual (136 × 10 em vez de manter 136,00/M3) — corrigido explicitando que o fator vem do
  tamanho da embalagem, nunca da quantidade pedida, e que unidade igual não gera equivalência

### Testado

3 casos: unidade igual (sem falsa conversão — Areia em M3), unidade diferente sem tamanho de
embalagem informável pela descrição (honesto, `null`, mostra preço bruto com aviso — Tinta em
LT vs L do SINAPI), e unidade diferente com conversão calculável (bate exato com o exemplo do
Dennis: 250 SC de Cimento CP II 50kg, SINAPI R$0,80/KG → R$40,00/SC). Regressão do fluxo
orçamento → pedido confirmada (`scripts/teste_gerar_pedido.py`).

---

## [Camada 2 — Candidatos SINAPI, confiança e equivalência de unidade] — 2026-07-04 (mesmo dia)

### Motivação

Primeiro teste da Camada 2 casou "Revestimento Cerâmico HD 32x57,5" com um código SINAPI de
**porcelanato** — categorias adjacentes mas tecnicamente diferentes, preços bem distintos.
Dennis: "prefiro que ela diga correspondência de baixa confiança... do que assumir um item
incorreto. Errar com confiança é pior do que admitir dúvida." Pediu também para a Laura
"entender o produto antes de procurar a referência" em vez de só comparar descrição — mas
sem criar uma entidade nova: "não quero criar uma estrutura permanente antes de comprovar
seu valor."

### Adicionado

- `_candidatos_sinapi()`: busca por palavra-chave (FTS5) contra `insumos_sinapi_fts` — recall
  alto, não precisão; é só o filtro inicial
- `_adicionar_correspondencia_sinapi()`: uma única chamada ao Claude decide a correspondência
  da lista inteira (não uma por item) — chamada de dentro de `_interpretar_lista_texto()`/
  `_interpretar_lista_arquivo()`, nunca por um caminho separado (mesma convergência da Camada 1)
- `PROMPT_ESCOLHER_SINAPI`: pede pro Claude considerar internamente categoria, aplicação,
  material e especificação técnica antes de decidir — sem exigir esses atributos como campos
  de saída (raciocínio de interpretação, não schema novo)
- Grau de confiança por correspondência: alta/média/baixa/nenhuma — sempre exibido, nunca
  escondido
- Regra explícita contra categorias adjacentes (o caso real do porcelanato/revestimento)
- Equivalência de unidade quando a comercial diverge da SINAPI (ex: 250 SC de cimento de
  50 kg → 12.500 KG), calculada só quando há certeza a partir do contexto da própria descrição
- Itens anotados com os 5 campos de snapshot já previstos no schema (`sinapi_codigo` +
  descrição/unidade/preço/mês de referência) — prontos pra Camada 6 gravar sem tradução

### Documentado

- Nova "Visão de Longo Prazo — Compreensão de Produto antes da Correspondência SINAPI" em
  `docs/ROADMAP.md`: a visão completa (atributos técnicos completos, catálogo próprio da
  Laura) fica registrada, deliberadamente não implementada como entidade — só como raciocínio
  dentro do prompt de decisão, por enquanto

### Testado

Contra a mesma tabela real como gabarito: o falso positivo do porcelanato desapareceu com o
texto colado (casou certo, Alta confiança) e as 4 equivalências de unidade calculadas bateram
exatas (12.500 KG, 1.200 KG, 4.000 KG, 30 KG). Com a foto real (onde a Camada 1 perde o
fabricante desse item específico), o mesmo match errado ainda aconteceu, mas rotulado "Média
confiança" em vez de "Alta" — mudança de natureza do erro, não eliminação total. Regressão do
fluxo orçamento → pedido confirmada.

---

## [Camada 1 — Saída estruturada em JSON] — 2026-07-04 (mesmo dia)

### Motivação

Teste com uma tabela real (planilha de 8 itens de material de acabamento) expôs que o formato
de saída original — uma linha de texto por item, casada por regex — forçava a IA a achatar uma
tabela em texto corrido antes de responder. Sintomas: quantidade virando "1" quando a coluna
real dizia outro valor (250, 60, 200, 6...), unidade errada, fabricante nunca separado, código
de referência alterado (`72707/72745` virou `27707/72745`). Dennis: "isso é frágil por natureza."

### Alterado

- `PROMPT_INTERPRETAR_LISTA` reescrito em procedimento (detectar tabela → linhas → colunas
  separadas → só então interpretar semanticamente) + regras (quantidade/unidade nunca
  inventadas, `null` em vez de chute; código de referência copiado literalmente, nunca
  "corrigido"; prioridade explícita: coluna da tabela > texto lido > interpretação da IA)
- Saída agora é array JSON (`numero`, `descricao`, `fabricante`, `codigo`, `unidade`,
  `quantidade`, `observacoes`) em vez de uma linha de texto por item
- `_itens_lista_materiais()` reescrita: `json.loads()` no lugar do regex
  (`_ITEM_LISTA_MATERIAIS_RE`, removido), com fallback defensivo — JSON malformado vira itens
  em string, nunca perde item silenciosamente
- `_texto_itens_interpretados()` mostra fabricante e código quando existirem; diz
  explicitamente "quantidade não identificada"/"unidade não identificada" em vez de omitir

### Documentado

- Lição #13 de `LICOES_EXTRACAO.md`: dado tabular forçado em texto plano perde estrutura —
  nova "Família C" de bug (formato de saída não tem a forma do dado de origem), distinta da
  Família A (vocabulário implícito) e B (não reaproveita o que já sabe)

### Testado

Validado contra a tabela real como gabarito conhecido: 8/8 itens corretos (quantidade, unidade
e código) com o texto colado; 5/8 perfeitos com a foto real — os 3 restantes com imperfeição
de campo, mas nenhum inventando valor (o caso mais difícil retornou `null` e disse isso, em
vez de "1 SC"). Regressão do fluxo orçamento → pedido confirmada.

---

## [Módulo de Compras — Redesenho em camadas, Camada 1 concluída] — 2026-07-04

### Motivação

Ao testar as Fiadas 1/2 de ontem, Dennis pediu um redesenho conceitual antes de continuar:
a Lista de Compras deve nascer com a mesma lógica de segurança do Pedido de Compra — IA
interpreta o que for enviado (texto, foto ou PDF) de uma vez, tenta padronizar contra o
SINAPI, só grava depois de conferência/edição humana. "Entradas diferentes podem existir.
Processos diferentes não" — princípio que emergiu desta sessão e passou a orientar tudo.

### Alterado — redesenho

- Schema de `lista_compra_itens`: 11 colunas novas de **snapshot**, congeladas no momento da
  confirmação e nunca recalculadas depois — `sinapi_codigo` + 4 campos de referência SINAPI
  (descrição/unidade/preço/mês) e 5 campos de referência interna da Laura (preço/data/
  fornecedor/origem/grau de confiança). `insumos_sinapi` muda todo mês; a leitura de uma
  lista antiga não pode mudar de valor sozinha (CONSTITUICAO.md, "Dados são sagrados")
- `adicionar_item()` (`compras/lista.py`) aceita e grava os 11 campos, todos opcionais
- Migração aplicada e verificada em produção e teste — `PRAGMA integrity_check` ok nas duas

### Adicionado — infraestrutura de busca

- `insumos_sinapi_fts`: tabela virtual FTS5, busca por palavra (não por frase inteira) —
  `LIKE '%termo%'` falhava quando a ordem das palavras mudava. Reconstruída do zero a cada
  reimportação via `scripts/import_sinapi.py::reconstruir_indice_fts()`
- Achado durante a implementação: `DELETE FROM` numa tabela FTS5 externa é instável nesta
  versão do SQLite (3.50.4) — retorna "database disk image is malformed" de forma
  intermitente, sem nenhuma corrupção real de dado. Resolvido com `DROP` + `CREATE` +
  `INSERT`, nunca `DELETE` na tabela virtual
- Diagnóstico rápido da infraestrutura de busca do projeto todo, a pedido do Dennis: só um
  lugar usa `LIKE '%texto%'` (`procurar_item`); achado um índice morto (`idx_fornecedores_cnpj`,
  nunca usado pela query real — confirmado com `EXPLAIN QUERY PLAN`); nenhuma mudança urgente
  fora do SINAPI, registrado como dívida técnica menor

### Adicionado — Camada 1 (interpretação)

- `PROMPT_INTERPRETAR_LISTA`: prompt dedicado para lista de materiais, não passa pela
  classificação compartilhada do orçamento
- `_interpretar_lista_texto()`/`_interpretar_lista_arquivo()`: mesma função pros dois pontos
  de entrada (`/lista` e botão "📝 Lista de materiais" no menu de documento) — testado
  estruturalmente que chamam o mesmo código, não duas implementações paralelas
- `/lista` muda de papel: não abre mais edição item a item — pede "Envie a lista — texto,
  foto ou PDF" e interpreta o conteúdo inteiro de uma vez

### Corrigido

- **Lição #12 de `LICOES_EXTRACAO.md`**: marca/fabricante (ex: "Quartzolit") confundida com
  unidade de medida quando aparece perto da quantidade no texto original. Prompt corrigido
  com lista explícita de unidades válidas e proibição explícita de usar marca no lugar da
  unidade — mesma classe de bug da Lição #1 (instrução implícita não basta)
- `mostrar_ajuda()` ainda descrevia o `/lista` de ontem — corrigido pro comportamento real

### Removido

- Todo o código das duas fiadas de 2026-07-03, órfão depois do redesenho: `_tela_lista_compras`,
  `_teclado_lista_compras`, `_abrir_lista_compras`, `_parse_item_lista`,
  `_resumo_lista_materiais`, `teclado_lista_materiais`, `_tela_lista_finalizada`,
  `_cb_lista_mat_confirmar`, `_cb_lista_fechar`, `_cb_lista_add_sug`, `_cb_lista_rem_item`
- `[lista_materiais]` saiu do `PROMPT` compartilhado de classificação (PASSO 1, PASSO 3,
  "valores aceitos") — não é mais usado por nenhum caminho
- Duplicação morta em `_cb_set_ggv()` (branch de `lista_materiais` que nunca mais é
  alcançado) encontrada e removida durante a limpeza

### Achado arquitetural — registrado, não corrigido nesta fiada

Durante a unificação, encontrado que o pipeline de confirmação de `comprovante_pix`/
`nota_fiscal` tem três pontos de entrada que não convergem entre si — um deles
(`_cb_set_tipo()`) com bug real (sempre mostra tela de orçamento, não importa o tipo
escolhido). Por pedido do Dennis, registrado como dívida técnica + visão de longo prazo
("Motor de Interpretação e Classificação de Documentos") em `docs/ROADMAP.md` — merece
fiada própria de investigação, não é uma troca simples de chamada.

### Não concluído

- Camadas 2-6 (SINAPI, referência de preço, tela de conferência editável, edição, gravação
  final) — ver `docs/ROADMAP.md`, Fase — Módulo de Compras
- Validação completa ao vivo no Telegram com a foto real que motivou o redesenho

---

## [Módulo de Compras — Fiada 1 e Fiada 2] — 2026-07-03

> **Substituída em 2026-07-04** — não complementada. Depois do primeiro teste real, Dennis
> pediu um redesenho conceitual (ver entrada acima); nenhum código desta entrada sobreviveu
> à reescrita. Preservada aqui só como histórico da decisão.

### Motivação

Primeira engenharia do domínio de Compras, na mesma sessão da fundação conceitual (política
+ casos de uso + modelo de domínio, ver entrada seguinte). Fiada 1 aprovada com critério
explícito. Fiada 2 nasceu de um pedido do Dennis no meio do trabalho, ao testar a Fiada 1 e
esperar (sem sucesso) achar "Lista de Compras" no menu de tipo de documento de uma foto.

### Adicionado

- **Módulo `compras/`** (`compras/lista.py` + `compras/__init__.py`) — nasce modular desde o
  primeiro dia (ADR-002): `StatusLista`/`StatusItem`, `init_db_compras()`, `sugerir_itens()`
  (nunca inventa — lista vazia sem histórico real), `criar_ou_buscar_lista_aberta()`,
  `adicionar_item()`, `remover_item()`, `listar_itens()`, todas recebendo `db_path`
- Tabelas `listas_compra` e `lista_compra_itens`
- **Comando `/lista`** (Fiada 1): cria/reabre a Lista de Compras de uma obra, Laura sugere
  itens recorrentes do histórico com último preço pago; adicionar por botão ou texto livre
  (`_parse_item_lista()`, parser tolerante, nunca bloqueia); remover item; fechar
- **Tipo de documento `lista_materiais`** (Fiada 2): foto/PDF de lista de materiais (sem
  preço, sem fornecedor) — novo template de classificação e extração no `PROMPT`, com
  cuidado explícito pra Claude nunca inventar preço/fornecedor nesse tipo; nova tela de
  confirmação (`_resumo_lista_materiais()`, mais simples que a de orçamento); confirmação
  gera a **Lista de Compras finalizada** (`_tela_lista_finalizada()`, resumo só leitura —
  não a tela de edição contínua da Fiada 1, ajustado ao vivo depois do primeiro teste real)

### Corrigido

- Duplicação morta em `_cb_set_ggv()`: um `if/else` cujos dois ramos chamavam a mesma função
  com o mesmo resultado — limpeza sem mudança de comportamento, encontrada ao adaptar essa
  função pro tipo `lista_materiais`

### Testado

- Script contra `data/laura_test.db`: sugestão real (GGV03, histórico existente) e "sem
  histórico" explícito (obra sem nenhuma compra) — critério do Dennis cumprido
- Regressão do fluxo orçamento → pedido (`scripts/teste_gerar_pedido.py`), duas vezes,
  sem alteração de comportamento
- Foto real do Dennis: 11 itens de material hidráulico (Tigre) extraídos corretamente,
  incluindo o caminho de obra não identificada → definir obra → lista finalizada

### Não concluído

- Validação completa ao vivo no Telegram, do início ao fim sem interrupção — retomar amanhã
- Endereço na Lista de Compras (frete é parte da negociação do orçamento) — registrado em
  `docs/ROADMAP.md`, decisão de implementação futura

---

## [Fundação do domínio de Compras] — 2026-07-03

### Motivação

Dennis quis entender o domínio de Compras por completo antes de escrever qualquer código
— "quando esse modelo estiver maduro, a implementação seja praticamente um exercício de
engenharia, e não mais de descoberta do negócio."

### Adicionado

- **`docs/POLITICA_COMPRAS.md`** — princípios do domínio: Laura é consultora de compras,
  nunca compradora automática; negociação e decisão comercial sempre humanas; nenhuma
  compra planejável nasce de um orçamento — nasce de uma necessidade, organizada numa
  Lista de Compras; compras obrigatórias (impostos, taxas, concessionárias) são domínio
  próprio, não exceção
- **`docs/CASOS_DE_USO_COMPRAS.md`** — 15 casos de uso em linguagem de negócio: compra
  planejada, primeira compra sem histórico, com histórico, fornecedor preferencial
  vence/perde, emergencial, obrigatória, serviço, equipamento, recorrente, mais 5 casos
  de proatividade e prevenção de erro (Laura inicia conversa, Laura evita erro) —
  encontrados em revisão crítica pedida por Dennis depois da primeira versão. Seção "Os
  Três Momentos da Laura" (antes/durante/depois) e 7 padrões comuns no fechamento
- **`docs/MODELO_DOMINIO_COMPRAS.md`** — transição pra engenharia: objetos conceituais
  (Lista de Compras, Item da Lista, Orçamento, Alerta — cada um com ciclo de vida
  próprio; Referência de Preço e Tendência de Fornecedor como valores computados sob
  demanda, não entidades persistidas), eventos de domínio, responsabilidades Laura ×
  usuário, regras de negócio por momento — sem banco de dados, classes ou APIs. Revisão
  arquitetural final corrigiu vocabulário interno vazado (`pfm_gerado` → "emitido") e um
  estado que era na verdade relacionamento opcional (vinculação orçamento↔item), não fase
  de ciclo de vida

### Atualizado

- **`docs/PROCESSO.md`**: novo mecanismo "Políticas de Domínio" — generalizado por pedido
  do Dennis pra não virar regra especial de Compras. Qualquer domínio (presente ou
  futuro) pode ganhar `docs/POLITICA_<DOMINIO>.md` + documentos complementares, de
  leitura obrigatória condicional ao tocar aquele domínio — mesmo padrão já usado pra
  `LICOES_EXTRACAO.md`
- **`docs/GLOSSARIO.md`**: novo termo "Lista de Compras"; distinção conceitual
  "Orçamento vs. Pedido de Compra" reescrita como cadeia de três objetos
- **`docs/IDENTIDADE_DO_PRODUTO.md`**: três referências leves à nova política (Objetos
  Centrais, novo Marco de Maturidade, tabela de documentos) — sem importar detalhe de
  processo, preservando a separação entre identidade de produto e política de domínio

### Não alterado, por decisão

- `CONSTITUICAO.md` — deliberadamente abstrata, não nomeia domínio específico (mesmo
  padrão de nunca ter nomeado Financeiro ou NF-e)
- Nenhuma ADR existente — são documentos históricos; a ADR-002 já estabelece o princípio
  que rege a implementação futura ("todo novo domínio nasce modular"), sem necessidade de
  ADR nova só pra repetir uma decisão já aceita

### Padrão aprendido

Domínio de negócio antes de arquitetura: Política → Casos de Uso → Modelo de Domínio →
só então engenharia. Cada camada foi revisada criticamente antes de avançar pra próxima —
inclusive com pedidos explícitos de "pare e aponte inconsistências antes de continuar".

---

## [Formalização do Jeito Claude] — 2026-07-03 (continuação)

### Motivação

**Erro grave:** Tentei implementar automação de pagamento na primeira parte desta sessão sem ler PROCESSO.md, violando ADR-004 e ADR-002. Dennis: "você parece uma anta! Gastamos horrores de tokens desenvolvendo nossos princípios."

**Lição:** Memória não serve se não é **consultada no primeiro passo**. Estabelecer ritual obrigatório.

### Adicionado

- **Checklist obrigatório de inicialização em PROCESSO.md Seção 1.0**
  - Ordem exata (baseada em `docs/00-Fluxo da cadeia do projeto.txt`):
    1. CONSTITUICAO.md — princípios
    2. PROCESSO.md — como funciona uma sessão
    3. ESTADO.md — onde está agora
    4. ROADMAP.md — próximas fiadas
    5. ARQUITETURA.md (se engenharia)
  - **Não é opcional.** Evita violações de ADR, economiza horas de trabalho errado.

- **Memória formalizada:** `jeito_claude_checklist_obrigatorio.md`
  - Documenta por que o checklist existe
  - Registra o erro e a correção de 2026-07-03
  - Padrão aprendido: **Ler → Entender → Propor → Implementar → Documentar**

### Atualizado

- **Documentação corrigida:**
  - PROCESSO.md Seção 1.0 agora referencia `docs/00-Fluxo da cadeia do projeto.txt` (ordem exata)
  - MEMORY.md index aponta para checklist formalizado
  - ESTADO.md registra a continuação desta sessão

---

## [Segurança + módulo financeiro/relatorios.py] — 2026-07-03

### Corrigido

- 🔴 **Vulnerabilidade de segurança real** (encontrada na auditoria de bibliotecas de 2026-07-02,
  não corrigida até esta sessão): `responder_botao()` — dispatcher central de todo `callback_query`
  do Telegram — não verificava `DONO_ID`, diferente de todos os outros handlers. Combinado com
  `atualizar()`/`atualizar_obra()`, que interpolavam nome de coluna direto em SQL a partir de
  `**kwargs` sem allowlist, um `callback_data` arbitrário (cliente Telegram customizado) podia
  disparar ações reais e potencialmente injetar SQL sem nunca ter clicado em botão nenhum.
- `responder_botao()` agora retorna imediatamente se `update.effective_user.id != DONO_ID`
- `atualizar()` e `atualizar_obra()` agora validam contra allowlist (`_COLUNAS_DOCUMENTO`,
  `_COLUNAS_OBRA`) e levantam `ValueError` para qualquer coluna fora da lista

### Adicionado

- **Módulo `financeiro/relatorios.py`** — gerador de fluxos e relatórios de pagamento:
  - `gerar_fluxo_pagamentos_obra(db_path, ggv=None, output_dir=None)` — detalhe por obra (NF-e,
    descrição, % quitado)
  - `gerar_relatorio_pagamentos(db_path, output_dir=None)` — consolidado de todos os pagamentos
  - Saída em `data/relatorios/*.xlsx`, com timestamp
- Ainda não integrado a `bot.py` — funções chamadas manualmente, sem botão/comando no Telegram

---

## [Otimização de BD + CLI para memória rápida] — 2026-07-03

### Motivação

Dennis: "Laura não é uma ferramenta que você usa. É uma memória que você carrega. De nada adianta ter memória se não consigo acessá-la de maneira prática e rápida."

**Erro do início:** Tentei implementar automação de pagamento sem ler PROCESSO.md, violando ADR-004 e ADR-002. Dennis corrigiu: "gastamos horrores de tokens desenvolvendo nossos princípios e ideias e agora você parece uma anta!"

**Correção:** Li todos os documentos (CONSTITUICAO.md, PROCESSO.md, ARQUITETURA.md, ADR-004), entendi os 3 gatilhos que bloqueiam `comprovante/`, e implementei **respeitando restrições**.

### Adicionado

- **9 índices estratégicos em `data/laura.db`** — todos os filtros/buscas agora executam <3ms (validado em produção):
  - `idx_lancamentos_pfm`, `idx_lancamentos_ggv_status`, `idx_lancamentos_data_pag`
  - `idx_parcelas_pfm`, `idx_parcelas_data`, `idx_itens_pfm`
  - `idx_documentos_tipo`, `idx_fornecedores_cnpj` (+ uma coluna `resumo_compra`)
  
- **Módulo `financeiro/consultas.py`** (novo) — 4 funções de acesso instantâneo:
  - `obter_pedido_completo(db, "GGV03-001")` → consolida lançamento+parcelas+itens+docs (2.2ms)
  - `obter_consolidado_obra(db, "GGV03")` → resumo financeiro por obra (1.5ms)
  - `listar_pedidos_pendentes(db, "GGV03")` → sem documento fiscal (0.7ms)
  - `procurar_item(db, "redução")` → busca de material já comprado (0.9ms) — resolve a fiada
    "estruturar itens de compra numa tabela própria" (`itens_pedido`, criada em 2026-07-02 na
    sessão de modularização, agora com CLI de consulta em cima dela)

- **CLI `scripts/consultar.py`** (novo) — terminal instantâneo:
  - `python scripts/consultar.py GGV03-001` → pedido completo
  - `python scripts/consultar.py --obra GGV03` → resumo da obra
  - `python scripts/consultar.py --item redução` → procurar material
  - `python scripts/consultar.py --pendentes GGV03` → alertas

- **Extrato de pagamentos melhorado:**
  - Descrições consolidadas: `Categoria - item1, item2, item3`
  - Número de ART extraído automaticamente (ex: "ART 1720263226496")
  - Valor unitário em destaque (info decisória para materiais)
  - Comparação com SINAPI: identifica tubos caros (+76%), baratos (-18%)

### Não foi implementado (respeitando ADR-004)

- ❌ Automação de pagamento (`registrar_pagamento_automatico()` em `bot.py`)
- ✅ **Razão:** ADR-004 documenta 3 gatilhos bloqueadores:
  1. Decisão sobre dono de `parcelas_pagamento` (é de `financeiro/pagamentos`?)
  2. Refatorar `_total_pago()` pra aceitar `db_path` (hoje usa global `DB_PATH`)
  3. Resolver atomicidade de `_gerar_recibo()` (toca 2 tabelas numa transação)

**Conclusão:** Criamos a **infra** correta sem mexer em `bot.py` ou violar ADRs. Automação aguarda as 3 decisões.

### Padrão aprendido

**Do Jeito Claude = Ler. Entender. Propor. Implementar. Documentar. (nessa ordem)**

---

## [DOCX removido, ADR-004 (modularização), matching PIX/NF-e corrigido] — 2026-07-02

### Motivação

Eric (filho do Dennis, estudando engenharia de software) comentou que `bot.py` parecia
"bagunçado" — virou o gatilho pra uma rodada de limpeza e organização.

### Removido

- Geração de Word (`python-docx`) em `gerar_pfm()` — PDF (HTML via Playwright) passa a ser o único
  documento gerado, confirmado por Dennis durante teste real. Helpers exclusivos do Word removidos
  (`_cell_bg`, `_set_col_widths`, `_secao_row`, `_kv_row`, `_data_extenso`)

### Corrigido

- **Segurança**: `bot.py` não tinha guard `if __name__ == "__main__":` — importar o módulo
  disparava `app.run_polling()` com o token real do Telegram. `import bot` agora é seguro
- `ITEM_RE` só reconhecia unidade de compra com até 4 letras — palavra por extenso ("blocos")
  caía no fallback sem preço unitário. Ampliado pra 15 letras (Lição #11)
- `buscar_candidatos_pix()` cortava em top-3 com desempate por ordem de inserção (favorecia
  pedidos mais antigos, escondendo candidatos legítimos mais novos em empate) — agora lista todos
  os pedidos com saldo em aberto, ordenados por score e proximidade de valor, com total pendente
  exibido na mensagem
- `buscar_candidatos_nfe()`/`vincular_nfe()` exigiam `status='pago'` — pedido em pagamento
  parcelado com nota já emitida pelo fornecedor não aparecia como candidato (caso real: GGV03-010).
  Vínculo de NF-e agora independente do status de pagamento — são registros paralelos
- Mensagem de confirmação de NF-e não dizia mais "Ciclo fechado" quando o pagamento ainda está em
  andamento — agora mostra "Pagamento em andamento: R$X de R$Y pago (faltam R$Z)"

### Adicionado

- Módulo `nfe/` (`nfe/__init__.py` + `nfe/nfe.py`) — parsing/exibição de NF-e extraído de `bot.py`,
  importável sem inicializar o bot (ADR-004)
- Dispatch table interna (`_CB_DISPATCH`) em `responder_botao()` — substituiu um `if/elif` de 929
  linhas (59 ramos) por 59 funções `_cb_*` nomeadas, mantendo um único `CallbackQueryHandler` e o
  mesmo tratamento de erro (ADR-004)
- Recibo (`_gerar_html_recibo()`) ganhou parágrafo narrativo com valor por extenso (`num2words`) e
  quantidade/unidade do item — modelo baseado no recibo antigo em Excel do GGV01 (Valdir Aparecida
  Silveira); layout em cartão mantido
- `docs/decisoes/ADR-004-modularizacao-bot-py.md` — modularização parcial de `bot.py`, decidida
  após processo de dois agentes independentes (propor + tentar derrubar)
- `docs/LICOES_EXTRACAO.md` — item #11 (unidade de compra por extenso)
- `.claude/settings.local.json` — restringe a skill `deep-research` a invocação explícita neste
  projeto (gestão de custo de IA)

### Auditoria (somente leitura, sem mudança de código)

7 agentes especializados varreram o código em busca de reinvenção de bibliotecas prontas. Achado
real aplicado: conversor de número por extenso manual (~85 linhas) trocado por `num2words`,
validado byte-a-byte. A auditoria também encontrou uma vulnerabilidade de segurança real (ver
"Próximas fiadas" no topo deste arquivo) e dois bugs de correção (`_parse_nfe()` não reusando
`_parse_brl()`; comparação de campo errado em `buscar_candidatos_pix()` — nome fantasia vs. razão
social) — catalogados como dívida técnica, não corrigidos nesta sessão.

---

## [Incidente crítico: documento de pedido pago apagado por botão antigo] — 2026-07-02

### O que aconteceu

Dennis relatou não conseguir acessar o GGV03-007 (já pago). O documento raiz (`documentos.id=28`)
tinha sido apagado do banco — o lançamento sobreviveu intacto (a lista de pedidos continuava
mostrando certo), mas a busca direta pelo código não encontrava mais nada.

**Causa raiz**: `_descartar_documento()`, criado ontem pro botão "Cancelar" (ver fiada de
"produção ativada"), não verificava se o documento já tinha virado um pedido de verdade antes de
apagar. Telegram mantém botões de mensagens antigas clicáveis para sempre — um toque num
"Cancelar" de uma mensagem de semanas atrás (de quando o GGV03-007 ainda estava em numeração
antiga) disparou o descarte num documento já pago.

### Correção

- `_descartar_documento()` agora recusa apagar documento com `pfm_numero` preenchido, a menos que
  `force=True` — usado só por "🗑 Excluir pedido", que já tem tela de confirmação explícita
- Botão "Cancelar" mostra alerta claro quando a recusa acontece, em vez de falhar silenciosamente

### Recuperação

Arquivos reais (PFM em `.docx`/`.pdf`, comprovante, NF-e) continuavam intactos no OneDrive — só o
vínculo interno do banco tinha sumido. Documento reconstruído lendo o PDF real gerado (mesmos
valores exatos: subtotal R$3.700, desconto R$100, total R$3.600) e reaproveitando a observação já
registrada sobre a correção do item com a Espaço Azul/Heliadi. Restaurado duas vezes — a primeira
tentativa foi apagada de novo (outro botão antigo) antes do bot subir com a correção; a segunda,
já protegida, ficou estável.

### Esclarecimento paralelo (sem código)

A confusão "Base Forte" vs. "Espaço Azul Materiais para Construção Ltda" se resolveu: são a mesma
empresa, "Base Forte" é o nome fantasia. O cadastro de fornecedor já estava correto
(`nome='Base Forte'`, `razao_social='ESPACO AZUL...'`) — a confusão era só de nome de arquivo no
OneDrive, não do sistema.

### Segundo bug: Observações não aparecia no cockpit

Dennis achou que a observação registrada sobre a correção do item (água fria × esgoto) tinha se
perdido de novo — estava salva certinha no banco, mas o cockpit do pedido (`mostrar_pedido()`)
nunca exibia o campo Observações, só a tela de resumo antes de confirmar. Corrigido: `Pedido`
ganhou o campo `observacoes`, cockpit mostra "📝 Obs: ..." quando existe algo registrado.

### Terceiro bug: `_obs()` nunca capturava o formato real

Mesmo depois da correção acima, a observação continuou sumindo — `_obs()` só reconhecia texto em
**linhas separadas** abaixo de "Observações:", mas o formato real (usado em 100% dos casos
observados no projeto) sempre foi tudo **na mesma linha**. A função pulava essa linha inteira sem
capturar nada — provavelmente quebrada silenciosamente desde que foi escrita. Corrigida pra
aceitar os dois formatos; também passou a usar `_campo_vazio()` pra não mostrar "não informado"
como se fosse uma observação real.

### Navegação: "Cancelar" virou "← Voltar"

Ao clicar num "Cancelar" de mensagem antiga já vinculada a um pedido, o fluxo abria uma tela
intermediária ("Mensagem antiga — esse documento já é o pedido #X" + botão) antes de chegar no
cockpit — dois cliques. Simplificado pra abrir o cockpit direto, um clique só. Os três botões
"Cancelar" do fluxo de orçamento e confirmação inicial foram renomeados pra "← Voltar", seguindo o
padrão já usado em todo o resto da Laura — a lógica de fundo não mudou, só o rótulo e a navegação.

---

## [Enriquecimento de fornecedor via Receita — e-mail, telefone, CNAE] — 2026-07-02

### Fornecedor: nome não reaproveitado, e mais dados da Receita

- **Bug corrigido**: a tela de resumo (antes de gerar o pedido) travava o nome do fornecedor como
  "Fornecedor não identificado" mesmo quando só o CNPJ era informado e o fornecedor já existia no
  cadastro — nunca consultava `buscar_fornecedor()`. Corrigido pra seguir o mesmo padrão já usado
  em CNPJ/PIX e no PDF/PFM final.
- `_consultar_receita()` ampliada: além de razão social/cidade/UF, agora também extrai e-mail,
  telefone (`ddd_telefone_1`/`ddd_telefone_2`) e CNAE — tudo já vinha na mesma resposta da
  BrasilAPI, só não estava sendo aproveitado
- Novo campo `fornecedores.cnae`: código oficial formatado no padrão do Cartão CNPJ (ex:
  "47.44-0-99") + descrição da atividade econômica principal, separado de `ramo` (que continua
  vindo do documento; CNAE só entra como fallback quando o documento não especifica)
- Sincronização retroativa rodada nos 27 fornecedores já cadastrados (o job periódico só mexe em
  pendências, e nenhum estava mais pendente) — 22 ganharam telefone, todos os 27 ganharam CNAE;
  e-mail raramente vem preenchido na Receita (dado pouco comum de existir publicamente)

### Operacional

- Bot caiu com `sqlite3.OperationalError: database is locked` ao reiniciar — o DB Browser for
  SQLite estava aberto com o `laura.db`, segurando o arquivo. Resolvido fechando o programa.
  Lição: nunca deixar visualizador de SQLite aberto enquanto o bot está rodando.

---

## [Sincronização com a Receita sempre ativa, com política por campo] — 2026-07-02

### Job periódico deixa de mexer só em pendências

Job de 6h passou a resincronizar **todos** os fornecedores com CNPJ, não só os marcados
`receita_pendente=1` — antes disso, toda vez que um campo novo fosse adicionado (como o CNAE),
seria preciso rodar um script manual pra propagar pros fornecedores já cadastrados.

Três políticas diferentes por tipo de campo, decididas em conversa (não é um "sempre sobrescreve"
genérico):

- **Razão social, cidade, UF, CNAE**: sempre atualiza com o dado mais recente da Receita — dado
  oficial de cadastro, baixo risco de estar errado
- **Ramo**: continua priorizando o texto natural já salvo (extraído de documento real, ex:
  "Comércio de Materiais de Construção"); o CNAE da Receita (mais burocrático) só entra como
  fallback quando ainda não há nada — "ramo é uma coisa, CNAE é outra"
- **E-mail, telefone**: só preenchem se ainda estiverem vazios, nunca sobrescrevem — risco real
  de a Receita estar desatualizada nesses dois (empresa atualiza endereço por obrigação legal,
  raramente atualiza contato)

`_sincronizar_receita_pendentes` renomeada para `_sincronizar_receita_fornecedores` (nome não
refletia mais o comportamento). Só grava no banco e avisa o Dennis quando algo muda de verdade —
sem mensagem repetida a cada 6h sem novidade nenhuma.

---

## [Produção ativada + cadastro retroativo completo de GGV03] — 2026-07-01

### Primeira vez rodando de verdade, e o que isso revelou

`LAURA_ENV=prod` ativado. Banco de produção zerado de novo por decisão de Dennis (incluindo o
GGV03-001 de teste do Valdir/Sabiá) — cadastro retroativo das compras pendentes de GGV03 passou a
ser feito 100% pelo Telegram, ao vivo, com acompanhamento em paralelo direto no banco. 8 pedidos
reais registrados (GGV03-001 a 008): CREA, DeltaD/projetos, DeltaD/gestão (parcelado), ONR,
Costaferro, Carlessi, Espaço Azul, Eletroluz — 7 pagos, 1 em aberto. Isso expôs, um por um, bugs
reais de parsing e de integração que nunca tinham aparecido com dado fictício.

### 10 bugs de extração/parsing corrigidos (catálogo completo em `docs/LICOES_EXTRACAO.md`)

- **Template de campos misturado**: um boleto (classificado como orçamento) voltou com campos de
  comprovante_pix E de orçamento concatenados — PROMPT agora proíbe explicitamente misturar
- **Fornecedor confundido com CNPJ da própria empresa**: guard que ignora CNPJ próprio em
  `buscar_fornecedor()` só cobria a VII; ampliado pra um conjunto (`CNPJS_PROPRIOS_DIGITS`) que
  também cobre a DeltaD — boletos frequentemente mostram uma das duas como Pagador
- **Unidade com dígito quebrava item**: "100,0 m2" (sem superíndice) não batia com `ITEM_RE`
  (só aceitava letras); ampliado pra aceitar dígito/superíndice no final da unidade
- **`_parse_brl` interpretava milhar como decimal**: "R$ 5.000" (sem vírgula) virava 5,00 em vez
  de 5000,00 — nova heurística: sem vírgula, "." com 3 dígitos depois é separador de milhar
- **Data sem zero à esquerda ilegível**: "5/06/2026" virava "6 /20" no histórico — parser trocado
  de fatiamento de índice fixo pra regex tolerante a 1 ou 2 dígitos
- **Documento que falha travava o hash**: comprovante sem pedido correspondente, ou cancelado,
  ficava permanentemente bloqueado pra reenvio — `_descartar_documento()` agora limpa registro e
  arquivo automaticamente nesses casos
- **PIX do fornecedor não reaproveitado**: pedido novo do mesmo fornecedor não puxava o PIX já
  conhecido — tela de resumo passou a consultar `buscar_fornecedor()`, e o cadastro (automático ou
  manual) passou a persistir PIX, não só `ramo`
- **Filtro de "campo vazio" só reconhecia gênero masculino**: "Não identificada" (concordando com
  "chave") passava como dado real; `_campo_vazio()` agora tolera gênero e frases mais longas
- **Pagamento parcial não encontrava o pedido**: comprovante de R$2.500 contra um pedido de
  R$30.000 não batia — `buscar_candidatos_pix()` só reconhecia valor exato ou ±10%; agora compara
  com o saldo restante (valor menos parcelas já pagas) e aceita qualquer valor parcial
- **Bloco de entrega do PDF ignorava o endereço real**: sempre mostrava "Obra GGV03" fixo, mesmo
  com o endereço de verdade já salvo no banco — corrigido pra exibir o endereço real

### Novo — excluir pedido

- Botão "🗑 Excluir pedido" no cockpit, com tela de confirmação — apaga lançamento, parcelas,
  fotos de entrega e todos os documentos vinculados na Laura (nunca toca em arquivo já arquivado
  no OneDrive). Testado com pedido fictício antes de liberar em produção.

### Novo — endereço automático e observações editáveis

- Endereço de entrega preenchido sozinho com o padrão da obra assim que o GGV é identificado —
  sem precisar clicar em "🏗 Obra" toda vez; continua editável depois pelo Corrigir campos
- Observações do pedido virou campo editável em "Corrigir campos" — antes só aparecia na tela
- Botão "✖ Cancelar" adicionado na tela de escolha de tipo de documento — antes, quem chegasse ali
  sem querer não tinha como sair

### Operacional

- Descoberto e corrigido: dois processos `bot.py` rodando ao mesmo tempo causam conflito de
  polling no Telegram (efeito "bot fora de serviço") — só uma instância deve rodar por vez
- Botões renomeados pra refletir que aceitam foto ou arquivo, não sugerir só um dos dois
  ("📋 Orçamento / Fatura", "📦 Foto/arquivo de entrega")
- `docs/LICOES_EXTRACAO.md` criado e alimentado com os 10 bugs — catálogo vivo de armadilhas,
  leitura obrigatória antes de mexer em PROMPT/regex (linkado em `docs/PROCESSO.md`)
- Limpeza retroativa de documentos "cancelado" que sobraram de antes do descarte automático
  existir, e de um arquivo órfão no OneDrive de um pedido excluído (Base Forte/GGV03-006 antigo)

Testado ao vivo com os 8 pedidos reais completos de GGV03 — 7 pagos, 1 em aberto (pagamento
parcelado em andamento).

---

## [Base de insumos SINAPI (referência)] — 2026-07-01

### Tabela de referência de materiais, sem vínculo com o bot ainda

Objetivo de longo prazo declarado por Dennis: reconhecer automaticamente qual insumo de referência
(padrão nacional) corresponde a um item de orçamento com descrição livre de fornecedor, mantendo
fabricante como dado comercial separado — sem depender do SINAPI, usando-o só como linguagem comum.
Antes de qualquer código, tivemos uma sessão longa só de conceito (premissas, entidades do domínio,
como ERPs de construção resolvem isso, armadilhas de equivalência técnica × comercial).

- Agentes de engenharia/arquitetura invocados antes de decidir a fonte de dado (mesmo processo já
  usado para a decisão de extrair `entrega/`, ver ADR-003): avaliado usar o projeto open-source
  `AutoSINAPI`/`autoSINAPI_API` do GitHub (stack Docker com Postgres + API REST + gateway Kong)
  contra baixar a planilha oficial da Caixa direto. Descartado o stack Docker — Dennis não tem
  Docker instalado, o próprio `AutoSINAPI` tem a URL de download oficial quebrada (a Caixa mudou a
  estrutura de pastas em 2025 e o projeto não acompanhou, confirmado baixando de verdade), a
  variante com API não tem nenhum modo sem Docker (7 serviços), e ambos os repositórios são
  mantidos por uma única pessoa
- `scripts/import_sinapi.py`: mesmo padrão de `scripts/import_fornecedores.py` — script único, roda
  manualmente, sem serviço externo. Baixa `SINAPI-{ano}-{mes}-formato-xlsx.zip` direto do site da
  Caixa (sem login), tentando os últimos 6 meses até achar um publicado
- Lê a aba `ISD` (Insumos Sem Desoneração — regime confirmado com Dennis), filtra
  `Classificação = MATERIAL`, usa a coluna de preço do Paraná
- Nova tabela `insumos_sinapi(codigo, descricao, unidade, preco_pr, mes_referencia, fabricante,
  atualizado_em)` — reexecutar o script atualiza preço/descrição por código mas nunca sobrescreve
  `fabricante`, que fica pra Dennis preencher aos poucos
- Testado de ponta a ponta contra produção: 4.365 insumos de material importados (referência
  05/2026); idempotência confirmada (fabricante setado manualmente sobreviveu a uma reimportação)

**Deliberadamente não implementado ainda:** nenhum vínculo com `bot.py` — sem matching automático,
sem tela no Telegram, sem `FOREIGN KEY` com `documentos`/`lancamentos`. Tabela de referência pura
por decisão — o gatilho real para conectar isso ao fluxo da Laura é a futura fase "lista de
compras", que só começa depois de subir as informações pendentes de GGV03.

---

## [Pagamento parcelado + ciclo de assinatura de recibo] — 2026-07-01

### Pagamento em parcelas, cada uma com seu próprio recibo assinado

Validando o recibo de GGV03-001 com Dennis, ficou claro que pagamento de mão de obra não é um
evento único: prestadores recebem em parcelas de valor e período livres até quitar o total, e cada
parcela paga precisa do seu próprio recibo assinado antes de fechar o ciclo. Por decisão explícita,
o modelo passou a valer para **todos os pedidos** — à vista é só um caso particular de parcelado.

- Nova tabela `parcelas_pagamento`: cada pagamento parcial vira uma linha vinculada ao
  `pfm_codigo`, com ciclo próprio `pago` → `aguardando_assinatura` → `assinado`
- `lancamentos.status` só vira `pago` quando a soma das parcelas atinge o valor do pedido; antes
  disso mostra progresso: "Aguardando pagamento · R$ 3.500,00 de R$ 70.000,00 pago"
- `pix_pagar` reescrito: todo comprovante recebido gera uma nova parcela; deduplicação de
  comprovante agora é por parcela, não mais por pedido inteiro
- `_gerar_recibo()` passa a ser por parcela — cada parcela paga gera seu próprio PDF, arquivado em
  `05 Entrega/` como `recibo-parcelaN`
- Tela "Ver parcelas" no cockpit: lista cada parcela com valor/data/status; ações para gerar
  recibo, ver o pendente de assinatura, ou anexar a versão assinada de volta
- Ciclo de assinatura fechado de ponta a ponta: recibo sai da Laura → assinado fora dela (ex:
  gov.br) → volta e substitui o arquivo em `05 Entrega/`, parcela vira `assinado`
- Recibo redesenhado em A5 paisagem com espaço de assinatura no rodapé, a partir de feedback
  direto no PDF gerado para GGV03-001 (cabeçalho simplificado: só "RECIBO" + código + data)
- Status obsoleto `pago_com_recibo` removido do `StatusPedido` — granularidade correta é a
  parcela, não o pedido

### Esclarecimento DeltaD × VII

Pesquisa nos CNPJs oficiais (Receita Federal) confirmou: DeltaD Engenharia é a marca da Verschoor
Construções Civis Ltda (CNPJ 48.494.891/0001-06, responsável técnica pela obra); a constante
`DELTAD` no código sempre guardou os dados corretos da Verschoor Investimentos Imobiliários Ltda —
VII (CNPJ 58.358.802/0001-58), dona real dos empreendimentos e CONTRATANTE correta no recibo. Por
decisão de Dennis, a DeltaD não participa do fluxo de compras — é só mais um fornecedor da VII.
Nenhuma restruturação de código; apenas um comentário explicativo sobre a constante `DELTAD`.

Testado de ponta a ponta com o pedido real GGV03-001 (Valdir Aparecida Silveira, R$ 70.000,00):
parcela parcial → progresso exibido → recibo gerado → assinatura simulada → segunda parcela
completando o total → pedido corretamente marcado `pago`.

**Pendência real, não é da Laura:** o recibo de GGV03-001 ainda não foi enviado pro Valdir assinar
de verdade — o teste de hoje validou o mecanismo, não o ciclo completo com assinatura real.

---

## [Fiada 6b — Geração automática de recibo] — 2026-07-01

### Recibo em PDF para quem não tem nenhum documento de fechamento

Complementa a fiada de taxas/impostos/serviços públicos: aquela resolveu entidades que já têm seu
próprio documento (fatura). Esta cobre o caso restante — fornecedor/prestador informal (mão de
obra autônoma, sem CNPJ) — onde não existe documento nenhum e a Laura precisa gerar o recibo.

- Cockpit do pedido pago sem NF-e ganha o botão "📄 Sem NF — gerar recibo" (fora das categorias
  já resolvidas automaticamente)
- Motivo da exceção com sugestões prontas (Autônomo sem CNPJ · Prestador informal · Órgão/entidade
  sem NF-e · Outro)
- Recibo gerado em PDF via Playwright — mesmo estilo visual do Pedido de Compra 2.0. CONTRATANTE é
  `DELTAD["nome"]` ("Verschoor Investimentos Imobiliários Ltda", dono real do empreendimento — não
  "DeltaD Engenharia", que é só o rótulo de marca do cabeçalho do PFM)
- Novo status `pago_com_recibo`; nova coluna `lancamentos.doc_id_recibo`
- `fornecedores.emite_nf` marcado automaticamente ao gerar o primeiro recibo do fornecedor
- Recibo arquivado em `05 Entrega/`, registrado como documento — pode ser visualizado depois
  pelo cockpit ("📄 Recibo")

Testado de ponta a ponta com prestador fictício: botão aparece só quando deveria, PDF gerado e
arquivado, status e cockpit atualizados corretamente, `emite_nf` marcado quando o fornecedor
já está cadastrado.

---

## [Taxas, impostos e serviços públicos no fluxo de compra] — 2026-07-01

### CREA, ONR, prefeitura, Copel, Sanepar reaproveitam o pipeline de compra

Em vez de um fluxo paralelo para despesas sem orçamento negociado, essas entidades passam pelo
mesmo caminho de sempre (orçamento → PFM → pagamento), só com categoria e fechamento diferentes.

- Prompt reconhece boleto/fatura/conta de consumo como `[orcamento]` — antes só reconhecia
  cotação de material, risco de cair em "não relacionado"
- Categorias `taxa`/`imposto`/`servicos` fecham o pedido com "Pago" — sem cobrar NF-e
- Fatura original arquivada de novo em `01 Controle financeiro` como "fatura" (terceira via) ao
  confirmar o pagamento, junto do comprovante
- Documento do Pedido de Compra oculta campos de entrega (data, endereço, aviso de foto) para
  essas categorias — não fazem sentido para uma anuidade ou conta de consumo
- Novo campo `categoria` no `Pedido`; nova constante `CATEGORIAS_SEM_NFE_OBRIGATORIA`

### Pesquisa antes de mudar a regra do RET

Antes de dispensar a exigência de NF-e (regra existente por causa do Regime Especial de
Tributação), pesquisamos o que cada entidade realmente emite: nenhuma tem documento fiscal
separado da fatura — Copel já é a própria nota fiscal (NF3e), as demais não emitem NF-e, só
fatura/boleto/guia. A fatura que já era enviada como orçamento já é o documento de fechamento.

---

## [Organização automática de arquivos por obra] — 2026-07-01

### Cada obra passa a saber seus próprios caminhos e nomes

Antes de colocar a Laura para rodar, os documentos passaram a se organizar sozinhos na pasta
OneDrive de cada obra, seguindo a convenção que Dennis já usava manualmente.

**Fiada 1 — Orçamento + PFM → `04 Compras`**
- Novo campo "Resumo da compra" no PROMPT (2-4 palavras, ex: "Espelho", "aço")
- PFM salvo como `GGV03-008 - Fornecedor - Resumo.docx` — e agora também `.pdf`, persistido em
  disco (antes só era enviado pelo Telegram, nunca gravado)
- Orçamento original arquivado em `04 Compras/00 Orçamentos/`, mesmo padrão de nome
- Revisão (`pfm_revisar`) sobrescreve o arquivo principal mantendo o nome correto
- Nova coluna `documentos.caminho_pfm` — resolve a dívida técnica de reconstruir o caminho a
  cada consulta

**Fiada 2 — Comprovante + NF-e → `01 Controle financeiro`**
- Nome com a data real do documento (pagamento / emissão da NF-e), não a data de hoje
- `_data_para_arquivo()` entende `DD/MM/AAAA` e `DD de mês de AAAA`

**Fiada 3 — Fotos de entrega → `05 Entrega`**
- Numeração sequencial (`foto01`, `foto02`...), extensão original preservada
- Recibo (Fiada 6b, ainda não implementado) vai cair no mesmo lugar

### Correção estrutural

- `obras.pasta_onedrive` mudou de significado: guarda a raiz da obra, não mais uma subpasta
  específica. `_pasta_pfm()`, `_pasta_controle_financeiro()` e `_pasta_entrega()` derivam cada
  subpasta por convenção.

### Escopo

- GGV03 e GGV00 configuradas com a convenção nova
- GGV01 **intocada** — regra explícita, nunca escrever na estrutura antiga dela
- GGV02 (em conclusão) sem `pasta_onedrive` configurada — estrutura própria diferente, decisão
  de onde arquivar pendente

---

## [Auto-cadastro de fornecedor via Receita Federal] — 2026-07-01

### Cadastro automático ao gerar PFM

- Fornecedor com CNPJ que não bate com nenhum cadastro existente é criado automaticamente na
  hora de gerar o PFM, sem esperar por importação manual
- Consulta à Receita Federal (BrasilAPI, gratuita e sem autenticação) enriquece o cadastro com
  razão social, cidade e UF oficiais — timeout de 4s, nunca trava a geração do PFM
- Se a consulta falhar, o fornecedor é criado mesmo assim com o que o Claude extraiu, marcado
  `receita_pendente=1` para tentar de novo depois

### Sincronização em segundo plano

- Job periódico (`JobQueue`, a cada 6h) tenta de novo os fornecedores pendentes
- Silencioso quando não há pendência; avisa Dennis só quando sincroniza algo:
  "📋 Receita sincronizada — N de M pendências resolvidas"
- Nova dependência: `python-telegram-bot[job-queue]` (traz `apscheduler`)

---

## [Preparação para produção — migração e limpeza de dados] — 2026-07-01

### Banco de produção migrado

- `data/laura.db` estava com schema desatualizado desde antes da Fase 4a — bot só era testado via
  `LAURA_ENV=test`. Aplicado o `init_db()` atual: tabela `obras` criada e populada (GGV00-03),
  `entrega_fotos` criada, colunas de `lancamentos`/`documentos`/`fornecedores` atualizadas.
  Migração aditiva — nenhum dado existente alterado.

### Fornecedores validados contra a Receita Federal

- 28 → 27 cadastros (1 duplicata removida — Reginaldo Wendler importado duas vezes)
- CNPJ da MO Construção corrigido: estava gravado com o CNPJ da própria DeltaD; é pessoa física
  (CPF de Valdir Aparecido Silveira)
- Chave PIX da Costa Ferro corrigida (estava com o CNPJ da Base Forte); Jhonatan Rogowski
  (estava com valor inválido "pix:")
- Cidade/UF corrigidos em 22 cadastros via API pública da Receita (BrasilAPI) — UF estava 100%
  vazia; 9 cadastros tinham cidade poluída com o nome do próprio Dennis/DeltaD
- Razão social oficial completa em 6 cadastros com valor truncado
- 6 nomes que eram descrição de item, não de fornecedor, corrigidos (ex: "Aco 6_3" → "Frísia")

### Pedidos zerados por decisão

- `documentos` e `lancamentos` de produção zerados — eram uma mistura de teste inicial (bugs de
  fase 1) com 19 PFMs reais, 17 dos quais sem lançamento financeiro (criados antes de
  `registrar_lancamento()` existir). Arquivos já gerados na pasta OneDrive **preservados**;
  numeração de PFM reinicia em 001.

---

## [Fase 6 — Fiada 6c++ — Múltiplas fotos de entrega + navegação] — 2026-06-30

### Entrega com N fotos, cada uma com legenda obrigatória

- Tabela `entrega_fotos`: substitui o vínculo único `doc_id_entrega` — um pedido pode ter várias fotos
- Legenda obrigatória ao anexar qualquer foto ou documento de entrega
- Tela "👀 Ver arquivos" lista as fotos por legenda; ícone 📷 para foto, 📄 para PDF
- Remoção de foto individual (lista por legenda), sem afetar as demais
- Rótulo "N arquivos" sempre recalculado do banco — singular/plural correto após edições

### Navegação e polimento de UI

- `← Voltar` adicionado aos submenus Ajuda e Obras, retornando ao menu inicial ("Por onde quer começar?")
- Botão de adicionar foto renomeado para "📎 Adicionar foto ou arquivo" (reflete que PDF também é aceito)
- Ícone do botão "Apagar entrega" trocado para `❌`, diferenciado de "🗑 Remover arquivo"

### Decisão arquitetural

- **ADR-003 registrada**: extração do domínio entrega de `bot.py` (3277 linhas) avaliada e adiada —
  dados de entrega ainda acoplados a `lancamentos` (Financeiro) e `documentos` (Pedido); feature sem
  uso real em produção. Gatilho de revisão explícito em `docs/decisoes/ADR-003-extracao-entrega-adiada.md`

---

## [Fase 6 — Fiada 6c+ — Gestão de Entrega] — 2026-06-30

### Edição, exclusão e anexo de foto durante o fluxo de observação

- Botão `✏️ Editar entrega` no cockpit sempre que entrega estiver registrada
- Tela de gestão exibe obs atual e se há foto; botões contextuais:
  - `✏️ Mudar observação` → seletor de obs com ← Voltar; suporta texto livre
  - `🔄 Trocar foto` / `📎 Anexar foto` → substitui ou adiciona foto sem alterar obs
  - `🗑 Remover foto` → remove só a foto, mantém obs e data
  - `🗑 Apagar entrega` → limpa obs, foto e data; cockpit volta ao estado "não entregue"
  - `← Voltar` → retorna ao cockpit do pedido
- `📎 Foto / Documento` na tela "Como foi a entrega?" permite anexar antes de confirmar obs
- Cockpit corrigido: quando há obs E foto, exibe ambos `📦 Foto de entrega` + `✏️ Editar entrega`
- DB helpers: `_atualizar_foto_entrega`, `_atualizar_obs_entrega`, `_apagar_entrega_db`, `_buscar_estado_entrega`

---

## [Fase 6 — Fiada 6c — Foto de Entrega e Registro de Entrega] — 2026-06-30

### Ciclo logístico fechado: pedido → pago → NF-e → entregue

- Novo tipo de documento `foto_entrega` no seletor — sem análise Claude, vai direto à seleção do pedido
- `/entrega`: lista pedidos sem entrega registrada → seleciona → observação → grava
- Botão `📦 Entregue` no cockpit do pedido enquanto entrega não registrada; vira `📦 Foto de entrega` quando tem foto
- Teclado de observações com sugestões de Laura: Entrega completa · Entrega parcial · Material com avaria · Produto diferente · Outra
- Qualquer pedido pode receber entrega, independente de status (a_pagar ou pago)
- Cockpit: histórico com data e observação; `📦 Foto de entrega` nos arquivos quando houver foto
- Ajuda (`/help`) atualizada com "Incluir nota fiscal" e "Registrar entrega"
- Banco: colunas `doc_id_entrega`, `obs_entrega`, `entregue_em` em `lancamentos`

---

## [Fiada 6a+ — Contato vendedor na tela de extração] — 2026-06-30

- Bloco Fornecedor da tela de validação exibe `Contato   Flávio  42 99912-7781` quando extraído
- Menu "Corrigir dados" ganha botão `📞 Contato vendedor` — edita nome e telefone em uma linha
- Parser separa telefone (dígitos no final) do nome automaticamente

---

## [Fase 6 — Fiada 6a — Recebimento de NF-e + Revisão de Pedido] — 2026-06-30

### Ciclo documental completo: PIX → NF-e vinculada

A partir desta fiada, todo pedido pago tem um destino fiscal: a NF-e vinculada.
O cockpit do pedido exibe o número da nota; o botão abre o arquivo original.

**Recebimento de NF-e:**
- Novo tipo de documento `nota_fiscal` no seletor inicial
- PROMPT de extração: Número da NF, CNPJ/CPF emitente, Nome emitente, Valor total, Data de emissão
- `buscar_candidatos_nfe()`: busca pedidos pagos sem NF-e vinculada, ordena por score (CNPJ + valor)
- Correspondência forte (score > 0): vinculação com confirmação; sem correspondência: seleção manual
- Vínculo gravado em `lancamentos.doc_id_nfe`; NF-e arquivada em `documentos`

**Cockpit do pedido enriquecido:**
- Status: `🟢 Pago · NF-e 490224` quando nota vinculada; `🟢 Pago · NF-e pendente` quando não
- Arquivos: `💰 Comprov. pagamento` e `🧾 NF-e 490224` na seção de arquivos
- Botões condicionais: `💰 Comprovante` e `🧾 NF-e` — aparecem apenas quando vinculados
- Histórico: linha `25/06 · Pago pix E10573521...` + linha `30/06 · NF-e 490224`
- Botão "Financeiro" removido — informações integradas ao cockpit principal

**Revisão do Pedido de Compra:**
- `pfm_revisar` abre tela de revisão completa dos dados antes de regerar
- Confirmar na revisão gera `GGV03-005-R01.docx` (arquivo com revisão)
- `GGV03-005.docx` no OneDrive é sempre sobrescrito com o conteúdo mais recente
- PDF do PC 2.0 enviado no chat a cada revisão; lançamento financeiro mantido inalterado
- `rev_numero` em `documentos` rastreia quantas revisões foram feitas

**Bugs corrigidos:**
- `ITEM_RE`: captura preço unitário separado do subtotal (formato `R$ 12,00 cada = R$ 144,00`)
- `_recalcular_itens()`: ao salvar edição de itens, recalcula `total = qtde × unit` e atualiza "Valor total"
- `edit_desconto`: desconto zero não era salvo (caía no valor original do banco)
- PROMPT de comprovante: prefere ID EndToEnd PIX (`E10573521...`) ao número MP

---

## [Sprint de Experiência — Jeito da Laura] — 2026-06-30

- **Jeito da Laura** nomeado e formalizado como princípio de comunicação assertiva do produto
- Revisão completa de todos os menus: boas-vindas, ajuda, lista de obras, cockpit da obra, lista de pedidos, cockpit do pedido, comprovante PIX, categoria do lançamento, tipo de documento
- Botão 📎 Orçamento no cockpit do pedido envia o arquivo original diretamente no chat
- Botão ◀️ Pedidos no cockpit do pedido; botão ◀️ Obras no cockpit da obra
- Histórico removido como tela separada (pendente reimplementação)

---

## [Sprint de Experiência — Navegação e Identidade] — 2026-06-30

- Boas-vindas: saudação ou texto não reconhecido abre menu com descrição de cada opção e 3 botões em linhas individuais
- Ajuda (`/help`, botão ❓): texto pessoal com cabeçalhos em negrito — "No que posso ajudar?" — guia o usuário por Pedido de compra, Pagamento e Consulta
- `/obras` registrado como comando Telegram; lista obras com título curto de cada GGV
- Lista de pedidos da obra: tela própria via "📋 Pedidos", cada pedido com emoji de status e valor
- Navegação direta: botão de pedido na lista abre cockpit do pedido
- Cockpit da obra: botão "✖ Fechar" + estrutura de bloco financeiro (placeholder para Fiada 5b-1)
- Botões de ação em linhas individuais em todos os menus — máxima largura no Telegram
- Processo: `mostrar_ajuda()` deve ser atualizado a cada nova ação visível ao usuário

---

## [Sprint de Experiência — Redesign de Cockpits] — 2026-06-30

### Cockpit do Pedido

- Header compacto: `🟢 #GGV03-005 — Pago` em vez de campos separados por label
- Valor final consolidado com desconto entre parênteses; condição e entrega na mesma linha
- CNPJ, vencimento vazio e labels redundantes removidos
- Botão "📄 Word" → "📄 PDF" — regenerado via Playwright na hora (sem dependência de arquivo em disco)
- Histórico completo implementado: orçamento recebido, pedido gerado, entrega prevista, pago com valor
- `data_pagamento` adicionada ao dataclass `Pedido` e à query de `buscar_pedido()`

### Cockpit da Obra

- Header: `GGV03 — Condomínio residencial` — código sem repetição na descrição
- Bloco financeiro placeholder (`⚪ Sem dados financeiros`) reservado para Fiada 5b-1
- CEP removido do endereço; separador ` - ` → ` · `
- Botões: `📋 Pedidos` · `✏️ Editar obra` · `✖ Fechar`

### Lista de Pedidos da Obra

- Tela própria via botão "📋 Pedidos": lista compacta com emoji de status, código, fornecedor e valor
- Botões individuais (2 por linha) com navegação direta ao cockpit do pedido
- "◀️ Voltar à obra" retorna ao cockpit do GGV

---

## [Fase 5 — Fiada 5a-1 — Categoria no Lançamento] — 2026-06-30

### O que mudou

- Ao clicar "✅ Gerar Pedido de Compra", Laura sugere a categoria do lançamento com base no ramo do fornecedor (`sugerir_categoria()` de `financeiro/lancamento.py`)
- Usuário confirma a sugestão ou seleciona manualmente entre todas as categorias disponíveis
- Lançamento gravado inclui `categoria`; exibida na mensagem de confirmação e na tela Financeiro do pedido
- Modo teste: deduplicação de comprovante PIX (por `identificador_comprovante`) bypassada em `TEST_MODE`, alinhando com o comportamento já existente para hash de arquivo

---

## [Fase 5 — Módulo Financeiro: Fiada 0 — Fundação] — 2026-06-30

### Marco de arquitetura de produto

Esta sessão foi uma sessão de arquitetura de produto, não apenas de engenharia.

Até aqui a Laura tinha um único objeto de domínio: o Pedido de Compra.
A partir desta fase nasce um segundo objeto igualmente importante: o Lançamento Financeiro.

> *"O Pedido de Compra registra uma decisão. O Lançamento Financeiro preserva suas
> consequências. Juntos, eles contam a história econômica da obra."*

**Princípio arquitetural registrado (ADR-002):**
> *"Todo novo domínio nasce modular. Os domínios existentes permanecem no monólito
> até existir um motivo real para migração. A modularização acontece por nascimento,
> não por refatoração."*

**Visão de longo prazo registrada:**
Surge naturalmente um terceiro grande objeto futuro: a **Obra** — não apenas como código
(GGV03), mas como agregador de Pedidos de Compra, Lançamentos Financeiros, documentos,
cronograma, custos e indicadores. Registrado no ROADMAP. Não implementado agora.

### Fiada 0 — Fundação (sem comportamento novo ao usuário)

- `financeiro/lancamento.py`: `CategoriaLancamento`, `StatusLancamento`, `TipoDocumento`,
  `sugerir_categoria()`, `init_db_financeiro()`
- `financeiro/conciliacao.py`: esqueleto documentado para Fase 5d
- `financeiro/__init__.py`: contrato público do domínio
- `app/README.md`: elimina ambiguidade da pasta reservada para ADR-003
- `bot.py`: `init_db()` passa a chamar `init_db_financeiro(DB_PATH)` ao iniciar
- `lancamentos`: novas colunas `categoria`, `tipo_documento`, `fonte_recurso`, `conciliado_em`
  adicionadas via ALTER TABLE idempotente

---

## [Fase 4b — Pedido de Compra 2.0] — 2026-06-30

### Novo documento — PC 2.0 em PDF

- Pedido de Compra gerado como PDF com design "A Carta" aprovado
- Layout em 7 zonas: cabeçalho · contexto · fornecedor · itens · financeiro · condições · tagline
- Ramo de atividade do fornecedor exibido abaixo do nome
- Número do orçamento, vendedor e telefone no bloco Origem
- Encarregado e endereço da obra no bloco Entrega
- Desconto exibido com percentual calculado automaticamente
- Tagline da Laura centralizada no fundo do documento
- DOCX continua gerado silenciosamente como backup no OneDrive

### Extração aprimorada pelo Claude

- 4 novos campos no PROMPT: Ramo de atividade, Número do orçamento, Vendedor, Telefone do vendedor
- Campo `ramo` adicionado à tabela `fornecedores` — salvo automaticamente ao gerar PFM

---

## [Fase 4a — Cadastro de Obras] — 2026-06-30

### Novo — Cockpit da obra

- Digitar `GGV03` abre o card da obra com dados cadastrais
- Botão "Editar obra" → seleciona campo → edita pelo chat
- `/nova_obra` para cadastrar novas obras conversacionalmente
- `/help` lista o que a Laura faz; comando desconhecido redireciona para `/help`
- Menu de comandos registrado no Telegram (aparece ao digitar `/`)
- Resposta "Não entendi." para texto que não corresponde a nenhuma ação

---

## [Housekeeping Documental] — 2026-06-29

### Marco de maturidade: engenharia → produto

Nenhum código alterado. Alinhamento dos documentos de processo e produto.

- `docs/PROCESSO.md` refatorado: dois tipos de sessão (Engenharia e Produto) com
  ordens de leitura distintas; etapa 2.5 — Validação da Identidade adicionada entre
  Planejamento e Implementação; "Quando NÃO desenvolver" ampliado com critério de
  identidade; preamble "A pergunta que abre tudo" registra a inversão identidade → implementação
- `docs/IDENTIDADE_DO_PRODUTO.md`: aprovação registrada; `docs/GLOSSARIO.md` adicionado
  à tabela de relações; seção "Marco de Maturidade" adicionada; `docs/PROCESSO.md`
  referenciado como repositório da etapa 2.5
- `docs/GLOSSARIO.md`: próxima revisão atualizada para Fase 2
- `docs/ROADMAP.md`: Fase 2 movida de "Próxima Fiada" para "Em Andamento" com
  detalhamento do que foi implementado e do que ainda está pendente

---

## [Sprint de Experiência — Fase 2] — 2026-06-29

### Estrutura — tela de validação do orçamento

Tela `_resumo_gerar` redesenhada como preview completo do Pedido de Compra.
Nenhuma regra de negócio alterada. Nenhum dado perdido.

**Layout aprovado (6 blocos):**
1. Obra (identificada ou não)
2. Fornecedor + CNPJ + PIX
3. Itens (lista completa) + Total bruto
4. Valor final (negrito) + Desconto (se houver) + Condição de pagamento + Vencimento
5. Logística: entrega, endereço, validade, contato (Dennis + encarregado da obra)
6. Observações (sempre exibido — "não informado" quando vazio)

**Implementações:**
- `teclado_orcamento()` unificado — substitui `teclado_confirmacao` + `teclado_gerar`;
  bloqueia geração se obra não identificada; botão "Conferir itens" removido
  (itens visíveis diretamente no layout)
- Botão Voltar em `sel_ggv`, `teclado_condicao`, `teclado_endereco`
- Campos `vencimento_pgto` e `encarregado` no banco (via `ALTER TABLE` seguro),
  na tela de validação e nos botões de correção
- `GGV_ENCARREGADO` dict — padrão por obra, substituível por documento
- `DELTAD["ie"] = "Isento"` adicionado para uso futuro no Pedido de Compra
- `parse_mode="HTML"` em todas as chamadas do resumo — `parse_mode="Markdown"`
  causava `TimedOut` quando itens extraídos pelo Claude continham `**` não balanceados;
  `_esc_html()` adicionada para escapar dados externos
- `"Obra GGV03"` como label em vez de `"GGV03"` isolado

---

## [Sprint de Experiência — Fase 1] — 2026-06-29

### Voz — reescrita de todas as mensagens do bot

Nenhuma lógica alterada. Apenas linguagem e estrutura visual.

**Critério de aceite aplicado:** enviar um orçamento e gerar um pedido sem encontrar
nenhuma mensagem com linguagem interna, emojis decorativos ou estrutura contrária
aos padrões definidos na Sprint de Experiência.

**Aplicações do Glossário:**
- "PFM" → "Pedido de Compra" em todas as mensagens e no próprio documento Word
- "A PAGAR" → "🟡 Aguardando pagamento" (e demais status com labels corretos)
- "Editar campos" → "Corrigir campos"
- "Lançamento" → "Financeiro" (nas telas de usuário)
- "Candidatos" → removido; "Qual pedido este pagamento quita?" como linha guia
- "Comprovante identificado" → "Pagamento identificado."
- "Possíveis correspondências" → "Qual pedido este pagamento quita?"
- "PFM gerada · lançamento criado" (histórico) → "Pedido de Compra gerado"
- "Arquivo salvo. Que tipo de documento é este?" → "Documento recebido. O que você trouxe?"
- "Revisar e gerar PFM." → "Confirmar para gerar o Pedido de Compra."
- "GGV não identificado" → "Obra não identificada"

**Emojis decorativos removidos:** `❌`, `⚠️`, `⏳`, `💰`, `📅`, `📍`, `💲`, `🏷️`,
`✅` (fora de botões), `💾`, `👤`, `📌`, `🕐`, `📎`, `🔄` das mensagens de texto.
Mantidos: 🟡🟢🔴⚫⚪ (marcadores de status) e 🧪 (modo teste).

---

## [Sprint de Experiência — Fase 0] — 2026-06-29

### Glossário e base da Sprint de Experiência

- `docs/GLOSSARIO.md` criado — decisões de linguagem com justificativa para cada termo
  aprovado, cada termo banido e cada distinção conceitual relevante
- `docs/IDENTIDADE_DO_PRODUTO.md` atualizado — segunda frase fundadora adicionada:
  *"Laura não espera ser perguntada. Ela mostra o que precisa de atenção."*
- ROADMAP atualizado: quatro fases de implementação definidas (Voz → Estrutura →
  Navegação → Pedido de Compra) substituem "Design System" e "Apresentação Profissional"
  como nomenclatura de fiadas

**Decisões de linguagem aprovadas no Glossário:**
- Corrigir vs. Ajustar: distinção conceitual entre correção de extração e decisão deliberada
- Cockpit vs. Painel: a visão do GGV é um cockpit ativo, não um painel passivo
- Orçamento vs. Pedido de Compra: objetos distintos, direções opostas
- Comprovante vs. Extrato: pagamento único vs. histórico de conta

---

## [Sprint de Produto] — 2026-06-29

### Sprint de Design e Identidade — fundação do produto

Encerra a fase de engenharia e abre a fase de produto.
Esta Sprint não alterou código. Definiu quem a Laura é.

**O que foi construído:**

- `docs/IDENTIDADE_DO_PRODUTO.md` — constituição de produto da Laura
  - Missão, visão de cinco anos e promessa central
  - Personalidade, voz e sistema de status visual
  - Princípios de UX, design, navegação e tomada de decisão
  - O que a Laura faz e o que ela nunca fará
  - O que o usuário ganha (transformação antes/depois)

**Decisões de produto aprovadas:**

- A promessa central da Laura: *"Você nunca vai perder o rastro de uma compra."*
- PDF é o artefato canônico do Pedido de Compra. Word é saída secundária.
- "PFM" não existe para o usuário — apenas "Pedido de Compra" e o código (ex: GGV03-009).
- Sistema de status unificado: 🟡 🟢 🔴 ⚫ ⚪ — únicos emojis semânticos permitidos.
- Emojis decorativos são banidos da interface.
- Seleção manual de tipo de documento é um andaime — deve desaparecer no produto maduro.
- Princípio central de produto: *"Laura vem até o usuário. O usuário não adapta seu fluxo para Laura."*

**Frase que define o produto:**

> *"Laura não é uma ferramenta que você usa. É uma memória que você carrega."*

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
