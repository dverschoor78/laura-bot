# Projeto Laura

Bot de Telegram local para gestão de compras, pagamentos e conciliação financeira de obras GGV.

**Status:** Fase 1 — Fundação (em desenvolvimento)

---

## O que é

O Laura recebe documentos pelo Telegram (fotos, PDFs, prints), extrai os dados com IA, pede confirmação e registra tudo de forma organizada. Elimina o lançamento manual no extrato Excel.

### Fluxos principais

| Você faz | Bot faz |
|---|---|
| Manda foto/PDF do orçamento | Extrai dados, gera PFM Word/PDF numerado, cria lançamento "A PAGAR" |
| Manda comprovante PIX | Extrai valor/data, vincula ao PFM, marca como "PAGO" |
| Manda extrato mensal do MP | Cruza com lançamentos, aponta divergências e pendências |

---

## Estrutura de pastas

```
01-Laura/
├── app/
│   ├── bot/handlers/     ← handlers do Telegram
│   ├── services/         ← lógica de negócio
│   ├── extractors/       ← Claude API e parsers
│   ├── db/               ← banco SQLite
│   └── utils/            ← utilitários
├── templates/            ← template Word do PFM
├── data/                 ← banco e uploads (no .gitignore)
├── logs/                 ← logs de runtime (no .gitignore)
├── tests/                ← testes automatizados
├── docs/                 ← documentação
└── scripts/              ← scripts de manutenção
```

---

## Instalação

Ver [docs/instalacao.md](docs/instalacao.md) para o guia completo passo a passo.

### Resumo rápido (após configurar a VM)

```bash
git clone https://github.com/SEU-USUARIO/laura-bot.git
cd laura-bot
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# editar .env com os valores reais
python scripts/migrate.py
python -m app.bot.main
```

---

## Comandos do bot

| Comando | Função |
|---|---|
| `/start` | Apresentação e status |
| `/pendentes` | Lista lançamentos A PAGAR |
| `/pfm GGV03-007` | Consulta um PFM específico |
| `/ajuda` | Lista de comandos |

Você também pode simplesmente **mandar uma foto ou PDF** diretamente — o bot detecta o tipo automaticamente.

---

## Stack técnica

| Componente | Biblioteca |
|---|---|
| Bot Telegram | python-telegram-bot v22 |
| IA / Visão | Claude API (Anthropic) |
| Banco de dados | SQLite (built-in) |
| Geração Word | docxtpl + python-docx |
| Conversão PDF | LibreOffice headless |
| Excel | openpyxl |
| Validação | Pydantic v2 |
| Logs | loguru |
| Testes | pytest + pytest-asyncio |

---

## Fases de desenvolvimento

- [x] **Fase 1 — Fundação:** VM + bot básico + recebe arquivos + SQLite + Claude extrai + confirmação
- [ ] **Fase 2 — PFM:** Gera Word numerado + PDF + salva no OneDrive + cria A PAGAR
- [ ] **Fase 3 — Pagamento:** Comprovante PIX + vincula ao PFM + marca PAGO
- [ ] **Fase 4 — Conciliação:** Extrato MP + cruzamento + relatório + exporta XLSX

---

## Segurança

- Bot aceita mensagens **apenas do seu Telegram ID** (configurado em `.env`)
- Nenhum dado financeiro é gravado sem **confirmação explícita**
- Banco SQLite e arquivos financeiros **nunca vão para o Git**
- Backup automático diário para o OneDrive

---

## Autor

Dennis Verschoor — [dennis@deltad.com.br](mailto:dennis@deltad.com.br)  
DeltaD Engenharia — Carambeí, PR
