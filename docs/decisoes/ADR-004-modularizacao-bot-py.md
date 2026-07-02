# ADR-004 — Modularização parcial de `bot.py`: dispatch table + extração de `nfe/`

**Status:** Aceita
**Data:** 2026-07-02
**Responsáveis:** Dennis Verschoor (decisão) · Claude Sonnet 5 (análise técnica, com dois agentes independentes — um propondo, outro tentando derrubar)
**Relacionada a:** ADR-001 (gatilho de linhas ultrapassado), ADR-002 (padrão `db_path`, precedente de `financeiro/`), ADR-003 (gatilho de revisão de `bot.py` > 3.500 linhas — disparado)

---

## Contexto

A ADR-003 (2026-06-30) documentou um gatilho explícito: revisitar a extração de módulos de `bot.py` quando o arquivo ultrapassar **~3.500 linhas**. `bot.py` está hoje em **3.994 linhas** — o gatilho disparou. Uma auditoria de código independente (2026-07-02, focada em achar código substituível por bibliotecas prontas) encontrou de bônus que `responder_botao()`, o handler central de todo `callback_query` do Telegram, tem **929 linhas e 54 ramos `elif acao ==`** de primeiro nível, roteando todos os domínios do sistema (Pedido/PFM, Comprovante PIX, NF-e, Recibo, Entrega, Obra, Fornecedor) numa função só, dentro de um único `try/except Exception` genérico.

Como na ADR-003, dois agentes analisaram o problema de forma independente antes da decisão: um propôs um plano amplo de extração por domínio; outro leu o código real linha por linha tentando derrubar cada alegação do primeiro. O padrão se repetiu: **a análise de risco encontrou furos reais que a proposta inicial não via**, e a decisão final é mais conservadora que a proposta original — exatamente como aconteceu com `entrega/` na ADR-003.

---

## O que foi proposto e o que a revisão adversarial derrubou

### Proposta inicial (Agente 1)

Duas frentes: (1) dividir `responder_botao()` em ~8 funções por domínio, registradas como múltiplos `CallbackQueryHandler(fn, pattern=...)` do python-telegram-bot; (2) extrair, nesta ordem, `fornecedor/`, `nfe/`, `obra/`, `comprovante/` — deixando `entrega/`, `recibo/` e o núcleo `pedido/pfm` fora de escopo. Estimativa: `bot.py` cairia de 3.994 para ~3.100 linhas.

### O que a revisão adversarial (Agente 2) encontrou, verificando o código real

1. **A divisão do dispatcher não é "puro corte-e-cola".** Existe um guard clause (`bot.py:3051`, bloqueio de obra não identificada) que só funciona porque roda **antes** do único `query.answer()` genérico da função (`bot.py:3060`) — o Telegram só aceita uma chamada de `answerCallbackQuery` por callback. Registrar múltiplos `CallbackQueryHandler` do PTB, cada um chamando `answer()` independentemente, arrisca perder essa ordem sem nenhum erro visível — o alerta simplesmente para de aparecer.
2. **`sel_tipo_inicial` (92 linhas) atravessa 4 domínios internamente** (entrega, pix, nfe, pfm) dentro de um único ramo — não cabe em nenhum dos 8 "buckets por domínio" propostos, e o plano original não o mencionava.
3. **`fornecedor/` teria uma correção "de brinde" perigosa.** `_gerar_recibo()` faz duas escritas (`parcelas_pagamento` e `fornecedores`) na mesma transação SQLite. Movê-las para módulos separados com conexões próprias quebraria essa atomicidade — um crash entre as duas passaria a deixar dado inconsistente, um bug que só apareceria dias depois. Há também duas constantes quase idênticas (`DELTAD_CNPJ_DIGITS` vs `CNPJS_PROPRIOS_DIGITS`) com uso intencionalmente diferente entre as funções candidatas à extração — risco real de troca silenciosa.
4. **`obra/` reproduziria, dentro de si mesma, o motivo pelo qual `recibo/` foi descartada.** `pedido_excluir_*` (que ficaria na tela de obra) chama `_excluir_pedido()`, que toca 4 tabelas — o mesmo critério ("toca 4 domínios") usado para rejeitar `recibo/` no mesmo plano.
5. **`comprovante/` é estruturalmente idêntica ao problema que a ADR-003 já resolveu para `entrega/`.** `buscar_candidatos_pix()` depende de `_total_pago()`, que usa a constante global `DB_PATH` em vez de receber `db_path` como parâmetro — violando a convenção da ADR-002. Corrigir isso exige decidir quem é dono da tabela `parcelas_pagamento` (nunca discutido em nenhuma ADR anterior), sob risco de criar importação circular entre `financeiro/` e `bot.py`, ou duplicar a fórmula de saldo em dois lugares.

---

## Decisão

**Escopo desta rodada, reduzido em relação à proposta inicial:**

1. **Dispatch table interna** dentro de `responder_botao()` — trocar o `if/elif` de 929 linhas por um `dict[acao] -> função`, mantendo **um único** `CallbackQueryHandler`, o mesmo `try/except` e a mesma ordem de execução de hoje (guard clause incluído). Zero risco de multi-handler do PTB; ganho de legibilidade sem mudar comportamento.
2. **Extrair `nfe/`** (`_parse_nfe`, `_mostrar_nfe`, `_teclado_candidatos_nfe`) — confirmado como o único candidato genuinamente comparável ao padrão validado de `financeiro/` (ADR-002): funções puras, sem acesso a banco, já chamando `financeiro.lancamento.vincular_nfe`/`buscar_candidatos_nfe` existentes, sem import circular.

**Adiados nesta rodada, com motivo registrado (não por omissão):**

- **`fornecedor/`** — adiar até decidir separadamente como preservar a atomicidade da transação em `_gerar_recibo()` (ex.: passar a conexão explícita em vez de abrir uma nova dentro do módulo extraído) e confirmar por escrito qual constante (`DELTAD_CNPJ_DIGITS` vs `CNPJS_PROPRIOS_DIGITS`) cada função usa.
- **`obra/`** — adiar até que a extração de `pedido/pfm` (fora de escopo total, ver abaixo) resolva o destino de `_excluir_pedido()`; extrair `obra/` antes disso reproduziria o acoplamento de 4 tabelas que already reprovou `recibo/`.
- **`comprovante/`** — adiar até existir uma decisão explícita (mesmo formato desta ADR) sobre quem é dono de `parcelas_pagamento`/`_total_pago`, e até essa função aceitar `db_path` como parâmetro.
- **`entrega/`** — mantém a decisão da ADR-003. O gatilho numérico disparou, mas os motivos substantivos (schema em `lancamentos`, sem FK, zero horas de uso real em produção dos casos da Fase 6) não mudaram. O plano de 7 fiadas da ADR-003 continua válido e pronto.
- **`recibo/`** — não extrair. Mais acoplada que `entrega/`: `_gerar_recibo()` toca 4 domínios numa função de 46 linhas. Revisitar **junto** com `entrega/` (compartilham `parcelas_pagamento`/`documentos`/`fornecedores`), nunca isoladamente.
- **`pedido/pfm`** (núcleo maior, ~1.200+ linhas) — fora de escopo, como já estabelecido na ADR-002. Revisitar quando `itens_pedido` ganhar funções de consulta e estabilizar.

---

## Plano de execução

### Fiada 0 — Dispatch table (sem mudança de comportamento)

- Dentro de `responder_botao()`, manter o guard clause de `ok`/`nao_identificado` exatamente onde está, antes do `query.answer()` genérico.
- Substituir a cadeia `if/elif` por um dispatch table (`dict[str, callable]`) chamado dentro do mesmo `try/except` único de hoje.
- `sel_tipo_inicial` permanece como está nesta fiada — seu tratamento (divisão dos 4 domínios internos) fica registrado como ponto de acoplamento, não resolvido agora.

**Critério de aceite:** clicar em pelo menos um botão de cada um dos 54 ramos originais no Telegram, confirmando resposta idêntica à de antes. `python bot.py` sobe sem erro.

**Linhas de `bot.py` ao final:** ~3.994 (reorganização interna; ganho é de legibilidade e manutenção do tratamento de erro por ramo, não de contagem).

### Fiada 1 — Extrair `nfe/`

- Criar `nfe/__init__.py` + `nfe/nfe.py` com `_parse_nfe`, `_mostrar_nfe`, `_teclado_candidatos_nfe`, chamando `financeiro.lancamento.vincular_nfe`/`buscar_candidatos_nfe` (já existentes, já usados assim hoje).
- Ajustar `sel_tipo_inicial` e os ramos `nfe_confirmar`/`nfe_cancelar` para importar de `nfe/`.

**Critério de aceite:** enviar uma NF-e, vincular a um pedido pago sem NF-e, cancelar a vinculação — três fluxos, sem diferença perceptível.

**Linhas de `bot.py` ao final:** ~3.915.

---

## Pontos de acoplamento mapeados (documentados, não resolvidos nesta ADR)

Os pontos já registrados na ADR-003 sobre `entrega/` continuam válidos. Adiciono os encontrados nesta análise:

11. `buscar_candidatos_pix()` faz SQL inline direto contra `lancamentos`/`fornecedores` em vez de reusar função de domínio, diferente de `buscar_candidatos_nfe()`, que já faz certo.
12. `_gerar_recibo()` toca 4 domínios numa função de 46 linhas — hoje o ponto de maior acoplamento cruzado do sistema, mais entrelaçado que `entrega/`.
13. `parcelas_pagamento` nunca teve seu "dono de schema" decidido em nenhuma ADR — é uma lacuna preexistente, não introduzida por esta decisão.
14. `itens_pedido` já recebe escrita a cada `gerar_pfm()` mas não tem nenhuma função de leitura — schema "aberto", não deve ser tratado como estável por extrações futuras.
15. `sel_tipo_inicial` mistura a triagem de 4 domínios num único bloco de entrada — nenhuma extração de domínio individual resolve isso sozinha; provavelmente continua em `bot.py` como "porta de entrada" mesmo após futuras extrações.
16. 12 ações de `callback_data` sem prefixo de domínio (`ok`, `cancelar`, `sel_tipo`, `set_tipo`, `sel_ggv`, `set_ggv`, `pgto`, `end`, `sel_edit`, `edit_campo`, `voltar_edit`, `ver_itens`) — limpeza de nomenclatura cosmética, fora de escopo.
17. `_listar_obras()` faz SQL inline contra `obras` fora do trio `buscar_obra/atualizar_obra/criar_obra` — órfã, relevante quando `obra/` for revisitada.

---

## Gatilho de revisão desta decisão

Revisitar `fornecedor/`, `obra/` e `comprovante/` quando:

- Existir uma decisão explícita sobre o dono de `parcelas_pagamento` (desbloqueia `comprovante/`)
- `_total_pago()` for migrada para aceitar `db_path` como parâmetro (desbloqueia `comprovante/`)
- A atomicidade de `_gerar_recibo()` for resolvida (conexão explícita compartilhada, ou aceitação consciente do risco) (desbloqueia `fornecedor/`)
- O destino de `_excluir_pedido()`/núcleo `pedido/pfm` for decidido (desbloqueia `obra/`)

Revisitar `entrega/`/`recibo/` conforme o gatilho já escrito na ADR-003 (casos da Fase 6 tocarem o modelo em produção).

---

## O que esta ADR não decide

- Extração de `fornecedor/`, `obra/`, `comprovante/`, `entrega/`, `recibo/` — todas adiadas com motivo registrado acima.
- Propriedade de schema de `parcelas_pagamento`.
- Renomeação de `callback_data` sem prefixo (ponto 16).
- Adoção de suíte de testes automatizados — critérios de aceite continuam manuais via Telegram, como nas ADRs anteriores.

---

## Alinhamento com a Constituição

| Princípio | Como esta decisão o honra |
|---|---|
| Aprender antes de otimizar | A proposta ampla foi reduzida depois de verificar o código real, não aceita por alegação |
| Fiadas pequenas | 2 fiadas, cada uma reversível e testável isoladamente |
| Simplicidade | Dispatch table resolve o maior problema de legibilidade sem introduzir múltiplos handlers PTB |
| Engenharia viva | Terceira vez que o processo de dois agentes (propor + derrubar) muda a decisão final — o método está validado |

---

*Aprovada por Dennis Verschoor — 2026-07-02*
*Análise técnica: Claude Sonnet 5 (dois agentes independentes)*
*Próxima revisão: quando os gatilhos acima ocorrerem*

---

## Execução (2026-07-02)

Ambas as fiadas foram executadas e testadas manualmente no bot de teste (`LAURA_ENV=test`) no mesmo dia da aprovação.

- **Fiada 0:** extração mecânica via script AST (não retranscrita à mão) — 59 grupos de ramos identificados (não 54/57 como estimado inicialmente; a contagem exata inclui um bloco `elif acao in (...)` que serve 3 ações com uma única função). Verificação automatizada confirmou que todos os 59 corpos de ramo são **byte-idênticos** ao original antes de substituir o `if/elif` pela dispatch table. Testado no Telegram: todos os grupos de botão responderam de forma idêntica.
- **Fiada 1:** `nfe/` criado (`nfe/__init__.py` + `nfe/nfe.py`, 84 linhas). `_campo`/`_campo_vazio`/`_fmt_brl` foram duplicados dentro de `nfe/nfe.py` (não importados de `bot.py`) para manter o módulo importável de forma standalone, mesma convenção de `financeiro/lancamento.py` — decisão não coberta em detalhe pelo plano original, registrada aqui. Testado: envio de NF-e, listagem de candidatos, cancelamento.
- **Achado adicional durante o teste manual:** `buscar_candidatos_nfe()` (`financeiro/lancamento.py`) não tinha corte em top-N (diferente do bug já corrigido em `buscar_candidatos_pix`), mas o desempate de candidatos com score empatado em 0 usava ordem arbitrária do banco em vez de proximidade de valor. Corrigido com o mesmo padrão de desempate já aplicado a `buscar_candidatos_pix` (ver [[project_candidatos_pix_lista_completa]]).
- **Pendência resolvida — regra de elegibilidade de NF-e mudou.** Caso real de teste: GGV03-010 está em `a_pagar` (só uma parcela de 3 paga), mas o fornecedor já emitiu a nota e a entrega já ocorreu — o filtro `status='pago'` escondia um caso legítimo. Decisão do Dennis: NF-e pode ser vinculada "a qualquer momento" — `buscar_candidatos_nfe()`, `buscar_pedidos_sem_nfe()` e `vincular_nfe()` (`financeiro/lancamento.py`) tiveram a exigência `status='pago'` removida; o único critério de elegibilidade agora é `doc_id_nfe IS NULL`. Testado: os 9 pedidos sem NF-e (de 10 totais) passaram a aparecer como candidatos, incluindo GGV03-010.

**Linhas finais:** `bot.py` em 4.068 linhas (a Fiada 0 adicionou ~74 linhas de boilerplate de função — um `async def`/linha em branco por ramo — compensando parte da redução esperada; a Fiada 1 removeu ~52 linhas). Resultado líquido menor que a estimativa original (~3.915), mas o ganho real desta rodada foi de legibilidade e isolamento de erro por domínio, não de contagem bruta de linhas — como já esperado pela própria ADR.
