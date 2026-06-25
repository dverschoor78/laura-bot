# CHANGELOG

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versionamento baseado em [Semantic Versioning](https://semver.org/).

---

## [Não lançado]

### Próxima fiada
- Calcular hash SHA256 do arquivo (detectar duplicatas)

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
