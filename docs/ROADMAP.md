# Roadmap do Projeto Laura

> Atualizado em: 2026-06-29

---

## Próxima Fiada

**Design System**

Objetivo: traduzir a identidade definida em `docs/IDENTIDADE_DO_PRODUTO.md` em
componentes concretos de design — antes de qualquer implementação visual.

Escopo:
- Voz e linguagem: biblioteca de mensagens do Telegram (recebimento, status, confirmação, erro)
- Sistema de status visual: uso consistente de 🟡 🟢 🔴 ⚫ ⚪ em toda a experiência
- Estrutura de mensagem: hierarquia, separadores, botões, padrões por tipo de tela
- Identidade do Pedido de Compra: layout, tipografia, hierarquia, cor, blocos de conteúdo
- Definição: PDF como artefato canônico, Word como saída secundária

Motivo: a identidade do produto foi definida na Sprint de Produto (2026-06-29).
O Design System é a tradução dessa identidade em componentes reutilizáveis.
A implementação da Apresentação Profissional do Pedido nasce deste Design System.

Critério de aceite: ao final da fiada, qualquer decisão visual (cor, layout, texto de botão,
estrutura de mensagem) tem uma resposta no Design System — não depende de julgamento
caso a caso.

Tamanho esperado: Médio — sem código, mas com definições exaustivas que guiarão
toda implementação visual futura.

Referência obrigatória: `docs/IDENTIDADE_DO_PRODUTO.md`

---

## Fiada Seguinte

**Apresentação Profissional do Pedido**

Objetivo: implementar o Design System no documento gerado pela Laura.

Escopo:
- Novo layout do DOCX baseado no Design System aprovado
- Geração automática de PDF via LibreOffice headless
- PDF como output primário enviado pelo Telegram; Word como alternativa
- Ambos salvos na pasta do GGV
- Linguagem da interface atualizada: PFM → Pedido de Compra em todas as mensagens

Critério de aceite: ao gerar um pedido, a Laura produz um PDF visualmente profissional
e o envia pelo Telegram. O Word é gerado e salvo como saída secundária.

Tamanho esperado: Médio — implementação guiada pelo Design System já aprovado.

---

## Próximas Fiadas

1. Revisão do Pedido de Compra — `pfm_revisar` (botão existe, ação pendente)
2. Histórico do Pedido — `pfm_hist` (botão existe, ação pendente)
3. Corrigir BD fornecedores (MO Construção CNPJ, PRUDENTÓPOLIS split)
4. `pfm_caminho` como coluna no banco — eliminar reconstrução de path

---

## Dívida Técnica

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
