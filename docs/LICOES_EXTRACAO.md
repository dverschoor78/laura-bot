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

## Padrão geral por trás de tudo isso

A maioria desses bugs tem a mesma forma: **o código assume uma forma fixa de string vinda do
Claude** (largura de caractere, formato numérico americano, unidade só-letra, campo com nome
exato) — mas a extração por IA é inerentemente variável, principalmente em documentos que fogem do
padrão esperado (boleto em vez de orçamento, dia sem zero à esquerda, unidade sem superíndice).

Regra prática: qualquer parser de valor/data/unidade extraído pelo Claude deve ser feito com regex
tolerante (`{1,2}` em vez de índice fixo), nunca `string[a:b]` cru, e testado contra pelo menos um
caso real de produção antes de considerar corrigido — não só contra dado fictício. Foi assim que
todos os 6 bugs acima foram confirmados (lendo o PDF/imagem real, não assumindo a partir do
sintoma).
