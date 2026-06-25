# CHANGELOG

Todas as mudanças relevantes deste projeto serão documentadas neste arquivo.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versionamento baseado em [Semantic Versioning](https://semver.org/).

---

## [Não lançado]

### Próxima fiada
- Fiada 8: gerar documento Word do PFM com docxtpl (numeração GGV03-XXX)

---

## [0.0.7] — 2026-06-25

### Fiada 7 — Coleta de dados do PFM
- Ao confirmar orçamento, bot entra em fluxo de coleta de dados para PFM
- Condição de pagamento via botões: 💰 PIX à vista | 💰 PIX 50%+50% | ✏️ Outro (digitado)
- Endereço de entrega via botões: 🏗 Obra (GGV) | 🏠 Casa | 🏢 Escritório | 🌳 Chácara | ✏️ Outro
- Endereços conhecidos hardcoded: GGV01/02/03 (Rua Índia), Casa, Escritório, Chácara
- Opção "Outro" em qualquer campo ativa entrada de texto livre pelo usuário
- Novo handler `receber_texto` processa respostas textuais em contexto (aguardando)
- Estado temporário salvo em `ctx.user_data` (doc_id, ggv, aguardando, condicao_pgto)
- Colunas `condicao_pgto` e `endereco_entrega` adicionadas ao banco com ALTER TABLE seguro
- Status do documento muda para `pronto_pfm` ao completar a coleta
- Exibe resumo final: GGV, pagamento e endereço confirmados

---

## [0.0.6] — 2026-06-25

### Fiada 6 — Classificação + GGV + Confirmação
- Claude classifica o documento: orçamento, comprovante PIX, extrato MP ou não relacionado
- Claude identifica o GGV pelo conteúdo (matrícula, endereço, número do pedido)
- Botões: ✅ Confirmar | 🔄 Tipo | 🏗 GGV | ❌ Cancelar
- Reclassificação manual de tipo e GGV via botões inline
- Bloqueio: não permite confirmar sem GGV definido (alerta popup)
- Rejeição de formatos não suportados (Excel, Word) com mensagem clara
- tipo e ggv salvos no banco SQLite

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
