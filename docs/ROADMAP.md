# Roadmap do Projeto Laura

> Atualizado em: 2026-06-29

---

## Próxima Fiada

**Marcar como PAGO**

Objetivo: com a lista de candidatos já exibida, adicionar botões de confirmação
ao resultado do comprovante. Ao confirmar, gravar `status='pago'` no lançamento
escolhido e registrar valor pago, data de pagamento e vínculo com o comprovante.

Motivo: a base de identificação de candidatos está pronta. Esta fiada fecha o
ciclo financeiro — o pagamento acontece e o banco sabe.

Critério de aceite: Dennis confirma o candidato → `lancamentos.status` atualizado
para `pago` → consultar o pedido mostra "🟢 PAGO".

Tamanho esperado: Pequeno (a fundação já existe).

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

- **Média — `mime_type` não gravado no banco**
  Inferido pela extensão do arquivo ao reprocessar.
  Justificativa: funciona para o MVP; pode falhar para arquivos sem extensão clara.

- **Baixa — `bot.py` monolítico com ~1584 linhas**
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
