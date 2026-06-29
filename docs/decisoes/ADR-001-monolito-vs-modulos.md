# ADR-001 — Manter monólito vs. modularizar

**Status:** Aceita
**Data:** 2026-06-29
**Responsáveis:** Dennis Verschoor (decisão) · Claude Sonnet 4.6 (análise técnica)

---

## Contexto

O Projeto Laura nasceu pequeno e cresceu de forma incremental por fiadas.
Hoje possui aproximadamente 1400 linhas concentradas em `bot.py`.

A divisão conceitual do código já existe — constantes, banco, integração Claude,
geração de PFM, domínio do Pedido, teclados e handlers são blocos distintos com
responsabilidades claras. O que não existe é a separação física em arquivos e módulos.

A Constituição do projeto estabelece simplicidade, fiadas pequenas e aprendizado
acima da perfeição. Qualquer decisão arquitetural deve ser avaliada à luz desses
princípios.

---

## Alternativas consideradas

**A. Manter monólito (decisão atual)**

| Prós | Contras |
|---|---|
| Desenvolvimento rápido, sem overhead de imports e módulos | Arquivo cresce a cada fiada |
| Custo cognitivo baixo — um único arquivo para ler | Testes automatizados mais difíceis |
| Refatorações internas sem risco de quebrar interfaces | Acoplamento entre blocos mais alto |
| Alinhado ao estágio atual do projeto | Navegação exige busca por símbolo (Ctrl+F) |
| IA lê o contexto completo em uma sessão | — |

**B. Modularizar imediatamente**

Dividir em `app/bot/handlers/`, `app/services/`, `app/db/`, etc. — estrutura
planejada originalmente no projeto.

| Prós | Contras |
|---|---|
| Separação clara de responsabilidades | Refatoração significativa (~1 sessão inteira) |
| Testes por módulo se tornam viáveis | Risco de regressão em código estável |
| Preparado para crescimento futuro | Overhead desnecessário para projeto solo |
| — | IA precisaria ler múltiplos arquivos por sessão |
| — | Complexidade sem ganho real no estágio atual |

**C. Modularização parcial**

Extrair apenas o módulo mais problemático (ex: `gerar_pfm()` em `pfm_service.py`).

| Prós | Contras |
|---|---|
| Melhoria incremental sem refatoração total | Cria inconsistência: parte modular, parte monólito |
| Menor risco de regressão | Não resolve o problema fundamental |
| — | Adiciona complexidade sem entregar o benefício completo |

---

## Decisão

**Mantemos o monólito em `bot.py`.**

Não por desconhecimento das alternativas.
Mas porque é a decisão que melhor atende ao estágio atual do projeto.

A divisão conceitual já existe no código. A divisão física viria com custo real
e benefício pequeno agora. Quando o benefício superar o custo, modularizamos.

---

## Consequências

### Benefícios atuais

- Desenvolvimento rápido: cada fiada toca um único arquivo
- Custo cognitivo baixo: contexto completo em uma sessão com IA
- Refatorações internas sem risco de quebrar interfaces entre módulos
- Menor quantidade de arquivos para manter e versionar

### Custos conhecidos

- `bot.py` cresce a cada fiada — navegação demanda uso das referências em `ARQUITETURA.md`
- Testes automatizados exigem setup mais cuidadoso (funções acopladas ao banco e ao Telegram)
- `responder_botao()` é o ponto de maior acoplamento — dispatcher de ~280 linhas
- `gerar_pfm()` concentra três responsabilidades distintas

---

## Gatilhos para revisão

Esta decisão deverá ser revisada quando **um ou mais** dos seguintes ocorrerem:

- `bot.py` ultrapassar aproximadamente **2.500–3.000 linhas**
- Dificuldade recorrente para **localizar responsabilidades** no arquivo
- Necessidade de **testes automatizados por módulo**
- **Múltiplos desenvolvedores** trabalhando simultaneamente
- Nova funcionalidade exigir **isolamento claro** que o monólito não comporta

Quando isso ocorrer, abrir ADR-002 com a proposta de modularização.

---

## Alinhamento com a Constituição

| Princípio | Como esta decisão o honra |
|---|---|
| Aprender antes de otimizar | A arquitetura modular ideal foi planejada antes de entender o problema. O monólito surgiu do aprendizado real. |
| Simplicidade | Um arquivo é mais simples que dez. Aumentamos complexidade quando ela resolver um problema real. |
| Fiadas pequenas | Modularizar agora seria uma fiada grande e arriscada sem ganho proporcional. |
| Aprendizado acima da perfeição | Optamos pela velocidade de aprendizado sobre a perfeição arquitetural. |
| Engenharia viva | Esta ADR documenta a decisão real, não a arquitetura ideal. Será revisada quando os gatilhos ocorrerem. |
