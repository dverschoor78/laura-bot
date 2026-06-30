# ADR-003 — Adiar a extração do domínio Entrega de `bot.py`

**Status:** Aceita
**Data:** 2026-06-30
**Responsáveis:** Dennis Verschoor (decisão) · Claude Sonnet 5 (análise técnica)
**Relacionada a:** ADR-001 (gatilho de revisão atingido — bot.py em 3.277 linhas), ADR-002 (estabelece o padrão `db_path`; reservou esta decisão para uma futura ADR-003)

---

## Contexto

A ADR-001 definiu a faixa de revisão de `bot.py` em **2.500–3.000 linhas**. O arquivo está hoje em **3.277 linhas**, 9% acima do teto, tendo crescido 125 linhas só nesta sessão (Fiada 6c+: múltiplas fotos por entrega, com legenda obrigatória e galeria). O gatilho está formalmente disparado.

`ROADMAP.md` e `ESTADO.md` já apontavam a próxima fiada prioritária como "Refatorar bot.py — candidato: extrair domínio `entrega/`", seguindo o padrão validado pela ADR-002 para o domínio Financeiro.

Antes de executar essa extração, dois agentes analisaram o código de forma independente — um propondo a melhor forma de fazer a extração, outro tentando ativamente derrubá-la (risco de regressão, sem rede de testes automatizados). A análise de risco revelou uma diferença estrutural importante que a hipótese original (replicar o padrão de `financeiro/`) não tinha considerado.

---

## Por que entrega/ não é comparável a financeiro/

A ADR-002 funcionou porque `financeiro/` nasceu **vazio e independente** — zero refatoração de código estável, zero dependência cruzada com `bot.py`. `entrega/` é diferente:

- Os dados de estado de entrega (`obs_entrega`, `entregue_em`) vivem dentro de **`lancamentos`**, tabela cujo schema-owner conceitual, pela própria ADR-002, é o domínio **Financeiro** — não um domínio de entrega.
- A leitura de fotos (`_listar_fotos_entrega`) faz `JOIN` contra **`documentos`**, tabela do domínio **Pedido**.
- `ctx.user_data["aguardando"]` é uma máquina de estados única, compartilhada por todos os domínios da conversa — os 6 estados de entrega não têm prefixo consistente entre si.
- `teclado_pedido()` (função do domínio Pedido) já constrói `callback_data` com vocabulário de entrega diretamente.
- A funcionalidade — incluindo a extensão de hoje (múltiplas fotos) — tem **zero horas de uso real em produção**. Foi construída e testada interativamente nesta mesma sessão.
- O `ROADMAP.md` (Fase 6) já lista três casos em aberto que vão alterar o modelo de dados de entrega: múltiplas NF-e por pedido, fluxo invertido (entrega antes do PIX) e dados do prestador para recibo.

Extrair um módulo agora significa fixar um contrato sobre um modelo de dados que sabemos, hoje, que ainda vai mudar — o oposto do princípio "aprender antes de otimizar" da Constituição.

---

## Alternativas Consideradas

### A. Extrair `entrega/` agora, por completo (helpers + despacho de callback)

| Prós | Contras |
|---|---|
| Resolve o ponto de maior acoplamento do sistema para este domínio específico | Exige decidir, sob pressão, quem é dono do schema de `lancamentos` — decisão que ainda não existe |
| Aplica um padrão já validado (`financeiro/`) | A funcionalidade tem zero horas de produção real — fronteira do domínio ainda não foi exercitada |
| Bot.py volta a uma faixa mais próxima da ADR-001 | Três casos do ROADMAP (Fase 6) ainda vão alterar o modelo de dados extraído, possivelmente exigindo retrabalho do contrato do módulo em seguida |

### B. Extração ampla (entrega/ + módulo de UI/teclados + dispatcher por domínio)

| Prós | Contras |
|---|---|
| Ataca a causa raiz (`responder_botao()` como dispatcher único de ~800 linhas) | É, na prática, reabrir a "Modularização total" que a própria ADR-002 já descartou por falta de motivo real |
| Reduziria bot.py de forma mais expressiva | Combina duas decisões arquiteturais distintas numa única janela de mudança, sem testes automatizados, validado só manualmente |

### C. Adiar a extração, com gatilho de revisão preciso ← **Escolhida**

| Prós | Contras |
|---|---|
| Não fixa um contrato de módulo sobre um modelo de dados ainda instável | `bot.py` continua acima do teto da ADR-001 por mais um ciclo |
| Honra "aprender antes de otimizar": espera a Fase 6 tocar o modelo antes de desenhar a fronteira | Exige disciplina para não deixar a dívida virar "adiada para sempre" — mitigado pelo gatilho explícito abaixo |
| O plano de extração fica pronto e documentado — quando o gatilho disparar, não se começa do zero | |

---

## Decisão

**Adiamos a extração do domínio Entrega de `bot.py`.** O domínio continua dentro do monólito até o gatilho de revisão abaixo ocorrer.

Isso não é "ignorar a dívida" — é reconhecer que o formato da dívida ainda não está claro o suficiente para ser pago corretamente. A ADR-002 ensinou que modularização prematura sobre um domínio mal compreendido cria mais acoplamento do que resolve (ver "Por que entrega/ não é comparável a financeiro/" acima).

### Correções aplicadas imediatamente, independente desta decisão

- **Regra de propriedade de schema:** `init_db()` (em `bot.py`) e `init_db_financeiro()` (em `financeiro/`) continuam sendo os únicos lugares que criam ou alteram colunas em `lancamentos`. A tabela `entrega_fotos`, criada nesta sessão, já segue essa regra corretamente — é independente, sem colunas em `lancamentos`.
- **Limpeza de coluna vestigial:** `lancamentos.doc_id_entrega` parou de ser lida ou escrita nesta sessão (substituída pela tabela `entrega_fotos`, que suporta múltiplas fotos). A coluna permanece no schema por compatibilidade com bancos existentes, mas o código não referencia mais seu valor.
- **Correção de inconsistência documental:** `ESTADO.md` e `ROADMAP.md` citavam o limite da ADR-001 como "~2000 linhas"; o valor correto, conforme a própria ADR-001, é **2.500–3.000 linhas**. Corrigido nesta sessão.

---

## Gatilho de revisão desta decisão

Revisitar a extração de `entrega/` quando **um ou mais** dos seguintes ocorrer:

- A Fiada 6b ou os Casos 2/3 do `ROADMAP.md` (múltiplas NF-e por pedido; fluxo invertido entrega→PIX) tocarem o modelo de dados de entrega pelo menos uma vez em produção
- `bot.py` ultrapassar **~3.500 linhas**
- A necessidade de testes automatizados isolados para o fluxo de entrega se tornar bloqueante para alguma fiada futura
- Decorrerem pelo menos algumas semanas de uso real do fluxo de entrega em produção, sem alterações estruturais

Quando isso ocorrer, o plano abaixo está pronto para execução — não precisa ser refeito do zero.

---

## Plano de extração (pronto para quando o gatilho disparar)

Plano produzido pela análise técnica, preservado aqui como referência futura. Cada fiada move um único tipo de responsabilidade, é testável isoladamente no Telegram e reversível sem afetar as demais.

**Fiada 0 — Fundação:** criar `entrega/__init__.py` e `entrega/registro.py`; mover o `CREATE TABLE entrega_fotos` para `init_db_entrega(db_path)`, chamada a partir de `init_db()`. *Critério: bot sobe sem erro, zero comportamento novo.*

**Fiada 1 — Helpers de leitura:** mover `buscar_pedidos_sem_entrega()`, `_listar_fotos_entrega()`, `_buscar_estado_entrega()`, `_icone_arquivo_entrega()`, `_rotulo_qtd_arquivos()`, recebendo `db_path`. *Critério: telas de entrega mostram os mesmos dados de antes (comparação manual).*

**Fiada 2 — Helpers de escrita:** mover `_salvar_entrega_db()`, `_adicionar_foto_entrega()`, `_apagar_foto_entrega()`, `_atualizar_obs_entrega()`, `_apagar_entrega_db()`. *Critério: os 4 fluxos de escrita testados ponta a ponta no Telegram.*

**Fiada 3 — Texto e teclado:** mover os construtores de tela. Resolver explicitamente nesta fiada como `_tela_apos_entrega()` acessa `buscar_pedido()`/`mostrar_pedido()`/`teclado_pedido()` (funções do domínio Pedido) — por injeção de função, não por import cruzado de `bot.py`. *Critério: todas as telas renderizam texto e botões idênticos ao estado anterior.*

**Fiada 4 — Despacho de callback:** criar `entrega/despacho.py` com `despachar(acao, partes, query, ctx, db_path)`, cobrindo as 16 ações hoje embutidas em `responder_botao()`. *Critério: os 16 fluxos de botão testados um a um, sem alteração perceptível.*

**Fiada 5 — Desvios em `receber_arquivo()`/`receber_texto()`:** mover os 6 estados de `ctx.user_data["aguardando"]` ligados a entrega para `entrega.tratar_texto()`/`entrega.tratar_arquivo()`, retornando `None` quando o estado não é de entrega. *Critério: nenhuma regressão nos 6 ramos de entrega nem nos ramos vizinhos não-entrega — teste cruzado obrigatório, é o ponto de maior risco do plano inteiro.*

**Fiada 6 — Fechar o domínio:** mover `entrega_cmd()`; fechar `entrega/__init__.py` com export público; atualizar `ARQUITETURA.md`, `ROADMAP.md`, `ESTADO.md`, `app/README.md`; medir a contagem final de linhas.

**Fiada opcional:** 3-5 testes `pytest` cobrindo CRUD básico de `entrega/registro.py`, usando `tests/fixtures` (hoje vazio) — investimento pequeno, proporcional ao risco assumido nas Fiadas 4 e 5.

---

## Pontos de acoplamento mapeados (documentados, não resolvidos)

1. `ctx.user_data["aguardando"]` é compartilhado por todos os domínios; os 6 estados de entrega não têm prefixo consistente (`foto_entrega_obs`, `foto_entrega_troca`, `obs_entrega_texto`, `edit_obs_entrega_texto`, `entrega_legenda_inicial`, `entrega_legenda_add`) — um roteador por prefixo erraria 4 dos 6.
2. `receber_arquivo()` conhece o vocabulário de estado de entrega antes de qualquer dispatcher — é o handler genérico de upload, não deveria saber de domínio.
3. `responder_botao()` despacha as 16 ações de entrega misturadas com PFM/PIX/NF-e dentro do mesmo `if/elif` de ~800 linhas e do mesmo `try/except Exception` genérico — erros de extração (import quebrado, assinatura trocada) seriam mascarados como "Erro inesperado".
4. `_tela_apos_entrega()` chama de volta `buscar_pedido()`, `mostrar_pedido()`, `teclado_pedido()` — dependência cruzada nos dois sentidos com o domínio Pedido.
5. `teclado_pedido()` (função do domínio Pedido) constrói `callback_data` com vocabulário de entrega diretamente (`entrega_ver_fotos`, `entrega_editar`).
6. `sel_tipo_inicial` trata `tipo == "foto_entrega"` como desvio embutido no meio do dispatcher central de classificação de documento, antes de chamar o Claude.
7. `entrega_fotos` referencia `documentos.id` e `lancamentos.pfm_codigo` sem `FOREIGN KEY` declarada.
8. Todas as funções de entrega usam a constante global `DB_PATH` diretamente — nenhuma recebe `db_path` como parâmetro hoje (diferente de `financeiro/`, que já nasceu correto).
9. `_listar_fotos_entrega()` faz `JOIN` contra `documentos` (domínio Pedido) — decisão pendente: `entrega/` pode ler `documentos`, ou `bot.py` deve resolver o caminho do arquivo e passá-lo como parâmetro?
10. `_fmt_brl()` (helper genérico de formatação) é usado dentro de função de entrega — sem módulo de utilitários compartilhados hoje.

---

## O que Esta ADR Não Decide

- Se e quando a Alternativa B (redesenho do dispatcher por prefixo de domínio) será adotada
- A extração de PIX, NF-e ou obras de `bot.py`
- Quem é dono de `documentos` quando lido por `entrega/` (item 9 acima) — decisão de uma frase a ser tomada na Fiada 3, quando a extração realmente acontecer
- Adoção de uma suíte de testes automatizados como exigência geral do projeto

---

## Alinhamento com a Constituição

| Princípio | Como esta decisão o honra |
|---|---|
| Aprender antes de otimizar | Adiamos até a fronteira do domínio ser exercitada por uso real e pelos casos abertos da Fase 6 — não fixamos um contrato sobre um modelo que sabemos que vai mudar |
| Dados são sagrados | Nenhuma extração acontece sem que a propriedade do schema de `lancamentos` esteja resolvida primeiro |
| Simplicidade | Não inventamos uma camada de roteamento genérica nem um módulo novo só para "resolver" o número de linhas — o teto da ADR-001 é um sintoma, não o problema em si |
| Engenharia viva | O adiamento não é silencioso: tem gatilho de revisão preciso, plano de execução pronto e a inconsistência de documentação (2000 vs 2500–3000 linhas) foi corrigida |
| Fiadas pequenas | O plano preservado (quando executado) continua em 6-7 fiadas pequenas, cada uma reversível isoladamente |

---

*Aprovada por Dennis Verschoor — 2026-06-30*
*Análise técnica: Claude Sonnet 5, com apoio de dois agentes independentes (proposta arquitetural + revisão adversarial de risco)*
*Próxima revisão: ao atingir o gatilho definido acima*
