# Roadmap do Projeto Laura

> Atualizado em: 2026-06-29

---

## Próxima Fiada

**Atualizar `docs/ARQUITETURA.md`**

Objetivo: atualizar o documento de arquitetura para refletir a realidade atual do projeto.

Motivo: o documento atual descreve uma estrutura modular que não existe. O sistema
funciona como monólito em `bot.py`, com SQLite, Claude API, Telegram e OneDrive.
A documentação precisa refletir o que existe, não a arquitetura idealizada.

Critério de aceite: ao ler `docs/ARQUITETURA.md`, qualquer pessoa deve entender
o que a Laura faz hoje, quais tecnologias estão em uso, qual é a arquitetura real,
quais tabelas existem no banco, quais fluxos principais funcionam e quais limitações
arquiteturais são conhecidas.

Tamanho esperado: Pequeno

---

## Próximas Fiadas

1. Criar `docs/decisoes/ADR-001-monolito-vs-modulos.md`
2. Criar `docs/PROCESSO.md`
3. Marcar como PAGO — fechar o ciclo financeiro completo
4. PDF via LibreOffice headless
5. `pfm_revisar` — implementar revisão da PFM (botão existe, ação pendente)

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
