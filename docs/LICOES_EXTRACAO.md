# Lições de Extração e Parsing

> Catálogo vivo de armadilhas já encontradas na camada Claude → texto → parsing → exibição.
> Objetivo: não repetir o mesmo bug de formas diferentes. Antes de mexer no PROMPT, em `_campo()`,
> em qualquer `ITEM_RE`/regex de valor/data, ou em `buscar_fornecedor()`, leia este documento.

Toda entrada aqui nasceu de um caso real em produção, não de teoria. Formato: sintoma → causa raiz
→ correção → lição geral (a parte que generaliza para o próximo caso parecido).

---

## 1. Claude mistura o template de campos de dois tipos diferentes

**Sintoma:** um boleto (documento classificado como `[orcamento]`) voltou com dois blocos de campos
concatenados — um bloco no formato de `[comprovante_pix]` (Favorecido, Chave PIX, Instituição
financeira) e, embaixo, o bloco correto de `[orcamento]` (Fornecedor, Itens, Valor total). Boletos
bancários se parecem visualmente com recibo de pagamento, o que confunde o Claude mesmo depois de
classificar o tipo certo.

**Causa raiz:** o PROMPT (`PASSO 3`) não proibia explicitamente misturar templates — só dizia
"extraia conforme o tipo", o que o Claude nem sempre segue à risca quando o documento tem
ambiguidade visual.

**Correção:** instrução explícita no PROMPT (`bot.py`, fim do `PASSO 3`): "use SOMENTE os campos
da lista do tipo que você classificou... não misture campos de outro tipo".

**Lição geral:** instruções implícitas ("extraia conforme o tipo") não bastam quando o documento
tem ambiguidade visual. Para cada confusão de tipo já observada, adicionar uma proibição explícita
e nomeada no PROMPT, não só contar com a estrutura do PASSO 3.

---

## 2. Fornecedor confundido com a própria empresa (Pagador × Beneficiário)

**Sintoma:** no mesmo boleto do CREA, o CNPJ da DeltaD (Pagador do boleto) quase virou "fornecedor"
— o mesmo tipo de bug do v0.1.1 ("cliente como fornecedor"), mas o guard antigo só cobria o CNPJ
da VII, não o da DeltaD Engenharia (Verschoor Construções Civis, CNPJ 48.494.891/0001-06).

**Causa raiz:** `CNPJS_PROPRIOS_DIGITS` (antes `DELTAD_CNPJ_DIGITS`, singular) só tinha um CNPJ.
Dennis tem duas empresas (VII e DeltaD) que podem aparecer como Pagador em documentos diferentes.

**Correção:** `buscar_fornecedor()` agora ignora um **conjunto** de CNPJs próprios
(`CNPJS_PROPRIOS_DIGITS`), não um único. PROMPT também instrui: em boleto, Fornecedor = Beneficiário
/ Cedente, nunca o Pagador / Sacado.

**Lição geral:** qualquer guard de "CNPJ próprio" precisa cobrir **todas** as empresas do Dennis,
não só a mais óbvia. Se uma terceira empresa aparecer no futuro, adicionar aqui também — ver
[[project_deltad_vii]] na memória para o contexto societário completo.

---

## 3. Unidade de medida com dígito quebra o regex de item

**Sintoma:** item "100,0 m2" (sem o "²" sobrescrito) não teve o valor unitário calculado — o item
inteiro caiu no fallback de texto cru.

**Causa raiz:** `ITEM_RE` aceitava unidade só como `[A-Za-z]{1,4}` — letras puras. "m2", "m3",
"cm2" têm dígito no meio e nunca casavam.

**Correção:** grupo de unidade ampliado para `[A-Za-zÀ-ÿ]{1,4}[²³0-9]{0,2}` — aceita letras
acentuadas + até 2 caracteres finais de superíndice ou dígito.

**Lição geral:** unidades de construção civil frequentemente vêm sem superíndice (m2/m3 em vez de
m²/m³), principalmente de OCR ou digitação manual. Qualquer regex de unidade precisa assumir isso
por padrão, não como exceção.

---

## 4. `_parse_brl`: ponto sem vírgula é ambíguo (milhar × decimal)

**Sintoma:** valor "R$ 5.000" (sem centavos) virou `5.0` em vez de `5000.0` — o pagamento de
R$5.000 apareceu como R$5,00, e por consequência não bateu com nenhum pedido em aberto.

**Causa raiz:** `_parse_brl()` só tratava "." como separador de milhar quando havia vírgula na
mesma string. Sem vírgula, tratava "." como ponto decimal (estilo americano) — errado pro caso
comum de valor redondo em milhar sem centavos.

**Correção:** heurística — sem vírgula, se o último grupo após o "." tem exatamente 3 dígitos, é
separador de milhar (remove o ponto); senão é decimal. Testado contra 10 casos, incluindo valores
pequenos tipo "0.03" que não podem virar milhar.

**Lição geral:** esse é o bug mais perigoso do lote porque é silencioso — o valor não desaparece,
vira um número errado plausível. Qualquer função de parsing de valor monetário extraído por IA
precisa de teste explícito contra valores redondos em milhar sem centavos (ex: "R$ 1.500",
"R$ 25.000"), não só contra valores com vírgula.

---

## 5. Data extraída sem zero à esquerda quebra parser de largura fixa

**Sintoma:** data "5/06/2026 às 14:14:13" (dia sem zero à esquerda) virou "6 /20" no histórico do
pedido — ilegível.

**Causa raiz:** o código verificava `dt[2:3] == "/"` pra detectar formato "DD/MM/AAAA" (assumindo
sempre 2 dígitos de dia) e, se não achasse, caía em `_fmt_data_curta()` — que faz *slice* de índice
fixo assumindo formato ISO "AAAA-MM-DD". Nenhuma das duas suposições cobria "D/M/AAAA" (1 dígito).

**Correção:** `_fmt_data_flexivel()` — regex `^(\d{1,2})/(\d{1,2})/\d{2,4}` aceita 1 ou 2 dígitos,
formata sempre com zero à esquerda; cai pro parser ISO só se o regex não casar.

**Lição geral:** nunca fatiar string de data extraída por IA assumindo largura fixa de caractere.
O Claude não garante zero à esquerda em datas ("5/06" tanto quanto "05/06"). Sempre usar regex com
`{1,2}` pra dia/mês, nunca `dt[a:b]` cru. `_data_para_arquivo()` já fazia isso certo — os outros
formatadores de data deveriam ter seguido o mesmo padrão desde o início.

---

## 6. Documento que falha não pode ficar preso pelo hash

**Sintoma:** comprovante que não bateu com nenhum pedido (por causa do bug #4) ficou definitivamente
bloqueado para reenvio — `ja_existe()` barra qualquer arquivo com hash já visto, mesmo que o
processamento anterior tenha falhado. Precisou de intervenção manual no banco pra desbloquear.

**Causa raiz:** nenhum fluxo de falha (cancelar, comprovante sem correspondência) apagava o
registro em `documentos` — só o botão "Cancelar" fazia `UPDATE status='cancelado'`, que não libera
o hash.

**Correção:** `_descartar_documento(doc_id)` apaga o registro E o arquivo em `data/uploads` (não
mexe em arquivo já arquivado no OneDrive). Chamado no botão "Cancelar" e quando comprovante PIX não
encontra nenhum candidato.

**Lição geral:** todo caminho de falha que termina sem gerar pedido/lançamento/parcela precisa
desfazer o `registrar()` inicial — senão o hash fica "gasto" para sempre e o usuário não consegue
corrigir e reenviar o mesmo arquivo. Ao criar um novo fluxo de documento, sempre perguntar: "se
isso falhar aqui, o arquivo fica destrancado pra tentar de novo?"

---

## 7. Dado já conhecido do fornecedor não era reaproveitado (PIX)

**Sintoma:** GGV03-003 é do mesmo fornecedor de GGV03-002 (DeltaD), mas o PIX veio "Não
identificada" mesmo já tendo sido extraído corretamente no pedido anterior.

**Causa raiz:** dupla — (a) `_resumo_gerar()` (a tela que o usuário vê antes de confirmar) nunca
chamava `buscar_fornecedor()`, só lia o texto bruto do documento novo; (b) `_criar_fornecedor_auto()`
nunca salvava `chave_pix` no cadastro, mesmo quando o Claude a encontrava — então nem existia o que
reaproveitar.

**Correção:** `_resumo_gerar()` agora consulta `buscar_fornecedor()` e usa CNPJ/PIX já cadastrados
como fallback. `gerar_pfm()` passou a persistir PIX no fornecedor (tanto no cadastro automático
quanto como backfill de um fornecedor já existente sem PIX salvo), no mesmo padrão que `ramo` já
usava.

**Lição geral:** todo dado que o Claude extrai e que faz sentido ser característica do fornecedor
(não do pedido específico) deveria ser persistido no cadastro na primeira vez que aparece —
senão cada pedido novo reextraí do zero, e o sistema nunca fica "mais esperto" com o uso.

---

## 8. Filtro de "campo vazio" só reconhecia a forma masculina

**Sintoma:** mesmo depois da correção do item 7, o PIX continuou aparecendo como texto literal
"Não identificada" na tela — o fallback pro fornecedor nunca era acionado.

**Causa raiz:** o conjunto de marcadores de "não encontrado" em `_campo()` tinha só "não
identificado" (masculino) — "Não identificada" (concordando com "chave", feminino) não batia,
então era tratado como um valor real e válido, não como ausência de dado.

**Correção:** `_campo_vazio()` — checagem por prefixo tolerante a gênero (`"não identificad"` sem a
vogal final) e a frases mais longas (`"não identificada no documento"`), não mais comparação exata
contra uma lista fixa.

**Lição geral:** qualquer lista de "valores que significam vazio" escrita à mão vai ficar
incompleta — o Claude varia gênero, frase e nível de detalhe. Preferir checagem por prefixo/
substring a comparação exata de string sempre que o valor vier de texto gerado por IA.

---

## 9. Matching de comprovante não reconhecia pagamento parcial

**Sintoma:** comprovante de R$2.500 (pagamento parcial de um pedido de R$30.000) voltou "Nenhum
pedido em aberto corresponde a este pagamento" e foi descartado — mesmo o pedido estando aberto.

**Causa raiz:** `buscar_candidatos_pix()` só pontuava valor exato (±R$0,01) ou próximo (±10%) do
valor **original** do lançamento — nunca considerava que o pagamento parcelado é o caso normal
(ver pagamento parcelado, Fiada de 2026-07-01), nem comparava contra o **saldo restante** depois de
parcelas já pagas.

**Correção:** a pontuação agora compara com `valor_lanc - _total_pago(pfm_codigo)` (saldo, não
valor cheio), e qualquer valor positivo menor que o saldo ganha pontuação mínima de candidato —
pagamento parcial deixou de ser um caso não tratado.

**Lição geral:** uma função escrita antes de um domínio novo existir (pagamento parcelado nasceu
depois do matching de comprovante original) precisa ser revisitada quando esse domínio chega —
não basta o novo domínio funcionar isoladamente, ele precisa ser considerado nos pontos de
integração antigos também.

---

## 10. Bloco de entrega do PDF ignorava o endereço real salvo

**Sintoma:** o Pedido de Compra sempre mostrava "Obra GGV03" como endereço de entrega, nunca o
endereço de verdade — mesmo quando ele já estava salvo no banco (`documentos.endereco_entrega`).

**Causa raiz:** `_gerar_html_pc()` montava o bloco de entrega com `[f"Obra {ggv}"]` fixo — a
variável com o endereço real (`end_db`) era lida do banco mas nunca usada nesse bloco específico.

**Correção:** usa o endereço real (do pedido, com fallback pro padrão da obra) e só cai pro texto
genérico "Obra {ggv}" se realmente não houver nenhum endereço conhecido. Complementar: novo
`_autopreencher_endereco()` já grava o endereço padrão da obra assim que o GGV é identificado, sem
precisar de clique manual.

**Lição geral:** ter o dado certo no banco não garante que a tela final o exibe — sempre conferir
se cada bloco de exibição realmente lê a variável que já foi buscada, em vez de assumir que "já
que carreguei o dado, algum lugar deve estar usando".

---

## 11. Unidade por extenso (palavra inteira, não abreviação) quebra o regex de item

**Sintoma:** item "1. Bloco cerâmico 9x14x24 cm (8000 blocos) — R$ 6.960,00" não teve o valor
unitário calculado — mesmo sintoma do item #3 (fallback de texto cru), mas causa diferente.

**Causa raiz:** o grupo de unidade do `ITEM_RE` (corrigido no item #3 para aceitar dígito/
superíndice) ainda limitava a **quantidade de letras** a `{1,4}` — cobre "UND", "M3", "KG", mas não
palavras por extenso que o Claude às vezes usa em vez de abreviação ("blocos", "sacos",
"unidades").

**Correção:** grupo de unidade ampliado para `[A-Za-zÀ-ÿ]{1,15}[²³0-9]{0,2}` — mesma estrutura do
item #3, só com limite de letras maior.

**Lição geral:** o item #3 já generalizava "unidade sem superíndice", mas a lição real era mais
ampla: o Claude não segue um vocabulário fixo de abreviações de unidade. Qualquer limite de
tamanho num regex de unidade extraída por IA deveria ser generoso por padrão (uma palavra inteira
razoável, não 3-4 caracteres), não ajustado reativamente cada vez que aparece uma palavra nova.
Confirmado contra o pedido real GGV03-010 (Cerâmica Tio Nardo, teste em 2026-07-02).

---

## 12. Marca/fabricante confundida com unidade de medida (lista de materiais)

**Sintoma:** item "Rejunte cinza ártico 5kg" de uma lista de materiais real (foto) voltou como
"(1 QUARTZOLIT)" em vez de "(1 SC)" — "Quartzolit" é marca, não unidade. Dennis reportou:
"unidade não é quartzolit, é sc".

**Causa raiz:** o PROMPT (tanto o `[lista_materiais]` do template compartilhado quanto
`PROMPT_INTERPRETAR_LISTA`, dedicado ao domínio de Compras) só dizia "formato: N. Descrição
(QTDE UND)" — sem nunca definir o que É uma unidade válida. Quando a marca aparece perto da
quantidade no texto/foto original, o Claude não tem nenhuma instrução que o impeça de tratá-la
como se fosse a unidade.

**Correção:** ambos os PROMPTs ganharam uma linha explícita: UND é sempre uma unidade de medida
real (lista de exemplos: kg, sc/saco, un, m, m², m³, L, cx, rolo, barra, pç); marca/fabricante
nunca vai nesse lugar — se aparecer perto da quantidade, deve ficar dentro da descrição.
Validado com 8 fraseados diferentes (marca antes/depois/no meio da quantidade, com e sem
abreviação de unidade) — todos corretos depois da correção; nenhum reproduzido exatamente
igual ao caso real do Dennis, mas a classe de erro é a mesma da Lição #1 (instrução implícita
não basta).

**Lição geral:** todo PROMPT que pede pra Claude extrair uma "unidade" de texto livre precisa
dizer explicitamente o que conta como unidade válida, não só o formato de onde ela vai. O
Claude vai preencher a posição sintaticamente certa com o token mais próximo disponível
(marca, adjetivo, o que for) se não houver uma regra semântica clara sobre o que pertence ali.

---

## Padrão geral por trás de tudo isso

Duas famílias de bug, não uma só.

**Família A (itens 1-6) — o código assume uma forma fixa de string vinda do Claude** (largura de
caractere, formato numérico americano, unidade só-letra, gênero gramatical, campo com nome exato)
— mas a extração por IA é inerentemente variável, principalmente em documentos que fogem do padrão
esperado (boleto em vez de orçamento, dia sem zero à esquerda, unidade sem superíndice, "Não
identificada" em vez de "Não identificado"). Regra prática: qualquer parser de valor/data/unidade
extraído pelo Claude deve ser feito com regex tolerante (`{1,2}` em vez de índice fixo) ou checagem
por prefixo (nunca comparação exata de string), nunca `string[a:b]` cru.

**Família B (itens 7, 9, 10) — o sistema não reaproveita o que já sabe.** Dado já cadastrado
(PIX do fornecedor), domínio novo que muda o significado de "correspondência" (pagamento
parcelado), ou variável já buscada do banco mas nunca usada na tela final — três formas do mesmo
problema: escrever uma tela/função nova sem revisitar o que já existe ao redor dela.

Regra prática comum às duas famílias: testar contra pelo menos um caso real de produção antes de
considerar corrigido — não só contra dado fictício. Foi assim que todos os 10 bugs acima foram
confirmados (lendo o PDF/imagem real ou consultando o banco de produção, não assumindo a partir do
sintoma).
