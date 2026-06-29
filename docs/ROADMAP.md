# Roadmap do Projeto Laura

> Atualizado em: 2026-06-29

---

## Próxima Fiada

**Apresentação Profissional do Pedido**

Objetivo: redesenhar a identidade visual do Pedido de Compra gerado pela Laura,
mantendo todas as regras de negócio existentes.

Escopo:
- Novo layout do DOCX — hierarquia visual mais clara, leitura rápida, impressão A4 adequada
- Aparência moderna que reflita um Pedido de Compra profissional pronto para circular
- Preparação para conversão em PDF
- Geração automática de PDF via LibreOffice headless após o DOCX ser gerado
- Ambos (Word e PDF) salvos na pasta do GGV e enviados pelo Telegram

Motivo: o documento atual foi construído para validar o fluxo de dados. Está na hora
de cuidar da apresentação para que o Pedido de Compra possa circular com a cara da DeltaD.
O PDF é consequência natural dessa melhoria, não o objetivo principal.

Critério de aceite: ao gerar um pedido, a Laura cria um DOCX visualmente profissional
e também gera o PDF correspondente. Ambos são salvos na pasta do GGV e enviados pelo Telegram.

Tamanho esperado: Médio — envolve design do documento e conversão para PDF.

Nota de linguagem: a partir desta fiada, a interface com o usuário passa a usar termos
mais naturais — Pedido de Compra, Pedido em Word, Pedido em PDF, Financeiro, Entrega.
O termo PFM continua existindo internamente no código e no banco.

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
