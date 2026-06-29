# Roadmap do Projeto Laura

> Atualizado em: 2026-06-29

---

## Próxima Fiada

**Marcar como PAGO**

Objetivo: ao receber um comprovante PIX, o bot vincula ao lançamento correto
e atualiza o status para PAGO, fechando o ciclo financeiro.

Motivo: é o próximo passo natural após a geração do PFM. Sem isso, o fluxo
termina aberto — o pagamento acontece, mas o banco não sabe.

Critério de aceite: Dennis envia foto de comprovante PIX → bot identifica fornecedor
e valor → exibe o lançamento correspondente → Dennis confirma → status atualizado
para PAGO no banco.

Tamanho esperado: Médio

---

## Próximas Fiadas

1. PDF via LibreOffice headless
2. `pfm_revisar` — implementar revisão da PFM (botão existe, ação pendente)
3. `pfm_hist` — histórico completo do pedido (botão existe, ação pendente)
4. Corrigir BD fornecedores (MO Construção CNPJ, PRUDENTÓPOLIS split)
5. `pfm_caminho` como coluna no banco — eliminar reconstrução de path

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

- **Baixa — `bot.py` monolítico com 1418 linhas**
  Aceitável até ~2000 linhas.
  Justificativa: monólito é decisão consciente — será registrado na ADR-001.

---

## Ideias Futuras

- Conciliação com extrato Mercado Pago
- Relatório mensal por GGV
- Exportação XLSX dos lançamentos
- `/pendentes` com filtros por GGV e período
- Backup automático do banco via cron
