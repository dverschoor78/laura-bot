# Glossário da Laura

> Este documento registra decisões de linguagem do produto.
> Ele não é um dicionário. É um argumento.
> Cada termo carrega o motivo pelo qual foi escolhido.
>
> Última revisão: 2026-06-29

---

## Como usar este documento

Quando escrever qualquer coisa que o usuário lerá — mensagem, botão, tela, documento —
consulte este glossário.

Se o termo que você quer usar não está aqui, questione se ele deveria estar.
Se está aqui com uma versão alternativa proibida, use a versão aprovada.
Se precisar adicionar um termo novo, registre o motivo. Um termo sem justificativa
não entra neste documento.

---

## Linguagem do Usuário

Termos que aparecem em mensagens, botões, documentos e qualquer interface com o usuário.

---

### Pedido de Compra

**Aprovado:** Pedido de Compra
**Identificador público:** #GGV03-009 (número de série do pedido)
**Banidos:** PFM, Pedido de Fornecimento, Pedido de Fornecimento de Material, pfm_codigo

**Por que:**
PFM é jargão interno. O usuário não emite "PFMs" — emite Pedidos de Compra, como qualquer
empresa. O termo PFM continuará existindo no código e no banco como identificador técnico.
Nunca aparecerá para o usuário.

O identificador público (#GGV03-009) existe para referência rápida, como um número de nota
fiscal. Não é o nome do objeto — é o endereço dele.

---

### Aguardando pagamento

**Aprovado:** Aguardando pagamento
**Marcador visual:** 🟡
**Banidos:** a_pagar, pendente, em aberto (quando referindo-se ao status de um pedido individual)

**Nota:** "em aberto" é aceitável como qualificador em contagens — *"3 pedidos em aberto"* —
mas não como status de um pedido individual.

**Por que:**
"a_pagar" é uma constante de banco de dados. "Pendente" é ambíguo: pendente de quê?
"Aguardando pagamento" descreve o estado do pedido do ponto de vista do usuário — o pedido
existe, foi emitido, e está esperando o pagamento ser feito.

---

### Pago

**Aprovado:** Pago
**Marcador visual:** 🟢
**Banidos:** quitado, liquidado

**Por que:**
"Pago" é a palavra mais simples e direta. "Quitado" é jargão financeiro formal demais para
a interface. "Liquidado" é jargão bancário que o usuário não usa no dia a dia de obra.

---

### Requer atenção

**Aprovado:** Requer atenção
**Marcador visual:** 🔴
**Banidos:** pendente_revisao, com problema, erro, rejeitado

**Por que:**
"pendente_revisao" é código. "Com problema" é vago. "Requer atenção" é a linguagem que
um assistente competente usaria: não anuncia um erro, convida a uma ação. Preserva a
postura da Laura — ela informa sem punir.

---

### Substituído

**Aprovado:** Substituído
**Marcador visual:** ⚫
**Banidos:** cancelado

**Por que:**
Pedidos não são cancelados — são substituídos por versões corrigidas. "Cancelado" implica
que o pedido não vai acontecer. "Substituído" preserva o histórico e indica que existe uma
versão mais recente. A rastreabilidade é parte da promessa da Laura.

---

### Sem registro financeiro

**Aprovado:** Sem registro financeiro
**Marcador visual:** ⚪
**Banidos:** sem_lancamento, sem lançamento

**Por que:**
"sem_lancamento" é código. "Sem lançamento" expõe o conceito interno de lançamento.
O usuário não vê lançamentos — vê (ou não vê) registros financeiros.

---

### Corrigir / Ajustar

**Aprovados:** Corrigir (contexto de extração), Ajustar (contexto de decisão deliberada)
**Banidos:** editar, modificar, alterar

**Por que:**
"Editar" posiciona a Laura como um banco de dados com formulários. "Corrigir" e "Ajustar"
preservam o papel da Laura: ela extraiu informação, o usuário valida.

Ver distinção conceitual completa na seção **Distinções Conceituais**.

---

### Correspondência

**Aprovado:** Correspondência (plural: correspondências)
**Banidos:** candidato, match, resultado, sugestão

**Por que:**
"Candidatos" revela o processo interno de seleção — algo que o usuário não deveria
precisar conhecer. "Correspondência" descreve a relação entre dois objetos (o comprovante
e o pedido) de forma natural e direta.

---

### Obra

**Aprovado:** Obra (singular), Obras (plural)
**Identificador técnico:** GGV03 (aceitável na interface como código de referência)
**Banidos:** projeto, empreendimento; GGV como nome (é código, não nome)

**Por que:**
"GGV03" é o código da obra, não o nome. A obra é uma "obra". Os códigos GGV são familiares
no contexto da DeltaD e podem aparecer como identificadores, mas sempre com contexto —
"Obra GGV03", nunca sozinhos como se fossem nomes próprios.

---

### Comprovante

**Aprovado:** Comprovante (ou "comprovante de pagamento" quando necessário distinguir)
**Banidos:** comprovante_pix (o meio não precisa estar no nome do objeto)

**Por que:**
O que importa é que é uma prova de pagamento. O meio (PIX, TED, boleto) é detalhe
secundário. Quando relevante, aparece como contexto: "Comprovante de R$ 6.775,61 via PIX".
Mas o objeto se chama "comprovante".

---

### Cockpit da Obra

**Aprovado:** Cockpit da Obra (em documentação de produto e decisões de design)
**Na interface:** o nome da obra — ex: "Obra GGV03"
**Banidos:** painel, dashboard, tela de consulta

**Por que:**
"Cockpit" é um conceito de design, não um rótulo de interface. A tela que mostra o estado
financeiro de um GGV não é um painel passivo — é um instrumento ativo que orienta decisões
e chama atenção para o que precisa de ação. O conceito guia o design; a palavra não precisa
aparecer na interface.

---

## Linguagem Interna

Termos do código e do banco de dados. Nunca aparecem para o usuário.

| Termo interno | Significado técnico | Equivalente público |
|---|---|---|
| `pfm_codigo` | Identificador do pedido | Pedido #GGV03-009 |
| `a_pagar` | Status de lançamento | Aguardando pagamento |
| `pago` | Status de lançamento | Pago |
| `pendente_revisao` | Status de lançamento | Requer atenção |
| `substituido` | Status de lançamento | Substituído |
| `sem_lancamento` | Status de lançamento | Sem registro financeiro |
| `doc_id` | ID do documento no banco | — (nunca exposto) |
| `hash` | Fingerprint do arquivo | — (nunca exposto) |
| `identificador_comprovante` | ID da transação PIX/MP | — (nunca exposto) |
| `lancamento` | Registro financeiro no banco | Registro financeiro |
| `dados_claude` | Resposta bruta da IA | — (nunca exposto) |
| `GGV_ATIVO` | Variável de ambiente | — (nunca exposto) |

---

## Distinções Conceituais

Casos onde dois conceitos poderiam ser confundidos — e por que são diferentes.

---

### Corrigir vs. Ajustar

**Corrigir:** A Laura extraiu uma informação do documento e entendeu errado.
O usuário está corrigindo um erro de extração.

> A Laura leu "R$ 6.775,01" e o valor real é "R$ 6.775,61". O usuário corrige.

**Ajustar:** A Laura extraiu corretamente, mas o usuário quer mudar uma decisão.
Não é erro de extração — é uma escolha deliberada.

> A Laura leu "entrega em 07/08" e o usuário quer "21/08" por conveniência. O usuário ajusta.

**Na interface:** os dois casos usam o botão "Corrigir" por simplicidade. A distinção
conceitual existe para orientar o design — a tela de correção não deve parecer um formulário
genérico de banco de dados, mas uma validação do que Laura entendeu.

**No futuro:** quando a confiança da extração for visível na interface, a linguagem poderá
ser refinada para refletir a distinção de forma explícita.

---

### Cockpit vs. Painel

**Painel:** exibe informações. O usuário consulta. Postura passiva do sistema.

**Cockpit:** orienta decisões. O sistema chama atenção para o que exige ação. Postura ativa.

A visão de um GGV é um Cockpit, não um painel. Isso significa que ela não exibe apenas
o estado — ela destaca o que precisa de atenção: vencimentos passados, pedidos sem
comprovante, valores discrepantes.

> *"Laura não espera ser perguntada. Ela mostra o que precisa de atenção."*

---

### Orçamento vs. Pedido de Compra

**Orçamento:** documento recebido do fornecedor. É a proposta deles. Entra na Laura.

**Pedido de Compra:** documento gerado pela Laura. É a ordem formal da DeltaD. Sai da Laura.

São objetos diferentes, em direções opostas, com papéis distintos. O orçamento é matéria-prima;
o Pedido de Compra é o produto.

---

### Comprovante vs. Extrato

**Comprovante:** prova de um pagamento específico. Está vinculado a um único pedido.

**Extrato:** histórico de movimentações de uma conta (ex: Mercado Pago). Mostra múltiplas
transações em um período.

A Laura trata os dois de formas diferentes: o comprovante é vinculado a um pedido específico;
o extrato é processado para conciliação (funcionalidade futura).

---

*Responsável: Dennis Verschoor + Claude*
*Última revisão: 2026-06-29*
*Próxima revisão: ao final da Fase 2 de implementação (Estrutura) ou quando surgir novo termo relevante*
