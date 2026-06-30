# ADR-002 — Modularização Incremental por Domínio

**Status:** Aceita
**Data:** 2026-06-30
**Responsáveis:** Dennis Verschoor (decisão) · Claude Sonnet 4.6 (análise técnica)
**Relacionada a:** ADR-001 (mantém a decisão sobre bot.py; adiciona princípio para domínios novos)

---

## Contexto

A ADR-001 definiu manutenção do monólito em `bot.py` e registrou os gatilhos para revisão. Um deles foi atingido:

> *"Nova funcionalidade exigir isolamento claro que o monólito não comporta."*

O Módulo Financeiro é um domínio novo, grande e de longa vida. Não é uma extensão do fluxo de Pedido de Compra — é um sistema paralelo com objetos próprios, ciclo de vida próprio e visões próprias. Adicionar tudo isso a `bot.py` empurraria o arquivo para 3.000–3.500 linhas, acima do limite de 2.500–3.000 registrado na ADR-001.

A resposta não é modularizar tudo. É impedir que o monólito continue crescendo para novos domínios.

---

## O Princípio Arquitetural

> **Todo novo domínio nasce modular.**
>
> Os domínios existentes permanecem no monólito até existir um motivo real para migração.
>
> A modularização acontece por nascimento, não por refatoração.

O fluxo de Pedido de Compra continua em `bot.py` porque funciona e está estável.
O domínio Financeiro nasce fora do `bot.py` porque há clareza sobre sua fronteira — e é a oportunidade de fazer certo desde o primeiro dia.

Não estamos quebrando o monólito. Estamos impedindo que ele cresça para além do seu domínio.

---

## Os Dois Objetos Centrais da Laura

A partir desta fase, a Laura possui dois objetos de domínio igualmente importantes:

### Pedido de Compra
Representa a **decisão comercial**: o que será comprado, de quem, por quanto, com quais condições.

- Domínio: compras
- Reside em: `bot.py`
- Lifecycle: recebido → confirmado → pfm_gerado → substituido
- Origem: um orçamento recebido do fornecedor
- Identificador público: #GGV03-009

### Lançamento Financeiro
Representa o **impacto financeiro** dessa decisão — e de todos os outros fatos que movimentam dinheiro nas obras.

- Domínio: financeiro
- Reside em: `financeiro/`
- Lifecycle: A_PAGAR → PAGO → CONCILIADO
- Origem: um Pedido de Compra (automático) ou entrada manual (aportes, impostos, avulsos)
- Não possui identificador público próprio — é referenciado pelo pfm_codigo quando existe

**Relação entre os dois:**

Um Pedido de Compra sempre gera um Lançamento Financeiro.
Um Lançamento Financeiro nem sempre tem um Pedido de Compra.
Nenhum substitui o outro.
Toda decisão arquitetural futura deve respeitar esta separação.

---

## Alternativas Consideradas

### A. Continuar o monólito — adicionar Financeiro ao bot.py

| Prós | Contras |
|---|---|
| Zero mudança de estrutura | Viola o limite definido na ADR-001 |
| Nenhum risco estrutural | Financeiro e Telegram acoplados para sempre |
| | Cada sessão de IA lê 3.000+ linhas para alterar 100 |
| | Impossível testar lógica financeira sem inicializar o bot |

**Descartada.** Viola a ADR-001 e cria débito de difícil reversão.

---

### B. Modularização total — extrair também o fluxo de PFM

Quebrar bot.py na estrutura planejada originalmente em `app/`.

| Prós | Contras |
|---|---|
| Arquitetura final desejada | Refatoração de 1.700 linhas de código estável |
| Testabilidade completa | Risco de regressão em fluxo validado em produção |
| | Uma sessão inteira sem entregar funcionalidade nova |
| | A estrutura `app/` foi planejada antes de o produto existir |

**Descartada.** O fluxo de PFM funciona. Refatorá-lo agora é custo sem ganho de produto.

---

### C. Modularização incremental por domínio ← **Decisão**

O domínio Financeiro nasce em `financeiro/`. O fluxo de PFM permanece em `bot.py`. `bot.py` orquestra o Telegram e chama o domínio financeiro quando necessário.

| Prós | Contras |
|---|---|
| bot.py não cresce com código financeiro | bot.py fica híbrido por tempo indefinido |
| Domínio financeiro nasce testável e isolado | Dois lugares para procurar lógica (transição esperada) |
| Fluxo existente do PFM não é tocado | |
| Cada fiada continua pequena e reversível | |
| Aplicação direta do princípio arquitetural | |

**Escolhida.**

---

## Estrutura do Módulo Financeiro

### Organização por domínio, não por operações

A estrutura reflete os objetos do domínio, não as operações que existem hoje.
Os objetos são mais importantes do que as funções.
Se daqui a dois anos existirem dezenas de operações novas, a estrutura continua natural.

```
financeiro/
    __init__.py          ← exports públicos do domínio
    lancamento.py        ← Objeto Lançamento Financeiro
    conciliacao.py       ← Objeto Conciliação Mensal + Período
```

### `lancamento.py` — O Lançamento Financeiro

Tudo que pertence ao objeto Lançamento vive aqui.

- Modelo: `Lancamento` dataclass com todos os campos
- Enums: `CategoriaLancamento`, `StatusLancamento`, `TipoDocumento`
- Ciclo de vida: transições de status (A_PAGAR → PAGO → CONCILIADO)
- CRUD: criar, buscar, atualizar, listar
- Lógica de negócio: sugestão de categoria por ramo do fornecedor
- Consultas e visões: extrato da obra, totais, composição por categoria, fluxo de caixa mensal
- Inicialização do banco: `init_db_financeiro()` via ALTER TABLE seguro

As visões (extrato da obra, cockpit financeiro, fluxo de caixa) são consultas sobre lançamentos. Pertencem a `lancamento.py` — não são um domínio separado.

### `conciliacao.py` — A Conciliação Mensal

Tudo que pertence ao processo de reconciliação vive aqui.

- Modelo: `Periodo` dataclass (mês/ano + conta + status aberto/fechado)
- Importação do extrato Mercado Pago: parse de CSV/XLSX
- Algoritmo de matching: transação do extrato ↔ lançamento da Laura
- Interface de divergências: o que não casou automaticamente
- Confirmação: `confirmar_conciliacao()` atualiza status para CONCILIADO
- Fechamento: `fechar_periodo()` torna lançamentos do período imutáveis

### `__init__.py` — Contrato público do domínio

Exporta apenas o que `bot.py` precisa chamar. O restante é detalhe de implementação.

```python
from .lancamento import (
    criar_lancamento_de_pfm,
    criar_lancamento_manual,
    buscar_lancamentos_obra,
    sugerir_categoria,
    atualizar_status,
    extrato_obra,
    totais_obra,
)
from .conciliacao import (
    processar_extrato_mp,
    divergencias_periodo,
    fechar_periodo,
)
```

---

## Estrutura de Pastas Resultante

```
01-Laura/
│
├── bot.py                          ← orquestrador Telegram (não cresce por Financeiro)
│
├── financeiro/
│   ├── __init__.py                 ← contrato público do domínio
│   ├── lancamento.py               ← Objeto Lançamento Financeiro
│   └── conciliacao.py              ← Objeto Conciliação + Período
│
├── app/                            ← reservado para ADR-003 (ver README interno)
│   ├── README.md
│   └── ... (diretórios existentes, sem arquivos Python)
│
├── data/
│   ├── laura.db
│   └── laura_test.db
│
└── docs/
    └── decisoes/
        ├── ADR-001-monolito-vs-modulos.md
        └── ADR-002-modularizacao-incremental.md
```

---

## Acesso ao Banco de Dados

Não será criado um `config.py` agora.

As funções do módulo financeiro recebem `db_path` como parâmetro explícito.
`bot.py` passa `DB_PATH` ao chamar funções do domínio financeiro.

```python
# bot.py (exemplo futuro)
from financeiro import criar_lancamento_de_pfm, extrato_obra

await criar_lancamento_de_pfm(DB_PATH, pfm_codigo, categoria, ...)
dados = extrato_obra(DB_PATH, "GGV03")
```

Benefícios desta escolha:
- Funções são puras em relação ao ambiente — não dependem de variáveis globais do módulo
- Testável sem variáveis de ambiente: basta passar o caminho do banco de teste
- Sem dependência de `bot.py` → sem importação circular

Quando existir necessidade real de configuração compartilhada entre múltiplos domínios, cria-se `config.py`. Não antes.

---

## Responsabilidades: o que fica em bot.py

`bot.py` continua responsável por:

- Toda a infraestrutura Telegram (Application, handlers, polling)
- Todos os handlers existentes: `receber_arquivo()`, `receber_texto()`, `responder_botao()`
- Todo o fluxo atual do Pedido de Compra: `gerar_pfm()`, `parse_resposta()`, teclados
- `init_db()` — estende-se para chamar `financeiro.lancamento.init_db_financeiro(DB_PATH)`
- Utilitários de domínio existentes: `buscar_fornecedor()`, `buscar_obra()`
- Constantes de negócio atuais: `DELTAD`, `TIPOS`, `PROMPT`
- Integração Claude para extração de orçamentos
- Novos handlers Telegram para funcionalidades financeiras (despacho apenas)

`bot.py` não implementa lógica financeira. Chama `financeiro.*` e usa o retorno para responder ao Telegram.

---

## Plano de Implementação em Fiadas

### Fiada 0 — Fundação (sem comportamento novo)

- Criar `financeiro/__init__.py` (vazio com docstring)
- Criar `financeiro/lancamento.py` (modelo + enums + `init_db_financeiro()`)
- Criar `financeiro/conciliacao.py` (esqueleto com docstrings)
- Criar `app/README.md`
- `init_db()` em bot.py passa a chamar `financeiro.lancamento.init_db_financeiro(DB_PATH)`

**Critério de aceite:** `python bot.py` sobe sem erro. Nenhum comportamento novo.

---

### Fiada 5a-1 — Categoria no Lançamento

- `financeiro/lancamento.py`: `CategoriaLancamento`, `sugerir_categoria(ramo)`
- Fluxo do PFM em bot.py exibe categoria sugerida com confirmação
- Lançamento gravado inclui `categoria`

**Critério de aceite:** ao gerar PFM de fornecedor com ramo conhecido, usuário vê e confirma a categoria.

---

### Fiada 5b-1 — Extrato da Obra

- `financeiro/lancamento.py`: `extrato_obra()`, `totais_obra()`, `composicao_categorias()`
- Cockpit da obra em bot.py ganha bloco financeiro
- Nenhum handler novo

**Critério de aceite:** digitar "GGV03" mostra totais financeiros além do cockpit atual.

---

### Fiada 5c-1 — Lançamentos Manuais

- `financeiro/lancamento.py`: `criar_lancamento_manual()`
- Novos handlers em bot.py (apenas despacho)

**Critério de aceite:** usuário registra um aporte sem PFM. Aparece no extrato da obra.

---

### Fiada 5d-1 — Conciliação Mensal

- `financeiro/conciliacao.py` completo
- Handler para arquivo extrato MP em bot.py

**Critério de aceite:** processo de fechamento mensal sem abrir a planilha.

---

## Riscos

**Importação circular** — mitigado pelo parâmetro `db_path`. `financeiro/` não importa de `bot.py`.

**Banco compartilhado** — aceito. Ambos usam conexão por operação (`with sqlite3.connect(db_path)`). Sem colisão real para uso sequencial de um único usuário.

**bot.py híbrido** — aceito por decisão. A regra é clara: Financeiro vai em `financeiro/`. Tudo mais vai em `bot.py` até ADR-003. Ambiguidade resolvida com o README do `app/`.

**Regressão no fluxo PFM** — mínimo. Fiada 0 adiciona apenas uma chamada em `init_db()`. Cada fiada seguinte adiciona chamadas, não remove código.

---

## Critérios de Aceite da Decisão Arquitetural

Esta ADR é bem-sucedida quando:

1. `bot.py` não ultrapassa **2.200 linhas** ao final da Fase 5
2. Todo código financeiro nasce em `financeiro/` — sem exceções sem nova ADR
3. `financeiro/` pode ser importado sem inicializar o bot Telegram
4. `bot.py` continua funcionando sem regressões após cada fiada
5. Um colaborador lê apenas `financeiro/` e entende o domínio financeiro sem precisar de `bot.py`

---

## O que Esta ADR Não Decide

- Quando e se `app/` será usada (pertence a ADR-003)
- Quando e se o fluxo de PFM será extraído de `bot.py` (pertence a ADR-003)
- Testes automatizados — a estrutura permite, a decisão de adotá-los é separada

---

## Alinhamento com a Constituição

| Princípio | Como esta decisão o honra |
|---|---|
| Fiadas pequenas | 4 fiadas independentes, cada uma revertível |
| Aprender antes de otimizar | Fluxo estável do PFM não é tocado; apenas o novo domínio nasce correto |
| Simplicidade | Dois arquivos. Um por objeto de domínio. Sem camadas. |
| Engenharia viva | Complementa a ADR-001 com o aprendizado do que o produto se tornou |

---

*Aprovada por Dennis Verschoor — 2026-06-30*
*Análise técnica: Claude Sonnet 4.6*
*Próxima revisão: ao atingir os gatilhos de ADR-003 (modularização de bot.py existente)*
