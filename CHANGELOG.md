# CHANGELOG

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versionamento baseado em [Semantic Versioning](https://semver.org/).

---

## [Não lançado]

### Próxima fiada
- Pedir confirmação antes de gravar (botões ✅ / ❌)

---

## [0.0.5] — 2026-06-25

### Fiada 5 — Claude lê o documento
- Após salvar, envia o arquivo para Claude (haiku-4-5)
- Extrai: tipo, fornecedor, CNPJ, itens, valor total, condição de pagamento, observações
- Exibe resultado no Telegram antes de qualquer gravação
- Funciona com foto (JPEG) e PDF

---

## [0.0.4] — 2026-06-25

### Fiada 4 — SQLite
- Cria banco `data/laura.db` automaticamente na inicialização
- Registra cada arquivo recebido: nome, caminho, hash, status, data
- Detecção de duplicatas persiste entre reinicializações do bot

---

## [0.0.3] — 2026-06-25

### Fiada 3 — hash SHA256
- Calcula impressão digital do arquivo antes de salvar
- Detecta duplicatas em memória durante a sessão
- Arquivo duplicado: avisa e ignora em vez de salvar duas vezes
- Exibe os primeiros 16 caracteres do hash na confirmação

---

## [0.0.2] — 2026-06-25

### Fiada 2 — bot salva arquivos
- Recebe foto → salva como `YYYYMMDD_HHMMSS.jpg` em `data/uploads/`
- Recebe PDF/documento → salva com timestamp + nome original
- Responde confirmando o nome do arquivo salvo
- Cria a pasta `data/uploads/` automaticamente se não existir

---

## [0.0.1] — 2026-06-25

### Fiada 1 — Bot online
- `bot.py` mínimo: /start responde "Estou online.", qualquer outra mensagem responde "Recebi."
- Segurança: só aceita mensagens do TELEGRAM_USER_ID configurado no .env
- Repositório privado criado no GitHub (dverschoor78/laura-bot)
- Primeiro commit versionado e push realizado

---

## [0.0.0] — 2026-06-25

### Adicionado
- Estrutura inicial do projeto
- Documentação de arquitetura (`docs/arquitetura.md`)
- Guia de instalação (`docs/instalacao.md`)
- Schema do banco SQLite (`app/db/migrations/001_initial.sql`)
- Script de migrations (`scripts/migrate.py`)
- Script de backup (`scripts/backup.sh`)
- `.gitignore` configurado
- `.env.example` com todas as variáveis necessárias
- `pyproject.toml` com dependências
- `README.md`
