import os
import re
import hashlib
import sqlite3
import base64
import anthropic
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

load_dotenv()
TOKEN       = os.environ["TELEGRAM_BOT_TOKEN"]
DONO_ID     = int(os.environ["TELEGRAM_USER_ID"])
CLAUDE_KEY  = os.environ["CLAUDE_API_KEY"]
UPLOADS     = Path("data/uploads")
DB_PATH     = Path("data/laura.db")
UPLOADS.mkdir(parents=True, exist_ok=True)

claude = anthropic.Anthropic(api_key=CLAUDE_KEY)

TIPOS = {
    "orcamento":        ("📋", "Orçamento"),
    "comprovante_pix":  ("💰", "Comprovante PIX"),
    "extrato_mp":       ("🏦", "Extrato MP"),
    "nao_relacionado":  ("🗑", "Não é da obra"),
}
GGVS = ["GGV00", "GGV01", "GGV02", "GGV03"]

MESES = ["janeiro","fevereiro","março","abril","maio","junho",
         "julho","agosto","setembro","outubro","novembro","dezembro"]

DELTAD = {
    "nome":  "Verschoor Investimentos Imobiliários Ltda",
    "cnpj":  "58.358.802/0001-58",
    "end":   "Av. dos Pioneiros, 1380 – Centro – Carambeí/PR – CEP 84.145-000",
    "email": "dennis@deltad.com.br",
    "fone":  "(42) 99127-1255",
}
DELTAD_CNPJ_DIGITS = re.sub(r"\D", "", DELTAD["cnpj"])  # "58358802000158"

GGV_DESC = {
    "GGV01": "GGV01 — Matrícula 39.333, Quadra 05 Lote 02, JD das Nações, Carambeí-PR",
    "GGV02": "GGV02 — Matrícula 39.337, Quadra 05 Lote 06, JD das Nações, Carambeí-PR",
    "GGV03": "GGV03 — Matrícula 39.339, Quadra 05 Lote 08, JD das Nações, Carambeí-PR",
    "GGV00": "GGV00 — Despesas Gerais",
}

GGV_ONEDRIVE = {
    "GGV03": Path(r"C:\Users\denni\OneDrive\00 Obras\2026-06 GGV03\04 Aquisição e Execução"),
}

CONDICOES = {
    "pix_avista":  "PIX à vista",
    "pix_50_50":   "PIX 50% entrada + 50% na entrega",
}

ENDERECOS = {
    "obra_GGV01": "Rua Índia em frente ao nº139, Loteamento JD das Nações - Carambeí-PR CEP 84.145-000",
    "obra_GGV02": "Rua Índia em frente ao nº139, Loteamento JD das Nações - Carambeí-PR CEP 84.145-000",
    "obra_GGV03": "Rua Índia em frente ao nº139, Loteamento JD das Nações - Carambeí-PR CEP 84.145-000",
    "casa":        "Avenida dos Pioneiros, fundos Frederica's Coffie Huis - Carambeí-PR CEP 84.145-000",
    "escritorio":  "Avenida dos Pioneiros, 1380 - Carambeí-PR CEP 84.145-000",
    "chacara":     "Avenida dos Pioneiros, 5125 - Carambeí-PR CEP 84.145-000",
}

PROMPT = """
Você recebeu um arquivo enviado para um sistema de gestão de obras de construção civil.

PASSO 1 — Classifique o documento:
[orcamento]        — cotação, orçamento, pedido de compra, lista de materiais com preços
[comprovante_pix]  — comprovante de pagamento PIX ou transferência bancária
[extrato_mp]       — extrato do Mercado Pago ou extrato bancário
[nao_relacionado]  — qualquer outro documento não relacionado a obras

PASSO 2 — Identifique o empreendimento (GGV):
GGV01 — Matrícula 39.333, Quadra 05 Lote 02
GGV02 — Matrícula 39.337, Quadra 05 Lote 06
GGV03 — Matrícula 39.339, Quadra 05 Lote 08
GGV00 — despesas gerais compartilhadas
nao_identificado — se não conseguir determinar

PASSO 3 — Extraia os dados em português conforme o tipo:

Se [orcamento]:
- Fornecedor:
- CNPJ/CPF:
- Chave PIX: (procure em qualquer parte do documento — dados cadastrais, cabeçalho, rodapé, condições de pagamento; pode ser CPF, CNPJ, e-mail ou telefone)
- Itens (formato: N. Descrição do produto (QTDE UND) — R$ TOTAL; liste todos os itens do orçamento):
- Valor total:
- Desconto (valor em R$, se houver; se informado em %, calcule o valor sobre o total):
- Condição de pagamento:
- Prazo de entrega: (lead time ou data de entrega do material — NÃO a validade da proposta)
- Validade da proposta: (data até quando o preço é válido)
- Observações:

Se [comprovante_pix]:
- Data do pagamento:
- Valor:
- Destinatário:
- CNPJ/CPF do destinatário:
- Chave PIX:

Se [extrato_mp]:
- Período:
- Número de transações identificadas:
- Resumo:

Se [nao_relacionado]:
- Descreva brevemente o que é o documento.

Responda EXATAMENTE neste formato (sem colchetes, sem barra, escolha um valor de cada):
TIPO:orcamento
GGV:GGV03

Valores aceitos para TIPO: orcamento, comprovante_pix, extrato_mp, nao_relacionado
Valores aceitos para GGV: GGV00, GGV01, GGV02, GGV03, nao_identificado

Em seguida, os dados extraídos conforme o tipo identificado acima.
"""

# ── Banco ──────────────────────────────────────────────────────────────────

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS documentos (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                nome             TEXT,
                caminho          TEXT,
                hash             TEXT UNIQUE,
                tipo             TEXT DEFAULT 'desconhecido',
                ggv              TEXT DEFAULT 'nao_identificado',
                dados_claude     TEXT,
                condicao_pgto    TEXT,
                data_entrega     TEXT,
                endereco_entrega TEXT,
                desconto_rs      TEXT,
                pfm_numero       INTEGER,
                status           TEXT DEFAULT 'recebido',
                criado_em        TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        for col in ["tipo", "ggv", "dados_claude", "condicao_pgto", "data_entrega", "endereco_entrega", "desconto_rs TEXT", "pfm_numero INTEGER"]:
            try:
                con.execute(f"ALTER TABLE documentos ADD COLUMN {col}")
            except Exception:
                pass
        con.execute("""
            CREATE TABLE IF NOT EXISTS lancamentos (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id                INTEGER NOT NULL,
                pfm_codigo            TEXT NOT NULL UNIQUE,
                ggv                   TEXT,
                fornecedor            TEXT,
                valor                 REAL,
                data_prevista_entrega TEXT,
                vencimento_pagamento  TEXT,
                status                TEXT DEFAULT 'a_pagar',
                criado_em             TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS fornecedores (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                nome         TEXT NOT NULL,
                razao_social TEXT,
                cnpj         TEXT,
                cpf          TEXT,
                chave_pix    TEXT,
                email        TEXT,
                whatsapp     TEXT,
                contato      TEXT,
                logradouro   TEXT,
                numero       TEXT,
                bairro       TEXT,
                cidade       TEXT,
                uf           TEXT,
                cep          TEXT,
                origem       TEXT,
                criado_em    TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(cnpj),
                UNIQUE(cpf)
            )
        """)

def ja_existe(hash_arquivo):
    with sqlite3.connect(DB_PATH) as con:
        return con.execute("SELECT id FROM documentos WHERE hash = ?", (hash_arquivo,)).fetchone()

def registrar(nome, caminho, hash_arquivo, tipo, ggv, dados_claude):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "INSERT INTO documentos (nome, caminho, hash, tipo, ggv, dados_claude) VALUES (?,?,?,?,?,?)",
            (nome, str(caminho), hash_arquivo, tipo, ggv, dados_claude)
        )
        return cur.lastrowid

def atualizar(doc_id, **campos):
    sets = ", ".join(f"{k}=?" for k in campos)
    with sqlite3.connect(DB_PATH) as con:
        con.execute(f"UPDATE documentos SET {sets} WHERE id=?", (*campos.values(), doc_id))

def registrar_lancamento(doc_id, pfm_codigo, ggv, fornecedor, valor_v, data_entrega):
    """Insere lançamento A PAGAR. Idempotente: se pfm_codigo já existe, retorna o existente."""
    forn_ok  = fornecedor and fornecedor != "A PREENCHER"
    valor_ok = valor_v and valor_v > 0
    status   = "a_pagar" if (forn_ok and valor_ok) else "pendente_revisao"
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            """INSERT OR IGNORE INTO lancamentos
               (doc_id, pfm_codigo, ggv, fornecedor, valor, data_prevista_entrega, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (doc_id, pfm_codigo, ggv, fornecedor, valor_v, data_entrega, status)
        )
        ja_existia = cur.rowcount == 0
        if ja_existia:
            row = con.execute(
                "SELECT status FROM lancamentos WHERE pfm_codigo=?", (pfm_codigo,)
            ).fetchone()
            status = row[0] if row else status
    return status, ja_existia

def _dados_doc(doc_id):
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT dados_claude FROM documentos WHERE id=?", (doc_id,)).fetchone()
    return row[0] if row else ""

_CAMPOS_RESUMO_RE = re.compile(
    r"^\s*-\s*\*{0,2}(Desconto|Condição de pagamento|Prazo de entrega|Data.prazo de entrega)\b",
    re.IGNORECASE
)

def _dados_display(dados):
    """Remove do texto do Claude os campos que já aparecem no bloco de resumo."""
    linhas = [l for l in dados.split('\n') if not _CAMPOS_RESUMO_RE.match(l)]
    return '\n'.join(linhas).strip()

def _resumo_gerar(doc_id):
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT dados_claude, tipo, ggv, condicao_pgto, data_entrega, endereco_entrega, desconto_rs FROM documentos WHERE id=?",
            (doc_id,)
        ).fetchone()
    if not row:
        return "❌ Documento não encontrado.", None
    dados, tipo, ggv, condicao, data_ent, endereco, desconto_rs = row
    emoji, label_tipo = TIPOS.get(tipo, ("📄", tipo))
    label_ggv = ggv if ggv != "nao_identificado" else "❓ GGV não identificado"
    linhas_resumo = [
        f"💰 {condicao}"  if condicao  else "💰 Condição de pgto: não informada",
        f"📅 {data_ent}"  if data_ent  else "📅 Data de entrega: não informada",
        f"📍 {endereco}"  if endereco  else "📍 Endereço: não informado",
    ]
    subtotal_v, desconto_v, total_final_v = _calcular_totais(dados, desconto_rs)
    linhas_resumo.append("")
    if desconto_v > 0 and subtotal_v > 0:
        pct = desconto_v / subtotal_v * 100
        linhas_resumo += [
            f"💲 Subtotal:         R$ {_fmt_brl(subtotal_v)}",
            f"🏷️ Desconto:        -R$ {_fmt_brl(desconto_v)} ({pct:.1f}%)",
            f"✅ Valor negociado:  R$ {_fmt_brl(total_final_v)}",
        ]
    elif total_final_v > 0:
        linhas_resumo.append(f"✅ Valor:            R$ {_fmt_brl(total_final_v)}")
    texto = f"{emoji} {label_tipo} | 🏗 {label_ggv}\n\n{_dados_display(dados)}\n\n" + "\n".join(linhas_resumo) + "\n\nRevisar e gerar PFM."
    return texto, teclado_gerar(doc_id, tipo, ggv)

_FORN_COLS = ["nome", "razao_social", "cnpj", "cpf", "chave_pix", "email",
              "whatsapp", "logradouro", "numero", "bairro", "cidade", "uf", "cep"]

def buscar_fornecedor(nome_claude, cnpj_claude=None):
    """Busca no BD: 1º por CNPJ exato, 2º por prefixo do nome."""
    with sqlite3.connect(DB_PATH) as con:
        sel = f"SELECT {', '.join(_FORN_COLS)} FROM fornecedores"

        # 1. CNPJ — mais confiável; ignora o nosso próprio CNPJ (dado para fatura extraído errado)
        if cnpj_claude and cnpj_claude != "A PREENCHER":
            cnpj_digits = re.sub(r"\D", "", cnpj_claude)
            if cnpj_digits != DELTAD_CNPJ_DIGITS:
                row = con.execute(
                    f"{sel} WHERE REPLACE(REPLACE(REPLACE(cnpj,'.','' ),'/',''),'-','') = ? LIMIT 1",
                    (cnpj_digits,)
                ).fetchone()
                if row:
                    return dict(zip(_FORN_COLS, row))

        # 2. Prefixo do primeiro token do nome (evita falsos positivos de substring)
        if nome_claude and nome_claude != "A PREENCHER":
            primeiro = nome_claude.strip().upper().split()[0]
            row = con.execute(
                f"{sel} WHERE UPPER(nome) LIKE ? OR UPPER(razao_social) LIKE ? LIMIT 1",
                (f"{primeiro}%", f"{primeiro}%")
            ).fetchone()
            if row:
                return dict(zip(_FORN_COLS, row))

    return None

# ── PFM ───────────────────────────────────────────────────────────────────

def _campo(dados, nome):
    nao_encontrado = {
        "não identificado", "nao identificado",
        "não especificado", "nao especificado",
        "não informado", "nao informado",
        "n/a", "—", "-", "",
    }
    for linha in dados.splitlines():
        stripped = linha.strip().lstrip("- *")
        if stripped.lower().startswith(nome.lower() + ":"):
            val = stripped.split(":", 1)[1].strip().strip("*").strip()
            if val.lower() not in nao_encontrado:
                return val
    return "A PREENCHER"

def _substituir_campo(dados, nome, novo_valor):
    linhas = dados.splitlines()
    for i, linha in enumerate(linhas):
        stripped = linha.strip().lstrip("- *")
        if stripped.lower().startswith(nome.lower() + ":"):
            linhas[i] = f"{nome}: {novo_valor}"
            return "\n".join(linhas)
    return dados + f"\n{nome}: {novo_valor}"

def _bloco_itens(dados):
    linhas = dados.splitlines()
    capturando, resultado = False, []
    for linha in linhas:
        stripped = linha.strip().lstrip("- *")
        if re.match(r"^(itens|materiais)", stripped, re.IGNORECASE) and ":" in stripped:
            capturando = True
            continue
        if capturando:
            if stripped and not re.match(r"^\d+\.", stripped) and ":" in stripped and not stripped.startswith("http"):
                break
            resultado.append(linha)
    return "\n".join(resultado).strip() or "Nenhum item encontrado."

def _substituir_itens(dados, novo_bloco):
    linhas = dados.splitlines()
    inicio, fim, capturando = None, len(linhas), False
    for i, linha in enumerate(linhas):
        stripped = linha.strip().lstrip("- *")
        if re.match(r"^(itens|materiais)", stripped, re.IGNORECASE) and ":" in stripped:
            inicio = i
            capturando = True
            continue
        if capturando:
            if stripped and not re.match(r"^\d+\.", stripped) and ":" in stripped and not stripped.startswith("http"):
                fim = i
                break
    if inicio is None:
        return dados + f"\nItens:\n{novo_bloco}"
    return "\n".join(linhas[:inicio + 1] + novo_bloco.splitlines() + linhas[fim:])

ITEM_RE = re.compile(
    r"^\d+\.\s+(.+?)\s+\(([0-9,.]+)\s+([A-Za-z]{1,4})\)\s*[—–\-]+\s*R\$\s*([0-9.,]+)",
    re.IGNORECASE,
)

def _parse_brl(s):
    s = s.strip().replace(" ", "")
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    return float(s.replace(",", "."))

def _fmt_brl(v):
    s = f"{v:,.2f}"                                        # "6,292.93"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")  # "6.292,93"

def _itens(dados):
    """Retorna lista de dicts {desc, und, qtde, unit, total, _total_v} ou strings como fallback."""
    resultado, capturando = [], False
    for linha in dados.splitlines():
        stripped = linha.strip().lstrip("- *")
        if re.match(r"^(itens|materiais)", stripped, re.IGNORECASE) and ":" in stripped:
            capturando = True
            continue
        if capturando:
            if not stripped:
                continue
            if re.match(r"^(valor total|condição|condicao|prazo|validade|observ)", stripped, re.IGNORECASE):
                break
            m = ITEM_RE.match(stripped)
            if m:
                desc, qtde_str, und, total_str = m.groups()
                total_v = _parse_brl(total_str)
                qtde_v  = _parse_brl(qtde_str)
                unit_v  = total_v / qtde_v if qtde_v else 0
                resultado.append({
                    "desc":     desc.strip(),
                    "und":      und.upper(),
                    "qtde":     qtde_str,
                    "unit":     _fmt_brl(unit_v),
                    "total":    _fmt_brl(total_v),
                    "_total_v": total_v,
                })
            elif stripped:
                resultado.append(stripped)
    return resultado

def _obs(dados):
    resultado, capturando = [], False
    for linha in dados.splitlines():
        stripped = linha.strip()
        if stripped.lower().startswith("observaç"):
            capturando = True
            continue
        if capturando and stripped:
            resultado.append(stripped.lstrip("- *"))
    return "\n".join(resultado)

def _calcular_totais(dados, desconto_rs):
    """Retorna (subtotal_v, desconto_v, total_final_v) a partir dos dados extraídos."""
    itens = _itens(dados)
    subtotal_v = sum(i.get("_total_v", 0) for i in itens if isinstance(i, dict))
    if not subtotal_v:
        try:
            subtotal_v = _parse_brl(re.sub(r"[^\d,.]", "", _campo(dados, "Valor total")))
        except Exception:
            subtotal_v = 0.0
    desconto_v = 0.0
    desconto_raw = desconto_rs or (
        _campo(dados, "Desconto") if _campo(dados, "Desconto") != "A PREENCHER" else None
    )
    if desconto_raw:
        try:
            desconto_v = _parse_brl(re.sub(r"[^\d,.]", "", str(desconto_raw)))
        except Exception:
            desconto_v = 0.0
    return subtotal_v, desconto_v, subtotal_v - desconto_v

def _data_extenso(dt):
    return f"Carambeí, {dt.day} de {MESES[dt.month-1]} de {dt.year}."

def _cell_bg(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)

def _set_col_widths(tbl, widths_cm):
    tbl.autofit = False
    for i, w in enumerate(widths_cm):
        for cell in tbl.columns[i].cells:
            cell.width = Cm(w)

def _secao_row(tbl, texto, ncols, bg="1F3864"):
    """Linha de cabeçalho de seção (fundo azul, texto branco)."""
    row = tbl.add_row()
    cell = row.cells[0]
    for i in range(1, ncols):
        cell.merge(row.cells[i])
    _cell_bg(cell, bg)
    p = cell.paragraphs[0]
    r = p.add_run(texto)
    r.bold = True
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    return row

def _kv_row(tbl, label, valor, label_bg="D9D9D9"):
    """Linha label | valor em 2 colunas."""
    row = tbl.add_row()
    c_l = row.cells[0]
    _cell_bg(c_l, label_bg)
    r = c_l.paragraphs[0].add_run(label)
    r.bold = True
    r.font.size = Pt(8)
    c_r = row.cells[1]
    c_r.paragraphs[0].add_run(str(valor or "")).font.size = Pt(9)
    return row

def proximo_pfm_numero(ggv):
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT MAX(pfm_numero) FROM documentos WHERE ggv=? AND pfm_numero IS NOT NULL",
            (ggv,)
        ).fetchone()
    return (row[0] or 0) + 1

def gerar_pfm(doc_id):
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT ggv, dados_claude, condicao_pgto, data_entrega, endereco_entrega, desconto_rs FROM documentos WHERE id=?",
            (doc_id,)
        ).fetchone()
    if row is None:
        raise ValueError(f"Documento {doc_id} não encontrado no banco.")
    ggv, dados, condicao, data_entrega_db, endereco, desconto_rs = row

    nome_claude = _campo(dados, "Fornecedor")
    cnpj_claude = _campo(dados, "CNPJ/CPF")
    forn_db     = buscar_fornecedor(nome_claude, cnpj_claude)

    if forn_db:
        fornecedor = forn_db.get("razao_social") or forn_db.get("nome") or nome_claude
        cnpj       = forn_db.get("cnpj") or forn_db.get("cpf") or cnpj_claude
        pix        = forn_db.get("chave_pix") or _campo(dados, "Chave PIX")
        forn_logr  = " ".join(filter(None, [forn_db.get("logradouro"), forn_db.get("numero")]))
        forn_bairro = forn_db.get("bairro") or ""
        # Valida cidade: máx 30 chars, sem '/', sem dígitos — filtra dados errados do import
        _cidade = forn_db.get("cidade") or ""
        _uf     = forn_db.get("uf") or ""
        _cep    = forn_db.get("cep") or ""
        if len(_cidade) > 30 or "/" in _cidade or any(c.isdigit() for c in _cidade):
            _cidade = _uf = _cep = ""
        forn_cidade  = " / ".join(filter(None, [_cidade, _uf, _cep]))
        forn_email   = forn_db.get("email") or ""
        forn_fone    = forn_db.get("whatsapp") or ""
        forn_contato = forn_db.get("contato") or ""
    else:
        fornecedor  = nome_claude
        cnpj        = cnpj_claude
        pix         = _campo(dados, "Chave PIX")
        forn_logr = forn_bairro = forn_cidade = forn_email = forn_fone = forn_contato = ""

    prazo        = _campo(dados, "Prazo de entrega")
    if prazo == "A PREENCHER":
        prazo = _campo(dados, "Data/prazo de entrega")
    data_entrega = data_entrega_db or "A PREENCHER"
    itens        = _itens(dados)
    obs          = _obs(dados)

    subtotal_v, desconto_v, total_final_v = _calcular_totais(dados, desconto_rs)
    valor = f"R$ {_fmt_brl(total_final_v)}" if total_final_v > 0 else _campo(dados, "Valor total")

    pfm_num    = proximo_pfm_numero(ggv)
    pfm_codigo = f"{ggv}-{pfm_num:03d}"
    atualizar(doc_id, pfm_numero=pfm_num, status="pfm_gerado")

    now = datetime.now()
    doc = Document()
    for s in doc.sections:
        s.top_margin    = Cm(1.5)
        s.bottom_margin = Cm(1.5)
        s.left_margin   = Cm(2)
        s.right_margin  = Cm(2)
    # Largura útil: 21 - 4 = 17 cm

    # ── CABEÇALHO ────────────────────────────────────────────────────────────
    tbl_h = doc.add_table(rows=1, cols=2)
    tbl_h.style = "Table Grid"
    _set_col_widths(tbl_h, [11, 6])
    for c in tbl_h.rows[0].cells:
        _cell_bg(c, "D9E2F3")

    c_l = tbl_h.rows[0].cells[0]
    r = c_l.paragraphs[0].add_run("DeltaD Engenharia")
    r.bold = True; r.font.size = Pt(13)
    p2 = c_l.add_paragraph("Pedido de Fornecimento de Material")
    p2.runs[0].font.size = Pt(9)

    c_r = tbl_h.rows[0].cells[1]
    c_r.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r2 = c_r.paragraphs[0].add_run(f"Nº: {pfm_codigo}")
    r2.bold = True; r2.font.size = Pt(12)
    p3 = c_r.add_paragraph(_data_extenso(now))
    p3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p3.runs[0].font.size = Pt(8)

    # ── FORNECEDOR ───────────────────────────────────────────────────────────
    doc.add_paragraph()
    tbl_f = doc.add_table(rows=0, cols=2)
    tbl_f.style = "Table Grid"
    _set_col_widths(tbl_f, [5, 12])
    _secao_row(tbl_f, "FORNECEDOR", 2)
    _kv_row(tbl_f, "RAZÃO SOCIAL / NOME", fornecedor)
    _kv_row(tbl_f, "CNPJ/CPF", cnpj)
    _kv_row(tbl_f, "I.E.", "ISENTO")
    if forn_logr:
        _kv_row(tbl_f, "LOGRADOURO / Nº", forn_logr)
    if forn_bairro:
        _kv_row(tbl_f, "BAIRRO", forn_bairro)
    if forn_cidade:
        _kv_row(tbl_f, "CIDADE / UF / CEP", forn_cidade)
    if forn_contato:
        _kv_row(tbl_f, "CONTATO", forn_contato)
    if forn_email:
        _kv_row(tbl_f, "E-MAIL", forn_email)
    if forn_fone:
        _kv_row(tbl_f, "WHATSAPP", forn_fone)
    _kv_row(tbl_f, "CHAVE PIX", pix)

    # ── EMPREENDIMENTO ───────────────────────────────────────────────────────
    doc.add_paragraph()
    tbl_e = doc.add_table(rows=0, cols=2)
    tbl_e.style = "Table Grid"
    _set_col_widths(tbl_e, [5, 12])
    _secao_row(tbl_e, "EMPREENDIMENTO", 2)
    _kv_row(tbl_e, ggv, GGV_DESC.get(ggv, ggv))

    # ── MATERIAIS ────────────────────────────────────────────────────────────
    doc.add_paragraph()
    tbl_m = doc.add_table(rows=0, cols=6)
    tbl_m.style = "Table Grid"
    _set_col_widths(tbl_m, [1.2, 7.3, 1.5, 1.5, 2.75, 2.75])
    _secao_row(tbl_m, "MATERIAIS", 6)

    # Cabeçalho de colunas
    row_hdr = tbl_m.add_row()
    for i, h in enumerate(["ID", "DESCRIÇÃO", "UND", "QTDE", "R$ UNIT", "R$ TOTAL"]):
        c = row_hdr.cells[i]
        _cell_bg(c, "D9D9D9")
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.bold = True; r.font.size = Pt(8)

    # Itens
    lista_itens = itens if itens else [dados[:200]]
    for idx, item in enumerate(lista_itens, 1):
        ri = tbl_m.add_row()
        ri.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        ri.cells[0].paragraphs[0].add_run(f"{idx:02d}").font.size = Pt(9)
        if isinstance(item, dict):
            ri.cells[1].paragraphs[0].add_run(item["desc"]).font.size = Pt(9)
            for j, key in [(2, "und"), (3, "qtde"), (4, "unit"), (5, "total")]:
                ri.cells[j].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
                ri.cells[j].paragraphs[0].add_run(str(item[key])).font.size = Pt(9)
        else:
            ri.cells[1].paragraphs[0].add_run(str(item).lstrip("- ")).font.size = Pt(9)
            for j in [2, 3, 4, 5]:
                ri.cells[j].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                ri.cells[j].paragraphs[0].add_run("—").font.size = Pt(9)

    # Totais — subtotal + desconto (se houver) + total final
    def _total_row(tbl, label, valor_str, bg="D9D9D9"):
        r = tbl.add_row()
        c_label = r.cells[0]
        for i in range(1, 5):
            c_label.merge(r.cells[i])
        _cell_bg(c_label, bg)
        p = c_label.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = p.add_run(label)
        run.bold = True; run.font.size = Pt(9)
        c_v = r.cells[5]
        _cell_bg(c_v, bg)
        p_v = c_v.paragraphs[0]
        p_v.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run_v = p_v.add_run(valor_str)
        run_v.bold = True; run_v.font.size = Pt(9)

    if desconto_v > 0 and subtotal_v > 0:
        pct = desconto_v / subtotal_v * 100
        _total_row(tbl_m, "SUBTOTAL:", f"R$ {_fmt_brl(subtotal_v)}", "F2F2F2")
        _total_row(tbl_m, f"DESCONTO ({pct:.2f}%):", f"-R$ {_fmt_brl(desconto_v)}", "F2F2F2")

    _total_row(tbl_m, "TOTAL DO PEDIDO:", valor)

    # ── PARTE INFERIOR: PRAZO | DADOS ────────────────────────────────────────
    doc.add_paragraph()
    tbl_b = doc.add_table(rows=1, cols=2)
    tbl_b.style = "Table Grid"
    _set_col_widths(tbl_b, [8.5, 8.5])

    # — Esquerda: Prazo e Condições —
    c_prazo = tbl_b.rows[0].cells[0]
    p = c_prazo.paragraphs[0]
    r = p.add_run("PRAZO PARA ENTREGA E CONDIÇÕES DE PAGAMENTO")
    r.bold = True; r.font.size = Pt(8)
    _cell_bg(c_prazo, "D9D9D9")

    def _kv_p(cell, label, val):
        p = cell.add_paragraph()
        rl = p.add_run(f"{label}: ")
        rl.bold = True; rl.font.size = Pt(8)
        p.add_run(str(val or "A PREENCHER")).font.size = Pt(9)

    _kv_p(c_prazo, "CONDIÇÕES DE PAGAMENTO", condicao)
    _kv_p(c_prazo, "CHAVE PIX", pix)
    _kv_p(c_prazo, "DATA DE ENTREGA", data_entrega)
    obs_partes = []
    prazo_texto = prazo if prazo and prazo not in ("A PREENCHER",) and prazo != data_entrega else None
    if prazo_texto:
        obs_partes.append(prazo_texto)
    if obs and obs != prazo_texto:
        obs_partes.append(obs)
    if obs_partes:
        _kv_p(c_prazo, "OBSERVAÇÃO", " | ".join(obs_partes))

    # Nota de foto
    p_foto = c_prazo.add_paragraph()
    p_foto.add_run(
        "FAVOR TIRAR FOTOS DO MATERIAL DESCARREGADO E ENVIAR POR WHATSAPP PARA DENNIS – (42) 99127-1255"
    ).font.size = Pt(7)

    # — Direita: Dados para Fatura e Entrega —
    c_dados = tbl_b.rows[0].cells[1]
    p_fatura = c_dados.paragraphs[0]
    r_f = p_fatura.add_run("DADOS PARA FATURA")
    r_f.bold = True; r_f.font.size = Pt(8)
    _cell_bg(c_dados, "EBF3F0")

    def _linha(cell, txt, bold=False, size=9):
        p = cell.add_paragraph()
        r = p.add_run(txt)
        r.bold = bold; r.font.size = Pt(size)

    _linha(c_dados, DELTAD["nome"], bold=True, size=9)
    _linha(c_dados, f"CNPJ: {DELTAD['cnpj']}", size=9)
    _linha(c_dados, DELTAD["end"], size=8)
    _linha(c_dados, DELTAD["email"], size=8)
    _linha(c_dados, "")
    p_ent = c_dados.add_paragraph()
    p_ent.add_run("DADOS PARA ENTREGA").bold = True
    p_ent.runs[0].font.size = Pt(8)
    _linha(c_dados, endereco or "A PREENCHER", size=9)

    pasta = GGV_ONEDRIVE.get(ggv, Path("data/pfms"))
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{pfm_codigo}.docx"
    doc.save(caminho)

    lanc_status, ja_existia = registrar_lancamento(
        doc_id, pfm_codigo, ggv, fornecedor, total_final_v, data_entrega_db
    )
    return caminho, pfm_codigo, fornecedor, total_final_v, lanc_status, ja_existia

# ── UI helpers ─────────────────────────────────────────────────────────────

def parse_resposta(texto):
    tipo, ggv = "nao_relacionado", "nao_identificado"
    corpo = []
    for linha in texto.strip().splitlines():
        if linha.startswith("TIPO:"):
            tipo = linha.split(":", 1)[1].strip().strip("[]").split("|")[0].strip()
        elif linha.startswith("GGV:"):
            ggv = linha.split(":", 1)[1].strip().strip("[]").split("|")[0].strip()
        else:
            corpo.append(linha)
    return tipo, ggv, "\n".join(corpo).strip()

def teclado_confirmacao(doc_id, tipo, ggv):
    emoji_tipo = TIPOS.get(tipo, ("📄", tipo))[0]
    label_ggv  = ggv if ggv != "nao_identificado" else "❓GGV"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirmar",          callback_data=f"ok:{doc_id}:{tipo}:{ggv}"),
            InlineKeyboardButton(f"🔄 {emoji_tipo} Tipo", callback_data=f"sel_tipo:{doc_id}:{tipo}:{ggv}"),
        ],
        [
            InlineKeyboardButton(f"🏗 {label_ggv}",       callback_data=f"sel_ggv:{doc_id}:{tipo}:{ggv}"),
            InlineKeyboardButton("❌ Cancelar",            callback_data=f"cancelar:{doc_id}"),
        ],
        [
            InlineKeyboardButton("✏️ Editar campos",      callback_data=f"sel_edit:{doc_id}:{tipo}:{ggv}"),
        ]
    ])

def teclado_condicao(doc_id, ggv):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 PIX à vista",                   callback_data=f"pgto:{doc_id}:{ggv}:pix_avista")],
        [InlineKeyboardButton("💰 PIX 50% entrada + 50% entrega", callback_data=f"pgto:{doc_id}:{ggv}:pix_50_50")],
        [InlineKeyboardButton("✏️ Outro (digitar)",                callback_data=f"pgto:{doc_id}:{ggv}:outro")],
    ])

def teclado_endereco(doc_id, ggv):
    chave_obra = f"obra_{ggv}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🏗 Obra ({ggv})",    callback_data=f"end:{doc_id}:{ggv}:{chave_obra}")],
        [InlineKeyboardButton("🏠 Casa",             callback_data=f"end:{doc_id}:{ggv}:casa")],
        [InlineKeyboardButton("🏢 Escritório",       callback_data=f"end:{doc_id}:{ggv}:escritorio")],
        [InlineKeyboardButton("🌳 Chácara",          callback_data=f"end:{doc_id}:{ggv}:chacara")],
        [InlineKeyboardButton("✏️ Outro (digitar)",  callback_data=f"end:{doc_id}:{ggv}:outro")],
    ])

def teclado_gerar(doc_id, tipo, ggv):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Gerar PFM",      callback_data=f"pfm:{doc_id}:{ggv}")],
        [InlineKeyboardButton("✏️ Editar campos",  callback_data=f"sel_edit:{doc_id}:{tipo}:{ggv}")],
        [InlineKeyboardButton("❌ Cancelar",        callback_data=f"cancelar:{doc_id}")],
    ])

# ── Handlers ───────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DONO_ID:
        return
    await update.message.reply_text("Estou online.")

async def receber_arquivo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DONO_ID:
        return

    if update.message.photo:
        tg_file = await update.message.photo[-1].get_file()
        nome = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        mime = None
    elif update.message.document:
        tg_file = await update.message.document.get_file()
        nome = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{update.message.document.file_name}"
        mime = update.message.document.mime_type or "application/pdf"
    else:
        await update.message.reply_text("Recebi. Ainda não sei o que fazer com isso.")
        return

    conteudo = await tg_file.download_as_bytearray()
    hash_arquivo = hashlib.sha256(conteudo).hexdigest()

    if ja_existe(hash_arquivo):
        await update.message.reply_text("⚠️ Este arquivo já foi recebido antes. Ignorando.")
        return

    if mime is None:
        mime = "image/png" if conteudo[:4] == b'\x89PNG' else "image/jpeg"

    ACEITOS = {"image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"}
    if mime not in ACEITOS:
        await update.message.reply_text(
            f"⚠️ Formato não suportado: {mime}\n\n"
            "Aceito hoje:\n• 📷 Foto (JPEG, PNG, GIF, WEBP)\n• 📄 PDF\n\n"
            "CSV e Excel chegam nas próximas versões."
        )
        return

    caminho = UPLOADS / nome
    caminho.write_bytes(conteudo)
    await update.message.reply_text("✅ Arquivo salvo. Classificando com IA...")

    tipo_conteudo = "document" if mime == "application/pdf" else "image"
    dados_b64 = base64.standard_b64encode(conteudo).decode()

    resposta = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {"type": tipo_conteudo, "source": {"type": "base64", "media_type": mime, "data": dados_b64}},
                {"type": "text", "text": PROMPT}
            ]
        }]
    )

    tipo, ggv, corpo = parse_resposta(resposta.content[0].text)
    doc_id = registrar(nome, caminho, hash_arquivo, tipo, ggv, corpo)

    emoji, label_tipo = TIPOS.get(tipo, ("📄", tipo))
    label_ggv = ggv if ggv != "nao_identificado" else "❓ GGV não identificado"

    await update.message.reply_text(
        f"{emoji} {label_tipo} | 🏗 {label_ggv}\n\n{corpo}\n\nConfirmar ou ajustar?",
        reply_markup=teclado_confirmacao(doc_id, tipo, ggv)
    )

async def receber_texto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DONO_ID:
        return
    aguardando = ctx.user_data.get("aguardando")
    if not aguardando:
        await update.message.reply_text("Recebi. Ainda não sei o que fazer com isso.")
        return

    doc_id = ctx.user_data.get("doc_id")
    ggv    = ctx.user_data.get("ggv")
    texto  = update.message.text.strip()

    if aguardando == "condicao_pgto":
        atualizar(doc_id, condicao_pgto=texto)
        ctx.user_data["aguardando"] = None
        texto_resumo, markup = _resumo_gerar(doc_id)
        await update.message.reply_text(texto_resumo, reply_markup=markup)

    elif aguardando == "data_entrega":
        atualizar(doc_id, data_entrega=texto)
        ctx.user_data["aguardando"] = None
        texto_resumo, markup = _resumo_gerar(doc_id)
        await update.message.reply_text(texto_resumo, reply_markup=markup)

    elif aguardando == "edit_desconto":
        try:
            v = _parse_brl(re.sub(r"[^\d,.]", "", texto))
        except Exception:
            v = 0.0
        atualizar(doc_id, desconto_rs=f"{v:.2f}" if v > 0 else None)
        ctx.user_data["aguardando"] = None
        texto_resumo, markup = _resumo_gerar(doc_id)
        await update.message.reply_text(texto_resumo, reply_markup=markup)

    elif aguardando in ("edit_fornecedor", "edit_cnpj", "edit_valor", "edit_pix", "edit_itens"):
        campo_map = {
            "edit_fornecedor": "Fornecedor",
            "edit_cnpj":       "CNPJ/CPF",
            "edit_valor":      "Valor total",
            "edit_pix":        "Chave PIX",
        }
        tipo = ctx.user_data.get("tipo", "orcamento")
        with sqlite3.connect(DB_PATH) as con:
            row = con.execute(
                "SELECT dados_claude, ggv FROM documentos WHERE id=?", (doc_id,)
            ).fetchone()
        if row:
            dados_atuais, ggv_db = row
            if aguardando == "edit_itens":
                novos_dados = _substituir_itens(dados_atuais, texto)
                nome_campo = "Itens"
            else:
                nome_campo = campo_map[aguardando]
                novos_dados = _substituir_campo(dados_atuais, nome_campo, texto)
            atualizar(doc_id, dados_claude=novos_dados)
            ctx.user_data["aguardando"] = None
            texto_resumo, markup = _resumo_gerar(doc_id)
            await update.message.reply_text(texto_resumo, reply_markup=markup)
        else:
            ctx.user_data["aguardando"] = None
            await update.message.reply_text("❌ Documento não encontrado.")

    elif aguardando == "endereco_entrega":
        atualizar(doc_id, endereco_entrega=texto)
        ctx.user_data["aguardando"] = None
        texto_resumo, markup = _resumo_gerar(doc_id)
        await update.message.reply_text(texto_resumo, reply_markup=markup)

async def responder_botao(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    partes = query.data.split(":")
    acao   = partes[0]

    # GGV blocking — alert antes de responder, depois retorna
    if acao == "ok" and partes[3] == "nao_identificado":
        await query.answer("⚠️ Selecione o GGV antes de confirmar.", show_alert=True)
        return

    await query.answer()

    try:
        if acao == "ok":
            _, doc_id, tipo, ggv = partes
            atualizar(int(doc_id), status="confirmado")
            if tipo == "orcamento":
                ctx.user_data.update({"doc_id": int(doc_id), "ggv": ggv, "aguardando": None})
                texto, markup = _resumo_gerar(int(doc_id))
                await query.edit_message_text(texto, reply_markup=markup)
            else:
                emoji, label = TIPOS.get(tipo, ("📄", tipo))
                await query.edit_message_text(f"✅ Confirmado: {emoji} {label} | 🏗 {ggv}")

        elif acao == "cancelar":
            atualizar(int(partes[1]), status="cancelado")
            await query.edit_message_text("❌ Cancelado.")

        elif acao == "sel_tipo":
            _, doc_id, tipo, ggv = partes
            botoes = [[InlineKeyboardButton(f"{e} {l}", callback_data=f"set_tipo:{doc_id}:{t}:{ggv}")]
                      for t, (e, l) in TIPOS.items()]
            await query.edit_message_reply_markup(InlineKeyboardMarkup(botoes))

        elif acao == "set_tipo":
            _, doc_id, novo_tipo, ggv = partes
            atualizar(int(doc_id), tipo=novo_tipo)
            with sqlite3.connect(DB_PATH) as con:
                status = con.execute("SELECT status FROM documentos WHERE id=?", (int(doc_id),)).fetchone()[0]
            if status == "confirmado":
                texto, markup = _resumo_gerar(int(doc_id))
                await query.edit_message_text(texto, reply_markup=markup)
            else:
                emoji, label = TIPOS.get(novo_tipo, ("📄", novo_tipo))
                label_ggv = ggv if ggv != "nao_identificado" else "❓ GGV não identificado"
                corpo = _dados_doc(int(doc_id))
                await query.edit_message_text(
                    f"{emoji} {label} | 🏗 {label_ggv}\n\n{corpo}\n\nTipo corrigido. Confirmar ou ajustar?",
                    reply_markup=teclado_confirmacao(int(doc_id), novo_tipo, ggv)
                )

        elif acao == "sel_ggv":
            _, doc_id, tipo, ggv = partes
            botoes = [[InlineKeyboardButton(g, callback_data=f"set_ggv:{doc_id}:{tipo}:{g}")] for g in GGVS]
            botoes.append([InlineKeyboardButton("❓ Não identificado",
                                                callback_data=f"set_ggv:{doc_id}:{tipo}:nao_identificado")])
            await query.edit_message_reply_markup(InlineKeyboardMarkup(botoes))

        elif acao == "set_ggv":
            _, doc_id, tipo, novo_ggv = partes
            atualizar(int(doc_id), ggv=novo_ggv)
            with sqlite3.connect(DB_PATH) as con:
                status = con.execute("SELECT status FROM documentos WHERE id=?", (int(doc_id),)).fetchone()[0]
            if status == "confirmado":
                texto, markup = _resumo_gerar(int(doc_id))
                await query.edit_message_text(texto, reply_markup=markup)
            else:
                emoji, label = TIPOS.get(tipo, ("📄", tipo))
                label_ggv = novo_ggv if novo_ggv != "nao_identificado" else "❓ GGV não identificado"
                corpo = _dados_doc(int(doc_id))
                await query.edit_message_text(
                    f"{emoji} {label} | 🏗 {label_ggv}\n\n{corpo}\n\nGGV corrigido. Confirmar ou ajustar?",
                    reply_markup=teclado_confirmacao(int(doc_id), tipo, novo_ggv)
                )

        elif acao == "pgto":
            _, doc_id, ggv, escolha = partes
            if escolha == "outro":
                ctx.user_data.update({"doc_id": int(doc_id), "ggv": ggv, "aguardando": "condicao_pgto"})
                await query.edit_message_text("✏️ Digite a condição de pagamento:")
                return
            label_pgto = CONDICOES.get(escolha, escolha)
            atualizar(int(doc_id), condicao_pgto=label_pgto)
            ctx.user_data.update({"doc_id": int(doc_id), "ggv": ggv, "aguardando": None})
            texto, markup = _resumo_gerar(int(doc_id))
            await query.edit_message_text(texto, reply_markup=markup)

        elif acao == "end":
            _, doc_id, ggv, escolha = partes
            if escolha == "outro":
                ctx.user_data.update({"doc_id": int(doc_id), "ggv": ggv, "aguardando": "endereco_entrega"})
                await query.edit_message_text("✏️ Digite o endereço de entrega:")
                return
            endereco = ENDERECOS.get(escolha, escolha)
            atualizar(int(doc_id), endereco_entrega=endereco)
            texto, markup = _resumo_gerar(int(doc_id))
            await query.edit_message_text(texto, reply_markup=markup)

        elif acao == "sel_edit":
            _, doc_id, tipo, ggv = partes
            botoes = [
                [InlineKeyboardButton("👤 Fornecedor",    callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:fornecedor")],
                [InlineKeyboardButton("🔢 CNPJ/CPF",      callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:cnpj")],
                [InlineKeyboardButton("💲 Valor total",   callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:valor")],
                [InlineKeyboardButton("🔑 Chave PIX",     callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:pix")],
                [InlineKeyboardButton("📦 Itens",         callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:itens")],
                [InlineKeyboardButton("🏷️ Desconto",     callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:desconto")],
                [InlineKeyboardButton("💰 Condição pgto", callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:pgto")],
                [InlineKeyboardButton("📅 Data entrega",  callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:data")],
                [InlineKeyboardButton("📍 Endereço",      callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:endereco")],
                [InlineKeyboardButton("🏗 GGV",           callback_data=f"sel_ggv:{doc_id}:{tipo}:{ggv}")],
                [InlineKeyboardButton("📋 Tipo doc.",     callback_data=f"sel_tipo:{doc_id}:{tipo}:{ggv}")],
                [InlineKeyboardButton("◀️ Voltar",        callback_data=f"voltar_edit:{doc_id}:{tipo}:{ggv}")],
            ]
            await query.edit_message_reply_markup(InlineKeyboardMarkup(botoes))

        elif acao == "edit_campo":
            _, doc_id, tipo, ggv, campo = partes
            ctx.user_data.update({"doc_id": int(doc_id), "ggv": ggv, "tipo": tipo})

            if campo == "pgto":
                ctx.user_data["aguardando"] = None
                await query.edit_message_text(
                    "💰 Selecione a condição de pagamento:",
                    reply_markup=teclado_condicao(doc_id, ggv)
                )
            elif campo == "endereco":
                ctx.user_data["aguardando"] = None
                await query.edit_message_text(
                    "📍 Selecione o endereço de entrega:",
                    reply_markup=teclado_endereco(doc_id, ggv)
                )
            elif campo == "itens":
                ctx.user_data["aguardando"] = "edit_itens"
                with sqlite3.connect(DB_PATH) as con:
                    row = con.execute("SELECT dados_claude FROM documentos WHERE id=?", (int(doc_id),)).fetchone()
                bloco = _bloco_itens(row[0] if row else "")
                await query.edit_message_text(
                    f"📦 Itens atuais:\n\n{bloco}\n\n"
                    "✏️ Digite os novos itens.\n\n"
                    "Para cálculo automático do total no PFM, use o formato:\n"
                    "1. Descrição (qtde UN) — R$ valor_total\n\n"
                    "Exemplo:\n"
                    "1. Cimento 50kg (10 sc) — R$ 350,00\n"
                    "2. Areia grossa (5 m³) — R$ 875,00\n\n"
                    "Formato livre também é aceito, mas sem cálculo automático."
                )
            else:
                aguardando_campo = "data_entrega" if campo == "data" else f"edit_{campo}"
                ctx.user_data["aguardando"] = aguardando_campo
                labels = {
                    "fornecedor": "nome do fornecedor",
                    "cnpj":       "CNPJ ou CPF",
                    "valor":      "valor total (ex: R$ 1.500,00)",
                    "pix":        "chave PIX",
                    "desconto":   "valor do desconto em R$ (ex: 80 ou 80,00) — ou 0 para remover",
                    "data":       "data de entrega (ex: 01/08/2026, 7 dias úteis, A combinar)",
                }
                campo_doc = {
                    "fornecedor": "Fornecedor",
                    "cnpj":       "CNPJ/CPF",
                    "valor":      "Valor total",
                    "pix":        "Chave PIX",
                }
                with sqlite3.connect(DB_PATH) as con:
                    row = con.execute(
                        "SELECT dados_claude, desconto_rs, data_entrega FROM documentos WHERE id=?", (int(doc_id),)
                    ).fetchone()
                dados_atuais, desconto_atual, data_atual = row if row else ("", None, None)
                if campo == "desconto":
                    atual = f"R$ {_fmt_brl(_parse_brl(re.sub(r'[^\d,.]', '', str(desconto_atual))))}" if desconto_atual else "Não informado"
                elif campo == "data":
                    atual = data_atual or "Não informada"
                else:
                    atual = _campo(dados_atuais, campo_doc.get(campo, campo))
                await query.edit_message_text(
                    f"Valor atual:\n{atual}\n\n✏️ Digite o {labels.get(campo, campo)}:"
                )

        elif acao == "voltar_edit":
            _, doc_id, tipo, ggv = partes
            texto, markup = _resumo_gerar(int(doc_id))
            await query.edit_message_text(texto, reply_markup=markup)

        elif acao == "pfm":
            _, doc_id, ggv = partes
            await query.edit_message_text("⏳ Gerando PFM...")
            caminho, codigo, fornecedor, valor_v, lanc_status, ja_existia = gerar_pfm(int(doc_id))
            with open(caminho, "rb") as f:
                await ctx.bot.send_document(
                    chat_id=DONO_ID,
                    document=f,
                    filename=f"{codigo}.docx",
                    caption=f"📄 {codigo} gerado."
                )
            if ja_existia:
                lanc_msg = f"⚠️ Lançamento {codigo} já estava registrado."
            elif lanc_status == "pendente_revisao":
                lanc_msg = (
                    f"⚠️ Lançamento criado como PENDENTE DE REVISÃO\n"
                    f"(fornecedor ou valor ausente — revisar manualmente)"
                )
            else:
                lanc_msg = (
                    f"💾 Lançamento registrado:\n"
                    f"   Fornecedor: {fornecedor}\n"
                    f"   Valor: R$ {_fmt_brl(valor_v)}\n"
                    f"   Status: A PAGAR"
                )
            await ctx.bot.send_message(chat_id=DONO_ID, text=lanc_msg)

    except Exception as e:
        await ctx.bot.send_message(chat_id=DONO_ID, text=f"❌ Erro interno: {e}")

# ── Inicialização ──────────────────────────────────────────────────────────

init_db()
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, receber_arquivo))
app.add_handler(CallbackQueryHandler(responder_botao))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_texto))
app.run_polling()
