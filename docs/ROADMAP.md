# Roadmap do Projeto Laura

> Atualizado em: 2026-06-29

---

## Em Andamento

**Fase 2 — Estrutura** *(Sprint de Experiência)*

Tela de validação do orçamento redesenhada com layout em 6 blocos orientado pela
sequência mental do engenheiro civil: Obra → Fornecedor → Itens → Valor → Condições → Logística.

Implementado nesta fase:
- `_resumo_gerar()` reescrita com layout aprovado e parse_mode HTML
- `teclado_orcamento()` unificado — condicionado ao estado da obra
- Campos `vencimento_pgto` e `encarregado` adicionados ao banco e à interface
- `GGV_ENCARREGADO` dict — padrão por obra, substituível por documento
- Botão "Conferir itens" removido — itens visíveis diretamente na tela de validação
- `DELTAD["ie"] = "Isento"` adicionado para uso no Pedido de Compra
- Botões Voltar em `sel_ggv`, `teclado_condicao`, `teclado_endereco`

Pendente nesta fase:
- Saldo do GGV na tela de pedido criado
- Saldo restante da obra na tela de pagamento confirmado
- Cartão do pedido com histórico resumido

---

## Fases Seguintes — Sprint de Experiência

**Fase 2 — Estrutura de mensagens**
- Tela de extração: fornecedor e valor em destaque na primeira linha
- Tela de pedido criado: incluir saldo atualizado do GGV
- Tela de pagamento confirmado: incluir saldo restante da obra
- Cartão do pedido: histórico resumido (criado em, pago em)
- Erros: sempre com próximo passo — nunca mensagens genéricas

**Fase 3 — Navegação e visões**
- Digitar "GGV03" → Cockpit da Obra (novo)
- Digitar nome de fornecedor → cartão do fornecedor (novo)
- /pendentes: lista por obra, vencidos destacados com ⚠️
- Tela de correção campo a campo (refatorado de "editar" para "corrigir")

**Fase 4 — Pedido de Compra**
- Novo layout DOCX: sete zonas definidas na Sprint de Experiência
- PDF gerado automaticamente via LibreOffice headless
- PDF como output primário no Telegram; Word salvo no OneDrive
- Cabeçalho repetido em documentos multipágina

---

## Próximas Fiadas

1. Revisão do Pedido de Compra — `pfm_revisar` (botão existe, ação pendente)
2. Histórico do Pedido — `pfm_hist` (botão existe, ação pendente)
3. Corrigir BD fornecedores (MO Construção CNPJ, PRUDENTÓPOLIS split)
4. `pfm_caminho` como coluna no banco — eliminar reconstrução de path

---

## Dívida Técnica

- **CRÍTICA — Renomear GGV → Obra no código e banco**
  Preocupação principal é no código: variáveis (`ggv`, `GGVS`, `GGV_DESC`, `GGV_ONEDRIVE`),
  coluna do banco (`ggv`), e string values internos devem migrar para `obra`/`OBRAS`.
  Na interface: "GGV03" deve aparecer como "Obra GGV03" (código como referência, não nome).
  Escopo: refatoração abrangente — variáveis Python, coluna banco, possivelmente pfm_codigo.
  Registrado em: 2026-06-29. Não implementar até decisão sobre pfm_codigo e arquivos existentes.

- **Alta — BD fornecedores inconsistente**
  MO Construção com CNPJ errado; PRUDENTÓPOLIS com split incorreto.
  Justificativa: dados incorretos afetam a busca de fornecedores em cada geração de PFM.

- **Média — `gerar_pfm()` acumula responsabilidades**
  Mistura geração Word, gravação no banco e criação de lançamento.
  Justificativa: dificulta testes e futuras extensões.

- **Média — `pfm_caminho` não existe como coluna**
  O caminho do arquivo é reconstruído a cada consulta.
  Justificativa: risco de inconsistência se a estrutura de pastas mudar.

- **Média — `mime_type` não gravado no banco**
  Inferido pela extensão do arquivo ao reprocessar.
  Justificativa: funciona para o MVP; pode falhar para arquivos sem extensão clara.

- **Baixa — deduplicação de comprovante incompleta**
  Se o Claude não extrair `ID da transação`, a proteção por identificador não atua.
  Justificativa: afeta apenas comprovantes sem número de transação visível; raro no MP.

- **Baixa — `bot.py` monolítico com ~1705 linhas**
  Aceitável até ~2000 linhas.
  Justificativa: monólito é decisão consciente — registrado na ADR-001.

---

## Ideias Futuras

- Conciliação com extrato Mercado Pago
- Relatório mensal por GGV
- Exportação XLSX dos lançamentos
- `/pendentes` com filtros por GGV e período
- Backup automático do banco via cron
- Sugestão automática de tipo de documento ("Sugerir automaticamente")
