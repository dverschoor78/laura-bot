# Processo de Desenvolvimento — Projeto Laura

> Como acontece uma sessão de desenvolvimento da Laura.

---

## A pergunta que abre tudo

Antes de qualquer implementação que o usuário verá, responda:

> **"Isso parece com a Laura?"**

Se a resposta não for imediata, releia `docs/IDENTIDADE_DO_PRODUTO.md` antes de continuar.
Só depois: *"como implementamos?"*

Essa inversão — identidade antes de implementação — é a marca de maturidade do projeto.
A engenharia continua rigorosa. Mas toda decisão de interface, mensagem, navegação
ou experiência começa por aqui.

---

## 1. Abertura da Sessão

Antes de qualquer alteração, identifique o tipo da fiada e leia os documentos
na ordem correspondente.

### Sessão de Engenharia

Use quando a fiada envolver arquitetura, banco de dados, IA, integrações,
performance ou infraestrutura.

Leia nesta ordem:
1. `docs/ESTADO.md` — onde o projeto está agora
2. `docs/ROADMAP.md` — o que vem a seguir
3. `docs/CONSTITUICAO.md` — se for a primeira sessão ou após longa pausa
4. `docs/ARQUITETURA.md` — obrigatório quando envolve estrutura ou banco
5. `docs/decisoes/` — ADR relacionada, se existir

### Sessão de Produto

Use quando a fiada envolver UX, Telegram, interface, mensagens, Design System,
documento, PDF, navegação ou experiência do usuário.

Leia nesta ordem:
1. `docs/IDENTIDADE_DO_PRODUTO.md` — quem é a Laura e o que ela promete
2. `docs/GLOSSARIO.md` — como Laura fala e os termos aprovados
3. `docs/ESTADO.md` — onde o projeto está agora
4. `docs/ROADMAP.md` — o que vem a seguir
5. `docs/PROCESSO.md` — este documento
6. `docs/ARQUITETURA.md` — apenas quando necessário

**Antes de escrever uma linha de código que o usuário verá, lembre quem é a Laura.
Só depois pense em implementação.**

---

Confirmar o entendimento antes de propor qualquer código.

Se durante a leitura forem encontradas inconsistências entre os documentos,
interromper a implementação e corrigir primeiro a documentação.

---

## 2. Planejamento

- [ ] Identificar a próxima fiada no ROADMAP
- [ ] Discutir alternativas quando existirem
- [ ] Definir o critério de aceite
- [ ] Obter aprovação de Dennis antes de começar

**Nenhum código antes da aprovação do planejamento.**

---

## 2.5. Validação da Identidade

*Aplica-se a toda fiada que produza algo visível ao usuário.*

Antes de implementar, responder internamente:

1. Esta mudança reforça a promessa da Laura?
2. Ela reduz ou aumenta a carga cognitiva do usuário?
3. O usuário entende a próxima decisão em menos de três segundos?
4. Laura está ajudando a decidir ou apenas mostrando dados?
5. Esta solução respeita a `IDENTIDADE_DO_PRODUTO.md`?

**Se alguma resposta for negativa, interromper a implementação e replanejar.**
Não existe velocidade de entrega que justifique comprometer a identidade do produto.

---

## 3. Implementação

- Uma fiada por vez
- Uma responsabilidade por fiada
- Não misturar refatoração com nova funcionalidade

**Regra de domínio (ADR-002):**
- Lógica de negócio do domínio Financeiro nasce em `financeiro/` — nunca em `bot.py`
- `bot.py` é o orquestrador da conversa Telegram; ele chama o domínio, não implementa a lógica
- Todo novo domínio futuro segue o mesmo princípio: nasce em seu próprio módulo desde o primeiro dia

Se durante a implementação o escopo crescer, parar e replanejar.

---

## 4. Testes

- [ ] Testar o fluxo afetado manualmente
- [ ] Verificar que nenhuma funcionalidade existente foi quebrada
- [ ] Só então considerar a fiada concluída

---

## 5. Housekeeping

Antes do commit:

- [ ] Remover código morto introduzido ou exposto pela fiada
- [ ] Remover TODOs e comentários temporários
- [ ] Revisar nomes (funções, variáveis, constantes)
- [ ] Verificar imports desnecessários
- [ ] Confirmar que a documentação continua coerente com o código
- [ ] Se a fiada introduz uma nova ação acessível pelo usuário, atualizar `mostrar_ajuda()` em `bot.py` com uma linha descritiva no estilo: "Para X, basta Y."

---

## 6. Commit

- Todo commit representa um estado funcional — nunca commitar código quebrado
- Um commit por fiada, ou por conjunto coeso de mudanças da mesma sessão
- Mensagem de commit: `tipo: o que e por que`, não apenas quais arquivos foram alterados

---

## 7. Encerramento

- [ ] Atualizar `ESTADO.md` com o novo estado do projeto
- [ ] Atualizar `ROADMAP.md` (remover o que foi feito, adicionar o que emergiu)
- [ ] Atualizar `ARQUITETURA.md` se a estrutura do sistema mudou
- [ ] Atualizar `CHANGELOG.md` quando houver nova funcionalidade para o usuário
- [ ] Registrar ADR se uma decisão arquitetural importante foi tomada
- [ ] Fazer push para o GitHub

---

## 8. Quando NÃO desenvolver

Se durante o planejamento ou a implementação ocorrer qualquer um dos seguintes:

- A fiada está grande demais para ser compreendida, testada e revertida
- O problema ainda não está suficientemente compreendido
- Existe uma decisão arquitetural pendente que afetará a implementação
- A validação de identidade (2.5) gerou respostas negativas sem resolução clara

**→ Encerre a sessão com planejamento. Não com código.**

Registrar o entendimento no ESTADO.md e retomar na próxima sessão.
A vontade de produzir não deve superar a clareza sobre o que produzir.

---

*O processo existe para reduzir o custo de desenvolvimento, não para aumentá-lo.
Se algum passo deixar de agregar valor ao projeto, ele deve ser simplificado ou removido.*
