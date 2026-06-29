# Roadmap do Projeto Laura

> Atualizado em: 2026-06-29

---

## Próxima Fiada

**Criar `docs/PROCESSO.md`**

Objetivo: formalizar o ciclo de trabalho do projeto — abertura de sessão,
planejamento da fiada, implementação, encerramento e checklists de qualidade.

Motivo: é o último documento da engenharia de desenvolvimento. Com ele concluído,
qualquer sessão futura (com qualquer IA) pode ser iniciada com contexto completo
e processo definido.

Critério de aceite: ao ler `docs/PROCESSO.md`, qualquer pessoa deve entender
como abrir uma sessão, como planejar e executar uma fiada, e o que fazer antes
de encerrar.

Tamanho esperado: Pequeno

---

## Próximas Fiadas

1. Marcar como PAGO — fechar o ciclo financeiro completo
2. PDF via LibreOffice headless
3. `pfm_revisar` — implementar revisão da PFM (botão existe, ação pendente)
4. `pfm_hist` — histórico completo do pedido (botão existe, ação pendente)
5. Corrigir BD fornecedores (MO Construção CNPJ, PRUDENTÓPOLIS split)

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
