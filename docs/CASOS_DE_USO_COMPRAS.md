# Casos de Uso — Domínio de Compras

> Este documento não define princípios (ver `docs/POLITICA_COMPRAS.md`) nem arquitetura
> (ver `docs/ARQUITETURA.md`). Ele mostra como a Política de Compras acontece na prática,
> através de histórias completas do dia a dia da empresa.
>
> Cada caso vai da necessidade até o aprendizado que fica depois da compra. A linguagem
> é de negócio, não de sistema — qualquer pessoa que entre no projeto deve entender como
> esperamos que a Laura participe do processo, sem precisar ler uma linha de código.

---

## Os Três Momentos da Laura

Lendo os casos a seguir, um padrão se repete em todos: a Laura participa em três momentos
distintos de cada compra, nunca fora deles.

**Antes da compra** — ajuda a lembrar, ajuda a montar a lista, apresenta referências de
preço e fornecedor. É onde a necessidade se organiza.

**Durante a compra** — quando o orçamento negociado chega, organiza as informações,
compara contra o histórico, alerta sobre inconsistências. A negociação em si (contato com
o fornecedor, definição de preço e prazo) nunca é um momento da Laura — acontece
inteiramente fora dela, entre o "antes" e o "durante".

**Depois da compra** — registra o conhecimento, transforma a experiência em histórico,
melhora a próxima decisão.

Esta é a lente para ler cada um dos casos a seguir: cada "Como a Laura auxilia" cabe em um
destes três momentos, nunca fora deles.

---

## Caso 1 — Compra planejada de materiais para uma obra

**Contexto:** A obra GGV03 está entrando na fase de alvenaria. Dennis sabe que vai precisar de blocos cerâmicos, cimento e areia nas próximas semanas, mas ainda não decidiu quantidade exata nem fornecedor.

**Objetivo:** Levantar a necessidade de forma organizada antes de sair negociando, para não esquecer item nem comprar no impulso.

**Participantes:** Dennis (responsável pela compra). Laura, como consultora.

**Informações disponíveis para a Laura:** Histórico de itens já comprados para GGV03 e para obras semelhantes (GGV01, GGV02); último preço pago de blocos cerâmicos, cimento e areia; fornecedores que já venderam esses itens antes.

**Princípios aplicados:** 1 (a compra nasce da necessidade, não do orçamento), 2 (Lista de Compras é decisão técnica, distinta do orçamento), 3 (Laura ajuda a construir a lista).

**Como a Laura auxilia:** Dennis diz "preciso montar lista de alvenaria pra GGV03". A Laura responde com os itens que a obra normalmente usa nessa fase (com base no histórico de obras anteriores), quantidade aproximada baseada em compras passadas, e o último preço pago de cada um. Dennis ajusta a lista — adiciona um item que a Laura não sugeriu, remove um que já tem em estoque, muda uma quantidade.

**Decisões que permanecem humanas:** Quais itens realmente entram na lista, em que quantidade, e para quais fornecedores a lista vai ser levada pra negociação.

**Conhecimento incorporado ao histórico:** Quando a compra se completa (Caso relacionado: fluxo termina no Pedido de Compra), os itens, quantidades e preços negociados passam a fazer parte do histórico de GGV03 — disponíveis pra próxima lista dessa obra ou de outra semelhante.

---

## Caso 2 — Primeira compra de um insumo sem histórico

**Contexto:** A obra GGV03 vai precisar de uma manta asfáltica para impermeabilização — item que a empresa nunca comprou antes, em nenhuma obra.

**Objetivo:** Montar a lista mesmo sem ter nenhuma referência de preço ou fornecedor para esse item específico.

**Participantes:** Dennis. Laura, como consultora.

**Informações disponíveis para a Laura:** Nenhuma compra anterior do item. Possivelmente um preço de referência SINAPI, se o insumo constar na base.

**Princípios aplicados:** 5 (nenhuma compra sem referência — mas a ausência de referência também é informação), 8 (toda informação declara sua origem e confiança).

**Como a Laura auxilia:** Ao adicionar "manta asfáltica" na lista, a Laura diz claramente: *"Primeira compra registrada deste item — sem histórico de preço."* Se existir preço SINAPI para o insumo, ela apresenta como referência de mercado, deixando explícito que não é preço pago pela empresa, é estimativa de tabela oficial. Se não existir nem isso, ela diz que não há nenhuma referência disponível.

**Decisões que permanecem humanas:** Avaliar se o preço que vier no orçamento faz sentido, sem nenhuma referência interna para comparar — Dennis precisa usar outro critério (conhecimento de mercado, opinião do fornecedor preferencial, pesquisa própria).

**Conhecimento incorporado ao histórico:** Esta compra vira a primeira referência da empresa para manta asfáltica. A próxima vez que alguém precisar desse item, não vai mais ser "sem histórico" — vai cair no Caso 3.

---

## Caso 3 — Compra utilizando histórico de compras anteriores

**Contexto:** GGV03 precisa de mais cimento CP-II. A empresa já comprou esse item várias vezes, em obras diferentes, de fornecedores diferentes.

**Objetivo:** Aproveitar o que já se sabe sobre esse item para montar uma lista bem informada, sem repetir trabalho de descoberta.

**Participantes:** Dennis. Laura, como consultora.

**Informações disponíveis para a Laura:** Múltiplas compras anteriores de cimento CP-II — preços, fornecedores, quantidades típicas por obra, variação de preço ao longo do tempo.

**Princípios aplicados:** 3 (Laura sugere com base no histórico), 5 (referência confirmada — o item mais forte de dado que existe no domínio), 9 (o conhecimento acumulado melhora a próxima compra).

**Como a Laura auxilia:** A Laura não apresenta só "o último preço pago" isoladamente — ela mostra a tendência: "Últimas 3 compras de cimento CP-II: R$ 32, R$ 34, R$ 33 o saco, com a Frísia e a Roma Pré-Moldados." Isso dá a Dennis uma noção de faixa de preço razoável, não só um número solto que pode ter sido uma exceção.

**Decisões que permanecem humanas:** Decidir se repete fornecedor ou busca outro, e quanto comprar desta vez (a quantidade típica é sugestão, não regra).

**Conhecimento incorporado ao histórico:** Mais um ponto de dado se soma à série histórica do item — a tendência de preço fica mais confiável a cada compra repetida.

---

## Caso 4 — Compra com fornecedor preferencial

**Contexto:** GGV03 precisa de ferragens diversas. A Carlessi é fornecedora preferencial da empresa para esse tipo de material há tempos — atendimento bom, entrega confiável, poucos problemas.

**Objetivo:** Comprar de quem já é de confiança, sem abrir mão de saber se o preço continua fazendo sentido.

**Participantes:** Dennis, negociando com a Carlessi (e possivelmente mais um fornecedor, para efeito de comparação).

**Informações disponíveis para a Laura:** Histórico de compras com a Carlessi (preço, prazo, qualidade percebida ao longo do tempo); marcação de fornecedor preferencial no cadastro.

**Princípios aplicados:** 6 (fornecedor preferencial existe, mas não decide sozinho), 5 (comparação continua acontecendo mesmo com fornecedor de confiança).

**Como a Laura auxilia:** Ao ver o orçamento da Carlessi chegando, a Laura sinaliza que é fornecedor preferencial e mostra como o preço desta cotação se compara ao histórico dela mesma e, se houver, a outras cotações da mesma lista. Não recomenda "compre porque é preferencial" — apresenta o dado e deixa a leitura para Dennis.

**Decisões que permanecem humanas:** Fechar com a Carlessi mesmo que o preço esteja um pouco acima de uma alternativa — o valor do relacionamento (confiabilidade, histórico, menos problema) é uma ponderação humana, não calculável pela Laura.

**Conhecimento incorporado ao histórico:** A compra reforça o histórico da Carlessi como fornecedor confiável — mais um ponto de dado positivo, que só existe porque a compra aconteceu e foi registrada.

---

## Caso 5 — Compra onde o fornecedor preferencial perde para outro fornecedor

**Contexto:** GGV03 precisa de um lote grande de blocos cerâmicos. A Carlessi cotou, mas o preço veio bem acima do histórico dela mesma, e o prazo de entrega não bate com o cronograma da obra.

**Objetivo:** Decidir com base no que realmente importa para esta compra específica, mesmo quando isso significa não comprar do fornecedor de confiança.

**Participantes:** Dennis, negociando com a Carlessi e com outro fornecedor.

**Informações disponíveis para a Laura:** Histórico da Carlessi (mostrando que este preço está fora do padrão dela mesma); orçamento do fornecedor concorrente, se também for inserido na Laura.

**Princípios aplicados:** 6 (confiança não elimina comparação — este é o caso em que isso se prova na prática), 5 (parâmetro de comparação é o que orienta a decisão, não a preferência por si).

**Como a Laura auxilia:** A Laura sinaliza a variação: "Este orçamento da Carlessi está 22% acima da última compra do mesmo item com ela." Esse alerta é o tipo de informação que ajuda Dennis a perceber que vale negociar de novo ou considerar outra opção — sem a Laura sugerir qual decisão tomar.

**Decisões que permanecem humanas:** Escolher o outro fornecedor desta vez. Decidir se isso muda alguma coisa na relação com a Carlessi (voltar a comprar dela na próxima, questionar o motivo do preço, nada muda).

**Conhecimento incorporado ao histórico:** O histórico registra que, desta vez, outro fornecedor venceu — dado real que ajuda a próxima comparação envolvendo blocos cerâmicos ou a própria Carlessi, sem apagar o histórico positivo anterior dela.

---

## Caso 6 — Compra emergencial durante a execução da obra

**Contexto:** Durante a concretagem em GGV03, uma mangueira de bomba estoura e precisa ser substituída na hora, sob risco de perder a concretagem do dia.

**Objetivo:** Resolver o problema imediato, sem que isso vire uma falha de processo — é uma exceção prevista, não um desvio de disciplina.

**Participantes:** Dennis (ou o encarregado da obra), comprando direto na loja mais próxima.

**Informações disponíveis para a Laura:** Nenhuma, até o momento em que o comprovante/nota chega — a compra acontece inteiramente fora da Laura, na hora.

**Princípios aplicados:** 7 (compra planejada é a preferência, balcão é exceção — mas exceção prevista, não falha), 1 (esta compra especificamente não passa pelo ciclo de lista, e isso é esperado).

**Como a Laura auxilia:** Depois do fato, quando a nota/comprovante chega, a Laura processa normalmente (mesmo fluxo de hoje: recebe documento, extrai dados, gera Pedido de Compra) — sem exigir que uma Lista de Compras tenha existido antes. Ela pode, se fizer sentido, mostrar o preço pago comparado ao histórico do item (se existir), só como informação — não como cobrança.

**Decisões que permanecem humanas:** A decisão de comprar sem negociar prévia é do responsável na obra, no calor do momento — a Laura nunca vai bloquear ou exigir justificativa formal para isso.

**Conhecimento incorporado ao histórico:** A compra emergencial também vira dado — inclusive é um dado valioso: se um item aparece repetidamente como compra emergencial, isso é sinal de que talvez devesse entrar no planejamento padrão (estoque mínimo, por exemplo) — um padrão que só se percebe olhando o histórico ao longo do tempo.

---

## Caso 7 — Compra obrigatória (Copel, CREA, cartório, prefeitura)

**Contexto:** Chegou a fatura de energia da Copel referente à obra GGV03.

**Objetivo:** Registrar o pagamento e o documento de fechamento, sem tentar encaixar num processo de negociação que não existe para este tipo de despesa.

**Participantes:** Dennis, pagando a fatura. Não há negociação — o valor é o que a concessionária cobra.

**Informações disponíveis para a Laura:** Nenhum histórico de "comparação" é relevante aqui — o que existe é o histórico de faturas anteriores da mesma concessionária/obra, útil só para acompanhamento de gasto, não para decisão de compra.

**Princípios aplicados:** 10 (compras obrigatórias são domínio próprio, não uma exceção) — nenhum outro princípio do ciclo de Lista de Compras se aplica.

**Como a Laura auxilia:** A fatura entra como sempre entrou — a Laura reconhece a categoria (taxa/imposto/serviço), dispensa exigência de NF-e (a fatura já é o documento de fechamento) e arquiva. Não há lista, não há comparação de fornecedor, não há "melhor preço" a buscar.

**Decisões que permanecem humanas:** Nenhuma decisão de compra propriamente dita — só a confirmação de que o pagamento foi feito.

**Conhecimento incorporado ao histórico:** O gasto entra no histórico financeiro da obra (para acompanhamento de custo total), mas não alimenta nenhuma lógica de comparação de compra — esse tipo de despesa nunca vai gerar uma sugestão de "último preço pago" para a próxima lista.

---

## Caso 8 — Compra de um serviço

**Contexto:** GGV03 precisa contratar a gestão do empreendimento — um serviço de mão de obra especializada, pago em parcelas ao longo de vários meses, não uma entrega única de material.

**Objetivo:** Tratar a contratação de serviço com a mesma disciplina de comparação e planejamento que se aplica a material, reconhecendo que a "unidade de compra" aqui é diferente (meses de serviço, não metros ou sacos).

**Participantes:** Dennis, negociando com o prestador (ex: Verschoor Construções Civis / DeltaD Engenharia, atuando como prestador técnico).

**Informações disponíveis para a Laura:** Histórico de serviços semelhantes contratados em outras obras, se existir; valor mensal ou total praticado anteriormente para gestão de empreendimento.

**Princípios aplicados:** 1 e 3 (a necessidade de gestão também nasce de uma lista — mesmo que a "lista" tenha um item só, de valor alto), 5 (referência de preço para serviço é mais difícil de comparar item a item, mas ainda vale buscar).

**Como a Laura auxilia:** Ao montar a "lista" para este tipo de necessidade, a Laura reconhece que o item é um serviço (não um material com quantidade/unidade convencional) e ajusta a referência que apresenta — em vez de "preço por saco", mostra valor total ou mensal de contratações semelhantes anteriores, se houver.

**Decisões que permanecem humanas:** A avaliação de qualidade do prestador (algo que preço nenhum captura sozinho) e a negociação das condições de pagamento parcelado.

**Conhecimento incorporado ao histórico:** O valor e as condições negociadas passam a ser referência para a próxima contratação de serviço semelhante — e, ao longo do tempo, o histórico de parcelas pagas também vira um retrato da confiabilidade do prestador (paga em dia, entrega o que promete).

---

## Caso 9 — Compra de equipamento

**Contexto:** A obra precisa de uma betoneira própria, em vez de continuar alugando — uma compra de maior valor, pouco frequente, bem diferente de comprar material de consumo.

**Objetivo:** Tratar uma compra de investimento com mais cautela do que uma compra rotineira, reconhecendo que o "último preço pago" quase certamente não existe.

**Participantes:** Dennis, pesquisando e negociando com fornecedores de equipamento.

**Informações disponíveis para a Laura:** Provavelmente nenhum histórico de compra de betoneira — é o tipo de item que a empresa compra raramente. Pode haver preço de referência de mercado (fora do SINAPI, que é focado em insumo de obra, não em equipamento).

**Princípios aplicados:** 5 (ausência de referência declarada explicitamente, igual ao Caso 2), 7 (compra planejada — equipamento é o tipo de compra que menos faz sentido decidir no balcão).

**Como a Laura auxilia:** Sinaliza claramente que não há histórico da empresa para esse tipo de item, e que a decisão vai depender mais de pesquisa externa (marca, durabilidade, garantia) do que de comparação de preço histórico. A Laura ainda ajuda a organizar a lista e guardar o que for decidido, mesmo sem poder oferecer uma referência forte.

**Decisões que permanecem humanas:** Praticamente toda a avaliação — comparação de marca, durabilidade, garantia, custo-benefício — foge do que a Laura consegue oferecer com os dados que tem hoje.

**Conhecimento incorporado ao histórico:** Esta compra vira a primeira referência de equipamento da empresa. Se um dia a empresa comprar outra betoneira, não será mais "sem histórico" — mas a cadência é tão baixa que esse aprendizado amadurece muito mais devagar do que o de um item de consumo diário.

---

## Caso 10 — Compra recorrente de um item já conhecido

**Contexto:** GGV03 compra cimento a cada duas ou três semanas, sempre em quantidade parecida, quase sempre dos mesmos dois fornecedores.

**Objetivo:** Tornar a compra repetida cada vez mais rápida de planejar, sem perder a disciplina de comparação.

**Participantes:** Dennis, repetindo um padrão já estabelecido.

**Informações disponíveis para a Laura:** Série longa de compras do mesmo item — preço, fornecedor, cadência, quantidade — o caso com mais dado disponível de todos.

**Princípios aplicados:** 9 (o conhecimento acumulado é o que torna esta compra mais fácil que a primeira), 3 (a sugestão da Laura fica cada vez mais precisa quanto mais vezes o item aparece).

**Como a Laura auxilia:** A Laura pode notar o padrão de recorrência e sugerir proativamente: "Já se passaram 3 semanas desde a última compra de cimento para GGV03 — quantidade típica: 100 sacos." Isso não é uma decisão automática, é uma lembrança — o tipo de coisa que a Constituição do projeto já promete ("Laura não espera ser perguntada, ela mostra o que precisa de atenção").

**Decisões que permanecem humanas:** Confirmar se realmente é hora de comprar de novo, ajustar a quantidade conforme o ritmo real da obra, escolher entre os fornecedores recorrentes ou testar um novo.

**Conhecimento incorporado ao histórico:** Cada repetição reforça o padrão — a cadência, a quantidade típica e a faixa de preço ficam cada vez mais confiáveis como referência, exatamente o que o Princípio 9 da Política de Compras descreve.

---

## Caso 11 — Laura percebe que faz tempo desde a última compra de um insumo recorrente

**Contexto:** GGV03 compra cimento regularmente, a cada 2-3 semanas. Já se passou mais tempo que o normal desde a última compra, e a obra continua em fase que consome cimento.

**Objetivo:** Antecipar uma necessidade antes que ela vire urgência, sem esperar Dennis lembrar sozinho.

**Participantes:** Laura, tomando a iniciativa. Dennis, recebendo o aviso.

**Informações disponíveis para a Laura:** Histórico de compras de cimento para GGV03 — datas, quantidades, cadência média observada nas últimas compras.

**Princípios aplicados:** 3 (Laura ajuda a lembrar), 9 (o conhecimento acumulado torna a próxima decisão mais fácil) — aqui aplicados de forma proativa, não sob pergunta.

**Como a Laura auxilia:** Sem que Dennis pergunte nada, a Laura avisa: *"Já se passaram 4 semanas desde a última compra de cimento para GGV03 — a cadência normal é de 2 a 3 semanas. Vale montar uma lista nova?"* Não é cobrança, é lembrança — o mesmo espírito de "Laura não espera ser perguntada."

**Decisões que permanecem humanas:** Confirmar se realmente é hora de comprar de novo (a obra pode ter desacelerado por outro motivo) e, se sim, seguir pro fluxo normal de montar a lista.

**Conhecimento incorporado ao histórico:** Se Dennis confirma que era hora, a cadência se reforça como padrão confiável. Se ele diz que ainda não precisa, isso também é dado — mostra que a cadência variou por um motivo real (obra parada, item usado com menos frequência que o normal).

---

## Caso 12 — Laura percebe uma Lista de Compras parada há muitos dias

**Contexto:** Dennis começou uma Lista de Compras para GGV03 há duas semanas, adicionou alguns itens, e não voltou a mexer nela desde então.

**Objetivo:** Evitar que uma necessidade identificada se perca no meio do caminho, sem cobrar Dennis por isso.

**Participantes:** Laura, tomando a iniciativa. Dennis, decidindo o que fazer com a lista parada.

**Informações disponíveis para a Laura:** Data de criação e de última atualização da lista; itens já incluídos nela.

**Princípios aplicados:** 3 (ajudar a organizar não é só montar, é também não deixar esquecer), 1 (a necessidade só vira compra se o processo seguir até o fim).

**Como a Laura auxilia:** A Laura avisa: *"A lista que você começou para GGV03 (blocos, cimento) está parada há 12 dias, sem orçamento vinculado ainda. Quer retomar, ou a necessidade mudou?"* Não insiste depois de avisar uma vez sem necessidade — o alerta é discreto, coerente com "Laura não aparece quando não tem nada útil a dizer."

**Decisões que permanecem humanas:** Retomar a lista, ajustá-la, ou simplesmente descartá-la porque a necessidade não existe mais.

**Conhecimento incorporado ao histórico:** Se a lista é descartada, isso também é aprendizado — talvez sinalize que a necessidade original foi resolvida de outra forma (compra emergencial, por exemplo), o que ajuda a entender melhor o padrão de consumo da obra.

---

## Caso 13 — Laura percebe um desvio do padrão esperado

**Contexto:** Um orçamento chega para GGV03 com o preço do saco de cimento 40% acima da média das últimas compras, ou com uma quantidade muito maior que o normal para esse tipo de item.

**Objetivo:** Chamar atenção para algo fora do padrão antes que a decisão seja tomada, sem impedir que ela aconteça.

**Participantes:** Dennis, revisando o orçamento recebido. Laura, sinalizando o desvio.

**Informações disponíveis para a Laura:** Histórico de preço e quantidade do mesmo item, em compras anteriores da mesma obra ou de obras semelhantes.

**Princípios aplicados:** 5 (referência existe justamente para isso), 8 (a Laura declara a origem e o grau de confiança do alerta, não decide sozinha).

**Como a Laura auxilia:** Ao processar o orçamento recebido, a Laura destaca: *"Este preço está 40% acima da média das últimas 4 compras de cimento para GGV03."* Ou, no caso de quantidade: *"Você normalmente compra 100 sacos por vez — este orçamento é de 300."* O alerta aparece antes da confirmação do Pedido de Compra, no momento em que ainda pode ter efeito.

**Decisões que permanecem humanas:** Avaliar se o desvio tem uma explicação legítima (reajuste de mercado, compra maior porque vai durar mais tempo, condição comercial diferente) ou se é sinal de erro — a Laura não sabe qual dos dois é, só que é diferente do padrão.

**Conhecimento incorporado ao histórico:** Se a compra segue, o novo preço/quantidade passa a fazer parte do histórico — e, se realmente representa mudança de mercado, os próximos alertas já nascem calibrados com esse novo patamar.

---

## Caso 14 — Laura percebe possível duplicidade de compra

**Contexto:** Dennis está montando uma lista ou recebendo um orçamento para GGV03, e o item em questão já foi comprado há poucos dias, em quantidade que provavelmente ainda não foi consumida.

**Objetivo:** Evitar uma compra redundante antes que ela se concretize.

**Participantes:** Dennis. Laura, sinalizando a coincidência.

**Informações disponíveis para a Laura:** Data e quantidade da compra mais recente do mesmo item, para a mesma obra.

**Princípios aplicados:** 5 (referência de compra recente é o parâmetro de comparação), 12 (apontar inconsistência é parte do papel de consultora).

**Como a Laura auxilia:** A Laura avisa: *"Você já comprou 50 sacos de cimento para GGV03 há 4 dias — quer mesmo adicionar mais 50 agora, ou é continuação da mesma necessidade?"* Isso ajuda a pegar tanto erro genuíno (pedido duplicado sem querer) quanto casos legítimos (a obra realmente consome rápido) — o alerta serve pros dois; a diferença é decidida por Dennis.

**Decisões que permanecem humanas:** Confirmar se é mesmo uma compra nova e necessária, ou se é engano ou repetição.

**Conhecimento incorporado ao histórico:** Se confirmado como legítimo, o consumo real da obra fica mais claro (consome mais rápido do que a cadência "padrão" sugeria) — o que recalibra o Caso 11 na próxima vez.

---

## Caso 15 — Laura percebe uma tendência de queda num fornecedor preferencial

**Contexto:** Nas últimas três cotações da Carlessi (fornecedora preferencial), o preço veio sistematicamente acima do que outros fornecedores ofereceram para os mesmos itens, ou o prazo de entrega tem atrasado.

**Objetivo:** Trazer à atenção um padrão que só aparece olhando várias compras juntas — não visível numa única transação isolada.

**Participantes:** Dennis, avaliando a relação com o fornecedor. Laura, apresentando a tendência.

**Informações disponíveis para a Laura:** Série de orçamentos/compras da Carlessi ao longo do tempo, comparados entre si e, quando existir, contra outros fornecedores do mesmo item.

**Princípios aplicados:** 6 (confiança não elimina comparação — inclusive comparação ao longo do tempo, não só pontual), 8 (a Laura apresenta a tendência com a origem clara dos dados, sem recomendar ação).

**Como a Laura auxilia:** Depois de perceber o padrão repetido (não numa única compra, como no Caso 5, mas ao longo de várias), a Laura sinaliza: *"As últimas 3 cotações da Carlessi vieram acima da média de mercado para os mesmos itens — pode valer conversar sobre isso, ou considerar comparar mais nas próximas compras."* A Laura nunca sugere trocar de fornecedor — só mostra o padrão.

**Decisões que permanecem humanas:** Toda a avaliação da relação — conversar com o fornecedor sobre o motivo, aceitar por causa do relacionamento, ou de fato buscar mais comparação daqui pra frente. A classificação de "preferencial" continua sendo decisão humana, mesmo diante da tendência.

**Conhecimento incorporado ao histórico:** A tendência observada e a decisão tomada (manteve, questionou, reavaliou) também viram parte do histórico do fornecedor — insumo pra próxima vez que a mesma pergunta aparecer.

---

## Nota — Uma Lista de Compras Pode Gerar Mais de Um Pedido de Compra

Nenhum dos casos acima detalha isso, mas vale registrar como fato do domínio: uma única
Lista de Compras não implica necessariamente um único Pedido de Compra. Itens diferentes
da mesma necessidade podem vir de fornecedores diferentes — cimento de um fornecedor,
blocos de outro, ambos nascidos da mesma lista para a fase de alvenaria de GGV03. A Lista
de Compras organiza a necessidade; não obriga que ela feche com um fornecedor só.

---

## Padrões Comuns

Depois de percorrer os dez casos, alguns padrões se repetem — independente de material, serviço ou equipamento. Eles não são decisão de arquitetura, mas é provável que cada um vire, mais adiante, um serviço, uma regra de negócio ou um componente do sistema.

**1. A espinha dorsal é sempre a mesma; só a granularidade muda.**
Necessidade → Lista → negociação → orçamento → Pedido de Compra → histórico aparece em todos os dez casos, mesmo nos que pulam etapas (Casos 6 e 7). O que varia é a unidade de medida da necessidade — sacos de cimento, meses de serviço, uma unidade de equipamento — não o fluxo em si.

**2. Toda referência de preço tem um de três estados, e isso precisa ficar sempre visível.**
Confirmada (Casos 3, 10), aproximada (Caso 2, quando há SINAPI) ou ausente (Casos 2 e 9). Nenhuma compra deveria acontecer sem a Laura deixar claro qual dos três estados se aplica — esse é o mecanismo que sustenta o Princípio 8 na prática, em qualquer caso.

**3. Fornecedor preferencial é o mesmo mecanismo, com dois resultados possíveis.**
Os Casos 4 e 5 são o mesmo processo (comparar mesmo com confiança estabelecida) chegando a decisões opostas. Isso sugere que "comparar contra o histórico do próprio fornecedor preferencial" é tão importante quanto comparar contra outros fornecedores.

**4. Existem duas portas de saída do ciclo padrão, e são conceitualmente diferentes.**
Emergência (Caso 6) e obrigação (Caso 7) não têm Lista de Compras — mas por motivos opostos. A emergência é uma falha de planejamento aceitável, dentro do domínio planejável (podia ter tido lista, não teve). A obrigação nunca teve lista como opção — é outro domínio inteiramente. Tratar as duas como "a mesma exceção" seria um erro; são categorias diferentes que só parecem iguais de fora.

**5. O aprendizado amadurece em velocidades diferentes.**
Item recorrente (Caso 10) aprende rápido — cadência semanal, muitos pontos de dado. Equipamento (Caso 9) aprende devagar — pode levar anos até a segunda compra. Serviço (Caso 8) aprende sobre uma coisa diferente de preço — aprende sobre confiabilidade do prestador ao longo das parcelas. Um sistema de sugestão único, que trate todo item da mesma forma, provavelmente vai servir mal pelo menos um desses três ritmos.

**6. A unidade de comparação não é sempre "preço por item".**
Material compara preço por unidade (Casos 1, 3, 4, 5, 10). Serviço compara valor total ou mensal, e pondera prazo/qualidade tanto quanto preço (Caso 8). Equipamento quase não tem "preço de referência" no sentido tradicional — compara-se por pesquisa externa, não por histórico interno (Caso 9). Isso sugere que "comparação" não é uma função genérica única — é pelo menos três formas diferentes de comparar, dependendo da natureza do que está sendo comprado.

**7. Iniciar conversa e evitar erro são a mesma capacidade, vista de dois ângulos.**
Os Casos 11 a 15 mostram que "chamar atenção pra uma oportunidade" (tempo decorrido, lista parada, tendência de fornecedor) e "chamar atenção pra um risco" (desvio de padrão, duplicidade) usam o mesmo mecanismo de fundo: comparar contra o histórico e sinalizar quando algo foge do esperado. A diferença está só no tom da mensagem e no gatilho — nunca no que a Laura efetivamente faz, que é sempre a mesma coisa: comparar e avisar, nunca decidir.

---

*Responsável: Dennis Verschoor + Claude*
*Baseado em: `docs/POLITICA_COMPRAS.md`*
*Última revisão: 2026-07-03*
