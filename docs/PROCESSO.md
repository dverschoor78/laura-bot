# Processo de Desenvolvimento — Projeto Laura

> Como acontece uma sessão de desenvolvimento da Laura.

---

## 1. Abertura da sessão

Leia nesta ordem antes de qualquer alteração:

1. `docs/ESTADO.md` — onde o projeto está agora
2. `docs/ROADMAP.md` — o que vem a seguir
3. `docs/CONSTITUICAO.md` — se for a primeira sessão ou após longa pausa
4. `docs/ARQUITETURA.md` — quando a tarefa envolver estrutura ou banco
5. `docs/decisoes/` — ADR relacionada, se existir

Confirmar o entendimento antes de propor qualquer código.

Se durante a leitura forem encontradas inconsistências entre os documentos de
engenharia, interromper a implementação e corrigir primeiro a documentação.

---

## 2. Planejamento

- [ ] Identificar a próxima fiada no ROADMAP
- [ ] Discutir alternativas quando existirem
- [ ] Definir o critério de aceite
- [ ] Obter aprovação de Dennis antes de começar

**Nenhum código antes da aprovação do planejamento.**

---

## 3. Implementação

- Uma fiada por vez
- Uma responsabilidade por fiada
- Não misturar refatoração com nova funcionalidade

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

Se durante o planejamento ocorrer qualquer um dos seguintes:

- A fiada está grande demais para ser compreendida, testada e revertida
- O problema ainda não está suficientemente compreendido
- Existe uma decisão arquitetural pendente que afetará a implementação

**→ Encerre a sessão com planejamento. Não com código.**

Registrar o entendimento no ESTADO.md e retomar na próxima sessão.
A vontade de produzir não deve superar a clareza sobre o que produzir.

---

*O processo existe para reduzir o custo de desenvolvimento, não para aumentá-lo.
Se algum passo deixar de agregar valor ao projeto, ele deve ser simplificado ou removido.*
