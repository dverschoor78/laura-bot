-- ============================================================
-- Migration 001 — Schema inicial do Projeto Laura
-- 2026-06-25
-- ============================================================

-- Fornecedores conhecidos
-- Alimentado automaticamente quando Claude extrai dados de orçamentos
CREATE TABLE IF NOT EXISTS fornecedores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    razao_social    TEXT NOT NULL,
    cnpj_cpf        TEXT UNIQUE,            -- CNPJ ou CPF sem formatação: "77488385000889"
    ie              TEXT,
    logradouro      TEXT,
    numero          TEXT,
    bairro          TEXT,
    cidade          TEXT,
    uf              TEXT,
    cep             TEXT,
    contato         TEXT,
    email           TEXT,
    whatsapp        TEXT,
    criado_em       TEXT DEFAULT (datetime('now', 'localtime')),
    atualizado_em   TEXT
);

-- Documentos recebidos via Telegram (fotos, PDFs, CSVs)
-- Tabela central: todo arquivo passa por aqui primeiro
CREATE TABLE IF NOT EXISTS documentos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo                TEXT NOT NULL,      -- 'orcamento', 'comprovante', 'extrato_mp'
    nome_arquivo        TEXT,
    caminho_salvo       TEXT,
    hash_sha256         TEXT UNIQUE,        -- idempotência: evita processar o mesmo arquivo duas vezes
    telegram_file_id    TEXT,
    telegram_message_id INTEGER,
    status              TEXT DEFAULT 'recebido',  -- recebido | processando | confirmado | descartado
    dados_extraidos     TEXT,               -- JSON bruto retornado pelo Claude
    erro_extracao       TEXT,               -- descrição do erro, se houver
    processado_em       TEXT,
    criado_em           TEXT DEFAULT (datetime('now', 'localtime'))
);

-- PFMs (Pedidos de Fornecimento de Material/Serviço)
-- Cada PFM tem número sequencial por GGV: GGV03-001, GGV03-002...
CREATE TABLE IF NOT EXISTS pfms (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    numero              TEXT UNIQUE NOT NULL,    -- ex: 'GGV03-007'
    ggv                 TEXT NOT NULL,           -- ex: 'GGV03'
    fornecedor_id       INTEGER REFERENCES fornecedores(id),
    documento_id        INTEGER REFERENCES documentos(id),
    data_emissao        TEXT,
    prazo_entrega       TEXT,
    data_entrega        TEXT,
    condicao_pagamento  TEXT,
    observacoes         TEXT,
    valor_total         REAL,
    caminho_docx        TEXT,               -- caminho completo do arquivo Word gerado
    caminho_pdf         TEXT,               -- caminho completo do PDF gerado
    status              TEXT DEFAULT 'rascunho',  -- rascunho | confirmado | cancelado
    criado_em           TEXT DEFAULT (datetime('now', 'localtime'))
);

-- Itens de cada PFM (tabela de produtos/serviços)
CREATE TABLE IF NOT EXISTS pfm_itens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pfm_id          INTEGER NOT NULL REFERENCES pfms(id) ON DELETE CASCADE,
    ordem           INTEGER,            -- ordem na tabela (01, 02...)
    descricao       TEXT NOT NULL,
    unidade         TEXT,               -- m², m³, un, sc, kg, etc.
    quantidade      REAL,
    valor_unitario  REAL,
    valor_total     REAL
);

-- Lançamentos financeiros
-- Criados automaticamente quando PFM é confirmado (status=a_pagar)
-- Atualizados quando comprovante é confirmado (status=pago)
CREATE TABLE IF NOT EXISTS lancamentos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ggv             TEXT NOT NULL,          -- 'GGV03', 'GGV00', etc.
    categoria       TEXT,                   -- MATERIAL | SERVIÇOS | MO | TAXA | IMPOSTO | APORTE
    fonte           TEXT,                   -- quem fornece o recurso
    descricao       TEXT,
    fornecedor_id   INTEGER REFERENCES fornecedores(id),
    pfm_id          INTEGER REFERENCES pfms(id),
    forma_pgto      TEXT,                   -- pix | dinheiro | boleto
    tipo_doc        TEXT,                   -- NOTA | RECIBO | GUIA | FATURA | etc.
    valor_a_pagar   REAL,
    valor_pago      REAL,
    data_lancamento TEXT,
    data_vencimento TEXT,
    data_pagamento  TEXT,
    status          TEXT DEFAULT 'a_pagar', -- a_pagar | pago | cancelado
    exportado_xlsx  INTEGER DEFAULT 0,      -- 0=não exportado, 1=exportado para o extrato Excel
    criado_em       TEXT DEFAULT (datetime('now', 'localtime'))
);

-- Comprovantes de pagamento PIX vinculados a lançamentos
CREATE TABLE IF NOT EXISTS comprovantes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    lancamento_id       INTEGER REFERENCES lancamentos(id),
    documento_id        INTEGER REFERENCES documentos(id),
    valor               REAL,
    data_pagamento      TEXT,
    cnpj_cpf_destino    TEXT,
    nome_destino        TEXT,
    chave_pix           TEXT,
    id_transacao        TEXT UNIQUE,        -- ID único do PIX (idempotência)
    criado_em           TEXT DEFAULT (datetime('now', 'localtime'))
);

-- Transações do extrato bancário (Mercado Pago)
-- Carregadas mensalmente via CSV ou PDF
CREATE TABLE IF NOT EXISTS extrato_mp (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    mes_referencia  TEXT,               -- '2026-05'
    documento_id    INTEGER REFERENCES documentos(id),
    data_lancamento TEXT,
    tipo_transacao  TEXT,               -- 'Pix enviado', 'Pix recebido', etc.
    beneficiario    TEXT,
    valor           REAL,
    lancamento_id   INTEGER REFERENCES lancamentos(id),  -- NULL = não conciliado ainda
    status          TEXT DEFAULT 'pendente',  -- pendente | conciliado | ignorado
    criado_em       TEXT DEFAULT (datetime('now', 'localtime'))
);

-- Auditoria: registro imutável de toda ação crítica
-- Permite reconstruir o histórico completo
CREATE TABLE IF NOT EXISTS auditoria (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tabela          TEXT,               -- 'lancamentos', 'pfms', etc.
    registro_id     INTEGER,
    acao            TEXT,               -- 'criado' | 'confirmado' | 'cancelado' | 'exportado' | 'pago'
    dados_anteriores TEXT,              -- JSON do estado antes da ação
    dados_novos     TEXT,               -- JSON do estado depois da ação
    telegram_user_id TEXT,
    criado_em       TEXT DEFAULT (datetime('now', 'localtime'))
);

-- Controle de migrations executadas
CREATE TABLE IF NOT EXISTS _migrations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT UNIQUE NOT NULL,
    executado_em TEXT DEFAULT (datetime('now', 'localtime'))
);

INSERT OR IGNORE INTO _migrations (nome) VALUES ('001_initial');
