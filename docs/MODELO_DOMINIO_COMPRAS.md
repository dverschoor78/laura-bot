# Modelo de Domínio — Compras

> Este documento faz a transição entre o negócio e o software: identifica os conceitos
> fundamentais do domínio de Compras, seus ciclos de vida, eventos e responsabilidades —
> sem propor banco de dados, classes ou APIs. Base para `docs/POLITICA_COMPRAS.md` e
> `docs/CASOS_DE_USO_COMPRAS.md`, que continuam sendo a verdade do domínio.
>
> Última revisão: 2026-07-03 — encerrado, pronto para servir de base à implementação.

---

## Objetos conceituais

### Com ciclo de vida próprio (entidades)

**Lista de Compras** — agrega a necessidade organizada de uma obra. Existe do primeiro item sugerido até ser encerrada.

**Item da Lista** — cada necessidade individual dentro da lista (ex: "cimento CP-II, 100 sacos"). Tem ciclo de vida próprio, distinto do da Lista inteira — é o nível onde a compra de fato se resolve, não a lista como um todo.

**Orçamento** — a proposta já negociada que entra na Laura. Vida curta: nasce ao ser recebido, se transforma ao originar um Pedido de Compra.

**Pedido de Compra** — já existe hoje, com ciclo próprio já validado em produção. Não precisa de nova modelagem — só ganha uma origem nova: nasce de um Orçamento que, por sua vez, pode ter nascido de um Item de Lista.

**Alerta** — o que a Laura gera nos Casos 11 a 15 de `CASOS_DE_USO_COMPRAS.md`. Nasce quando ela detecta uma condição (cadência, desvio, duplicidade, tendência, lista parada). Morre quando o usuário responde — agindo ou dispensando.

### Sem ciclo de vida próprio (apoiam outros objetos)

**Fornecedor Preferencial** — não é objeto separado, é uma classificação sobre o cadastro de Fornecedor (que já existe). Muda de valor, não tem estados próprios.

**Referência de Preço** — não é entidade persistida, é um valor computado sob demanda, com três estados possíveis: confirmada / aproximada / ausente (Princípio 8 da Política). A empresa não possui esse valor de forma independente — ele só existe no momento da comparação.

**Tendência de Fornecedor** (Caso 15) — igual à Referência de Preço: uma interpretação sobre um conjunto de compras já registradas ao longo do tempo contra o mesmo fornecedor, não algo que existe por si só.

### Fora deste modelo, por decisão de escopo

**Compra Obrigatória** — não passa pela cadeia Lista → Orçamento → Pedido. Usa diretamente Fatura → Pedido/fechamento, fluxo que já existe hoje. Fica fora deste mapa (Princípio 10 da Política já estabelece que é domínio próprio).

---

## Estados e transições

**Lista de Compras**

| Estado | Significado |
|---|---|
| Aberta | sendo montada/ajustada — estado inicial |
| Encerrada | todo Item pendente virou Pedido ou foi removido |
| Descartada | a necessidade original deixou de existir (Caso 12) |

Transições: `Aberta → Encerrada` (todos os itens resolvidos) · `Aberta → Descartada` (decisão humana explícita)

**Item da Lista**

| Estado | Significado |
|---|---|
| Pendente | identificado, ainda não comprado — pode ou não já ter um orçamento associado a ele (ver nota abaixo) |
| Comprado | um Pedido de Compra nasceu dele |
| Removido | retirado sem virar compra — não precisava mais, ou virou compra emergencial fora do fluxo |

*Nota: um item Pendente pode carregar a informação de que já existe um orçamento em negociação para ele. Isso é um atributo opcional do item, não um estado próprio — a negociação em si nunca é rastreada como fase formal, porque acontece inteiramente fora da Laura (Princípio 4).*

**Orçamento**

| Estado | Significado |
|---|---|
| Recebido | chegou, dados extraídos (já existe hoje) |
| Confirmado | virou base de um Pedido de Compra |
| Não escolhido | conceito real (Caso 5) — um orçamento que existiu e não venceu a negociação. Sua persistência é decisão de implementação, em aberto; o conceito em si é domínio válido |

**Pedido de Compra** — mantém o ciclo já validado: recebido → confirmado → emitido → substituído. Não muda.

**Alerta**

| Estado | Significado |
|---|---|
| Gerado | Laura detectou a condição |
| Apresentado | mensagem enviada ao usuário |
| Resolvido | usuário agiu ou dispensou — a política não distingue os dois, ambos encerram o alerta |

---

## Eventos de domínio, por momento

**Antes da compra:** necessidade identificada · Lista criada · item adicionado/ajustado · cadência de recompra excedida (Caso 11) · lista sem atualização por N dias (Caso 12)

**Durante a compra:** orçamento recebido · orçamento associado a um item de uma Lista (opcional) · desvio de padrão detectado (Caso 13) · possível duplicidade detectada (Caso 14) · tendência de fornecedor detectada (Caso 15) · Pedido de Compra emitido

**Depois da compra:** compra registrada no histórico · referência de preço/cadência atualizada para o item · tendência do fornecedor recalculada

---

## Responsabilidades

| Laura | Usuário (Dennis) |
|---|---|
| Sugerir itens/quantidades para uma Lista nova, com base no histórico | Definir a Lista final — aceitar, ajustar ou ignorar sugestões |
| Apresentar Referência de Preço com grau de confiança declarado | Toda a negociação externa, 100% fora do sistema |
| Reconhecer quando um orçamento recebido corresponde a um item de uma Lista em aberto | Escolher o fornecedor |
| Comparar orçamento recebido contra histórico do item e do fornecedor | Confirmar/inserir o orçamento negociado |
| Gerar o Pedido de Compra a partir do orçamento confirmado | Confirmar a geração do Pedido de Compra |
| Perceber e sinalizar: cadência quebrada, lista parada, desvio, duplicidade, tendência | Decidir o que fazer diante de qualquer Alerta — agir, ignorar, explicar |
| Registrar o resultado de cada compra como novo ponto de histórico | Classificar (e revisar) um fornecedor como preferencial |

Laura nunca decide negociação, escolha de fornecedor, ou confirmação financeira — em nenhuma circunstância.

---

## Regras de negócio, por momento

**Antes:** nenhuma compra planejável sem Lista (Princípio 1) · Lista é decisão técnica, sem fornecedor definido (Princípio 2) · toda sugestão declara se é dado real ou inferência (Princípio 8)

**Durante:** negociação nunca acontece dentro da Laura (Princípio 4) · toda comparação usa Referência de Preço com confiança declarada (Princípio 5, 8) · Fornecedor Preferencial participa da comparação como qualquer outro (Princípio 6)

**Depois:** todo Pedido de Compra concluído atualiza o histórico do item e, se aplicável, do fornecedor (Princípio 9) · Alertas nascem de comparação contra histórico, nunca de decisão autônoma (Princípio 12)

---

## Mapa conceitual

```
Necessidade da obra (evento, não persiste)
        │
        ▼
Lista de Compras ──contém──► Item da Lista (N)
        │                         │
        │                    [negociação externa,
        │                     fora da Laura]
        │                         │
        │                         ▼
        │                    Orçamento ──origina──► Pedido de Compra
        │                                                  │
        └── encerra quando todo Item = Comprado/Removido    ▼
                                                        Histórico
                                                    (item, fornecedor)
                                                              │
                                              ┌───────────────┴───────────────┐
                                              ▼                               ▼
                                    Referência de Preço              Tendência de Fornecedor
                                    (computada sob demanda)          (computada sob demanda)
                                              │                               │
                                              └──────────► Alerta ◄───────────┘
                                                    (Casos 11-15)
```

Fornecedor (cadastro existente) participa em três pontos: origem do Orçamento, classificação Preferencial, e sujeito da Tendência.

---

*Responsável: Dennis Verschoor + Claude*
*Baseado em: `docs/POLITICA_COMPRAS.md`, `docs/CASOS_DE_USO_COMPRAS.md`*
*Encerrado — não sujeito a mais evolução conceitual. Mudanças futuras exigem revisitar este documento explicitamente.*
