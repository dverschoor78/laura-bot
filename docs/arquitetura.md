# Arquitetura do Projeto Laura

> Versão 1.0 — 2026-06-25  
> Autor: Dennis Verschoor / Arquiteto: Claude (Anthropic)

---

## 1. Visão Geral

O Projeto Laura é um bot de Telegram local para gestão de compras, pagamentos e conciliação financeira de obras da série GGV, começando pelo GGV03.

**Problema que resolve:** Dennis precisa cadastrar manualmente cada compra, pagamento e conciliação no extrato Excel. Isso é lento, sujeito a erros e é o gargalo do processo.

**Solução:** Um bot Telegram que recebe documentos (fotos, PDFs, prints), extrai os dados com IA (Claude), pede confirmação humana e registra tudo de forma organizada.

---

## 2. Princípios Arquiteturais

### 2.1 Fundação primeiro

Assim como em uma obra de engenharia, cada fase deve estar completa e testada antes da próxima começar. O MVP faz poucas coisas, mas faz com total confiabilidade.

### 2.2 Confirmação humana obrigatória

**Nenhum dado financeiro é gravado sem confirmação explícita do usuário.** O bot sempre mostra o que vai fazer e aguarda aprovação com botões inline (✅ / ❌ / ✏️).

### 2.3 Idempotência

Todo arquivo recebido recebe um hash SHA256. Se o mesmo arquivo for enviado duas vezes, o bot detecta e avisa em vez de duplicar o lançamento. Isso previne erros por reenvio acidental.

### 2.4 Separação de responsabilidades

Cada módulo tem uma função clara e única:
- **bot/handlers**: fala com o Telegram, nada mais
- **services**: lógica de negócio (gerar PFM, registrar pagamento)
- **extractors**: extrair dados de documentos (Claude API)
- **db/queries**: acesso ao banco de dados
- **utils**: funções de suporte sem lógica de negócio

### 2.5 Logs de auditoria

Todo lançamento financeiro deixa rastro: quem confirmou, quando, o que foi gravado. Isso permite reconstruir o histórico em caso de dúvida.

---

## 3. Fluxos Principais

### Fluxo A — Geração de PFM

```
Dennis → [foto/PDF do orçamento] → Telegram
Telegram → bot recebe arquivo
bot → calcula hash SHA256 (verifica duplicata)
bot → salva arquivo em data/uploads/
bot → envia para Claude API com prompt estruturado
Claude → retorna JSON: {fornecedor, cnpj, itens, valor_total, condicoes}
bot → valida dados com Pydantic
bot → mostra preview formatado para Dennis
bot → aguarda confirmação (botões inline)
[Dennis confirma]
bot → detecta próximo número PFM (ex: GGV03-008)
bot → preenche template Word com docxtpl
bot → converte Word → PDF via LibreOffice headless
bot → salva arquivos em OneDrive/04 Aquisição e Execução/
bot → registra no SQLite: pfms + pfm_itens + lancamentos (status=a_pagar)
bot → registra auditoria
bot → envia PDF do PFM para Dennis no Telegram
```

### Fluxo B — Registro de Pagamento

```
Dennis → [foto do comprovante PIX] → Telegram
bot → hash + salva arquivo
bot → envia para Claude API
Claude → retorna JSON: {data, valor, cnpj_destino, nome_destino, id_transacao}
bot → busca no SQLite: lançamento A PAGAR com CNPJ + valor ≈ comprovante
bot → mostra: "Isso corresponde ao PFM GGV03-008. Confirmar pagamento?"
[Dennis confirma]
bot → atualiza lancamentos: status=pago, data_pagamento
bot → cria registro em comprovantes
bot → salva imagem do comprovante em OneDrive (pasta do GGV)
bot → registra auditoria
```

### Fluxo C — Conciliação Mensal

```
Dennis → [CSV ou PDF do Mercado Pago] → Telegram
bot → detecta tipo: CSV → parse direto; PDF → Claude extrai
bot → carrega todas as transações do mês
bot → cruza com lancamentos no SQLite (por valor + data ± 2 dias + CNPJ)
bot → gera relatório:
  ✅ X lançamentos conciliados
  ⚠️ Y divergências de valor
  ❓ Z transações do banco sem lançamento correspondente
  📋 W lançamentos no extrato sem transação bancária
bot → aguarda confirmação para marcar conciliados
```

---

## 4. Estrutura de Pastas

```
01-Laura/
├── app/
│   ├── __init__.py
│   ├── config.py              ← lê .env, constantes globais
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── main.py            ← inicializa Application, registra handlers
│   │   ├── keyboards.py       ← botões inline reutilizáveis
│   │   └── handlers/
│   │       ├── __init__.py
│   │       ├── start.py       ← /start, /ajuda
│   │       ├── documento.py   ← recebe foto/PDF (orçamento)
│   │       ├── comprovante.py ← recebe comprovante PIX
│   │       ├── extrato.py     ← recebe CSV/PDF extrato mensal
│   │       ├── consultas.py   ← /pendentes, /pfm
│   │       └── callbacks.py   ← responde botões inline (confirmar/cancelar)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pfm_service.py     ← gera PFM: numera, preenche template, salva
│   │   ├── pagamento_service.py ← registra comprovante, marca PAGO
│   │   ├── extrato_service.py ← conciliação com extrato do MP
│   │   └── arquivo_service.py ← salva/move arquivos no OneDrive
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── claude_extractor.py ← chama Claude API com imagem ou texto
│   │   ├── csv_extractor.py    ← faz parse do CSV do Mercado Pago
│   │   └── schemas.py          ← Pydantic: OrcamentoExtraido, ComprovanteExtraido
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py      ← get_connection() com context manager
│   │   ├── setup.py           ← cria tabelas se não existem
│   │   ├── migrations/
│   │   │   └── 001_initial.sql
│   │   └── queries/
│   │       ├── __init__.py
│   │       ├── fornecedores.py
│   │       ├── pfms.py
│   │       ├── lancamentos.py
│   │       └── documentos.py
│   └── utils/
│       ├── __init__.py
│       ├── formatters.py      ← formata moeda, data, CNPJ
│       ├── validators.py      ← valida CNPJ, valores
│       └── hasher.py          ← SHA256 de arquivos
├── templates/
│   └── PFM-template.docx      ← template com marcadores Jinja2
├── data/
│   ├── laura.db               ← SQLite (NO .gitignore)
│   └── uploads/               ← arquivos temporários (NO .gitignore)
├── logs/
│   └── .gitkeep
├── tests/
│   ├── __init__.py
│   ├── test_extractors.py
│   ├── test_services.py
│   ├── test_db.py
│   └── fixtures/
│       ├── orcamento_teste.pdf
│       └── comprovante_teste.jpg
├── docs/
│   ├── arquitetura.md         ← este arquivo
│   ├── instalacao.md
│   └── fluxos.md
├── scripts/
│   ├── setup_vm.sh            ← setup inicial da VM
│   ├── backup.sh              ← backup do SQLite
│   └── migrate.py             ← roda migrations do banco
├── .env                       ← secrets (NO .gitignore)
├── .env.example               ← template sem valores reais
├── .gitignore
├── pyproject.toml
├── README.md
└── CHANGELOG.md
```

---

## 5. Tecnologias e Justificativas

### 5.1 python-telegram-bot v21

**Por que:** Biblioteca oficial mais usada para bots Telegram em Python. Suporte nativo async, ConversationHandler para gerenciar estados de conversa, callbacks inline para botões.

**Alternativas descartadas:**
- `aiogram`: mais moderno e rápido, mas curva de aprendizado maior e documentação menos amigável para iniciantes
- `pyTelegramBotAPI (telebot)`: síncrono, menos robusto para produção

**Maturidade:** ~26.000 ⭐, mantido ativamente, versão estável.

### 5.2 Claude API (Anthropic)

**Por que:** Superior a OCR tradicional para documentos variados (fotos tortas, prints de tela, PDFs escaneados). Entende contexto, extrai campos estruturados, lida com variações de formato.

**Modelo:** `claude-haiku-4-5` para extração de documentos (mais barato, rápido). `claude-sonnet-4-6` reservado para casos complexos.

**Custo estimado:** Cada extração custa ~0,001 USD. 100 documentos/mês = ~R$ 0,50.

**Alternativas descartadas:**
- Tesseract OCR: gratuito mas exige pré-processamento pesado e perde qualidade em fotos ruins
- GPT-4 Vision: similar ao Claude, mas sem vantagem técnica e maior custo

### 5.3 docxtpl

**Por que:** Usa Jinja2 para preencher templates Word. Muito mais simples que manipular XML diretamente com python-docx. Basta marcar os campos no Word com `{{ campo }}` e preencher com um dicionário Python.

**Maturidade:** ~2.500 ⭐, estável.

**Alternativa:** `python-docx` puro — mais controle, muito mais verboso. Usar só se docxtpl não atender.

### 5.4 LibreOffice headless

**Por que:** Converte DOCX para PDF com fidelidade total ao layout. Gratuito, disponível no Ubuntu.

**Uso:** `libreoffice --headless --convert-to pdf arquivo.docx`

**Alternativas descartadas:**
- `weasyprint`: bom para HTML→PDF, não para DOCX
- `reportlab`: gera PDF do zero, muito mais complexo

### 5.5 openpyxl

**Por que:** Única biblioteca madura para ler e escrever `.xlsx` com fórmulas e formatação preservadas. É o padrão absoluto.

**Uso no projeto:** Leitura do extrato existente e, nas fases avançadas, escrita de novos lançamentos.

### 5.6 SQLite + sqlite3 (built-in)

**Por que:** Banco de dados local, sem servidor, arquivo único, backup trivial. Suficiente para o volume deste projeto (centenas de registros, não milhões).

**Migrations:** Scripts SQL puros em `db/migrations/`. Simples, sem dependência extra.

**Alternativas descartadas:**
- PostgreSQL: overkill, requer servidor separado
- SQLAlchemy ORM: poderoso mas adiciona complexidade desnecessária para iniciantes
- Peewee: ORM simples mas uma dependência a mais sem ganho real

### 5.7 Pydantic v2

**Por que:** Valida os dados extraídos pelo Claude antes de usar. Se o Claude retornar um campo inválido, o Pydantic captura o erro antes de chegar ao banco. Documentação clara, padrão da indústria Python.

**Maturidade:** ~21.000 ⭐, mantido pela equipe core do Python.

### 5.8 loguru

**Por que:** Substitui o módulo `logging` padrão com uma API muito mais simples. Uma linha para configurar, rotação automática de arquivos, cores no terminal, captura automática de exceções.

**Maturidade:** ~20.000 ⭐, estável.

**Alternativa:** `logging` built-in — funciona, mas requer mais configuração.

### 5.9 pdfplumber

**Por que:** Extrai texto de PDFs que já têm texto embutido (não escaneados). Usar como pré-processamento antes do Claude quando o PDF tem texto real — reduz custo da API.

**Lógica:** tenta pdfplumber primeiro; se texto vazio ou ruim, envia para Claude com visão.

**Maturidade:** ~6.500 ⭐, ativo.

### 5.10 pytest

**Por que:** Padrão absoluto para testes em Python. Simples de escrever, excelente output.

**Complementos:** `pytest-asyncio` para testar handlers assíncronos.

---

## 6. Segurança

### O que nunca vai para o Git
- Token do Telegram Bot
- Chave da Claude API  
- Arquivo `.env` com qualquer valor real
- Banco SQLite (`data/laura.db`)
- Arquivos financeiros (PDFs, CSVs, fotos de comprovantes)
- Pasta `data/uploads/`

### Controle de acesso ao bot
O bot só aceita mensagens do seu `TELEGRAM_USER_ID`. Qualquer outro usuário recebe: "Acesso não autorizado."

### Dados financeiros nos logs
Logs de auditoria registram ações, não valores completos. Ex: "Lançamento #42 confirmado" em vez de "Pagamento R$ 4.904,69 para CNPJ 77.488.385".

### Backup automático
Script `scripts/backup.sh` roda via cron diariamente:
- Copia `data/laura.db` para pasta de backup no OneDrive
- Mantém últimas 30 versões
- Nome: `laura-backup-YYYY-MM-DD.db`

---

## 7. Tratamento de Erros

### Hierarquia de erros

```
LauraBotError (base)
├── ExtractionError        ← Claude não conseguiu extrair dados
├── ValidationError        ← dados extraídos inválidos (Pydantic)
├── DatabaseError          ← erro ao gravar no SQLite
├── FileError              ← erro ao salvar arquivo no OneDrive
└── DuplicateDocumentError ← arquivo já processado (hash repetido)
```

### Comportamento em produção
- Erro de extração: bot avisa Dennis e pede para reenviar o arquivo
- Erro de banco: bot avisa, registra no log, não perde o arquivo
- Erro de arquivo: bot avisa, dados ficam no SQLite mesmo sem o arquivo
- Duplicata: bot avisa sem travar ("Este arquivo já foi processado em DD/MM")

---

## 8. Fases de Desenvolvimento

| Fase | Escopo | Critério de conclusão |
|------|--------|----------------------|
| **1 — Fundação** | VM + bot básico + recebe arquivos + SQLite + Claude extrai + confirmação | Bot responde, salva arquivo, mostra extração, pede confirmação |
| **2 — PFM** | Gera Word numerado + PDF + salva no OneDrive + cria A PAGAR | Dennis recebe PDF do PFM no Telegram |
| **3 — Pagamento** | Recebe comprovante PIX + vincula ao PFM + marca PAGO | Extrato SQLite atualizado corretamente |
| **4 — Conciliação** | Processa extrato MP + cruzamento + relatório + exporta para XLSX | Relatório mensal gerado com divergências apontadas |

---

## 9. Decisões Pendentes (ADRs)

| Decisão | Opções | Status |
|---------|--------|--------|
| Montar OneDrive via SMB ou rclone | SMB (simples) vs rclone (mais robusto) | **SMB** — Windows já compartilha, VM acessa |
| Modelo Claude para extração | haiku vs sonnet | **haiku** para padrão, sonnet via flag se falhar |
| Estado de conversa | Em memória (dict) vs Redis | **Em memória** — usuário único, sem necessidade de persistência |
| Geração de PDF | LibreOffice vs outro | **LibreOffice** headless — já disponível no Ubuntu |
