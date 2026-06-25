import os
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
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

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

GGV_DESC = {
    "GGV01": "GGV01 — Matrícula 39.333, Quadra 05 Lote 02, JD das Nações, Carambeí-PR",
    "GGV02": "GGV02 — Matrícula 39.337, Quadra 05 Lote 06, JD das Nações, Carambeí-PR",
    "GGV03": "GGV03 — Matrícula 39.339, Quadra 05 Lote 08, JD das Nações, Carambeí-PR",
    "GGV00": "GGV00 — Despesas Gerais",
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
- Chave PIX:
- Itens principais (até 5):
- Valor total:
- Condição de pagamento:
- Data/prazo de entrega:
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

Formate sua resposta assim:
TIPO:[orcamento|comprovante_pix|extrato_mp|nao_relacionado]
GGV:[GGV00|GGV01|GGV02|GGV03|nao_identificado]

[dados extraídos]
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
                endereco_entrega TEXT,
                pfm_numero       INTEGER,
                status           TEXT DEFAULT 'recebido',
                criado_em        TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        for col in ["tipo", "ggv", "dados_claude", "condicao_pgto", "endereco_entrega", "pfm_numero INTEGER"]:
            try:
                con.execute(f"ALTER TABLE documentos ADD COLUMN {col}")
            except Exception:
                pass

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

# ── PFM ───────────────────────────────────────────────────────────────────

def _campo(dados, nome):
    nao_encontrado = {"não identificado", "nao identificado",
                      "não especificado", "nao especificado", ""}
    for linha in dados.splitlines():
        stripped = linha.strip().lstrip("- ")
        if stripped.lower().startswith(nome.lower() + ":"):
            val = stripped.split(":", 1)[1].strip()
            if val.lower() not in nao_encontrado:
                return val
    return "A PREENCHER"

def _itens(dados):
    resultado, capturando = [], False
    for linha in dados.splitlines():
        if "Itens principais" in linha:
            capturando = True
            continue
        if capturando:
            stripped = linha.strip()
            if not stripped or stripped.lower().startswith("valor total"):
                break
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
            resultado.append(stripped.lstrip("- "))
    return "\n".join(resultado)

def _secao(doc, titulo):
    p = doc.add_paragraph()
    r = p.add_run(titulo)
    r.bold = True
    r.font.size = Pt(11)

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
            "SELECT ggv, dados_claude, condicao_pgto, endereco_entrega FROM documentos WHERE id=?",
            (doc_id,)
        ).fetchone()
    ggv, dados, condicao, endereco = row

    fornecedor = _campo(dados, "Fornecedor")
    cnpj       = _campo(dados, "CNPJ/CPF")
    pix        = _campo(dados, "Chave PIX")
    valor      = _campo(dados, "Valor total")
    prazo      = _campo(dados, "Data/prazo de entrega")
    itens      = _itens(dados)
    obs        = _obs(dados)

    pfm_num    = proximo_pfm_numero(ggv)
    pfm_codigo = f"{ggv}-{pfm_num:03d}"
    atualizar(doc_id, pfm_numero=pfm_num, status="pfm_gerado")

    doc = Document()
    for section in doc.sections:
        section.top_margin    = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin   = Cm(2.5)
        section.right_margin  = Cm(2.5)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("DELTAD ENGENHARIA\nPEDIDO DE FORNECIMENTO DE MATERIAL")
    r.bold = True
    r.font.size = Pt(14)

    doc.add_paragraph()

    p = doc.add_paragraph()
    p.add_run("Nº  ")
    r = p.add_run(pfm_codigo)
    r.bold = True
    r.font.size = Pt(13)
    p.add_run(f"          Data: {datetime.now().strftime('%d/%m/%Y')}")

    doc.add_paragraph()

    _secao(doc, "FORNECEDOR")
    doc.add_paragraph(f"Empresa / Responsável:  {fornecedor}")
    doc.add_paragraph(f"CNPJ / CPF:  {cnpj}")
    doc.add_paragraph(f"Chave PIX:  {pix}")

    doc.add_paragraph()

    _secao(doc, "EMPREENDIMENTO")
    doc.add_paragraph(GGV_DESC.get(ggv, ggv))

    doc.add_paragraph()

    _secao(doc, "ITENS")
    if itens:
        for item in itens:
            doc.add_paragraph(item)
    else:
        doc.add_paragraph(dados)

    doc.add_paragraph()

    p = doc.add_paragraph()
    r = p.add_run(f"VALOR TOTAL:  {valor}")
    r.bold = True
    r.font.size = Pt(12)

    doc.add_paragraph()

    _secao(doc, "CONDIÇÃO DE PAGAMENTO")
    doc.add_paragraph(condicao or "A PREENCHER")

    doc.add_paragraph()

    _secao(doc, "PRAZO / DATA DE ENTREGA")
    doc.add_paragraph(prazo)

    doc.add_paragraph()

    _secao(doc, "ENDEREÇO DE ENTREGA")
    doc.add_paragraph(endereco or "A PREENCHER")

    if obs:
        doc.add_paragraph()
        _secao(doc, "OBSERVAÇÕES")
        doc.add_paragraph(obs)

    doc.add_paragraph()
    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("_" * 40 + "\nDennis Verschoor\nDeltaD Engenharia\nCarambeí-PR")

    Path("data/pfms").mkdir(parents=True, exist_ok=True)
    caminho = Path("data/pfms") / f"{pfm_codigo}.docx"
    doc.save(caminho)
    return caminho, pfm_codigo

# ── UI helpers ─────────────────────────────────────────────────────────────

def parse_resposta(texto):
    tipo, ggv = "nao_relacionado", "nao_identificado"
    corpo = []
    for linha in texto.strip().splitlines():
        if linha.startswith("TIPO:"):
            tipo = linha.split(":", 1)[1].strip()
        elif linha.startswith("GGV:"):
            ggv = linha.split(":", 1)[1].strip()
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
        ]
    ])

def teclado_condicao(doc_id, ggv):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 PIX à vista",                   callback_data=f"pgto:{doc_id}:{ggv}:pix_avista")],
        [InlineKeyboardButton("💰 PIX 50% entrada + 50% entrega", callback_data=f"pgto:{doc_id}:{ggv}:pix_50_50")],
        [InlineKeyboardButton("✏️ Outro (digitar)",                callback_data=f"pgto:{doc_id}:{ggv}:outro")],
    ])

def teclado_endereco(doc_id, ggv, pgto):
    chave_obra = f"obra_{ggv}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🏗 Obra ({ggv})",    callback_data=f"end:{doc_id}:{ggv}:{pgto}:{chave_obra}")],
        [InlineKeyboardButton("🏠 Casa",             callback_data=f"end:{doc_id}:{ggv}:{pgto}:casa")],
        [InlineKeyboardButton("🏢 Escritório",       callback_data=f"end:{doc_id}:{ggv}:{pgto}:escritorio")],
        [InlineKeyboardButton("🌳 Chácara",          callback_data=f"end:{doc_id}:{ggv}:{pgto}:chacara")],
        [InlineKeyboardButton("✏️ Outro (digitar)",  callback_data=f"end:{doc_id}:{ggv}:{pgto}:outro")],
    ])

def teclado_pfm(doc_id, ggv):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📄 Gerar PFM", callback_data=f"pfm:{doc_id}:{ggv}")
    ]])

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
        max_tokens=1024,
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
        ctx.user_data["condicao_pgto"] = texto
        ctx.user_data["aguardando"] = None
        await update.message.reply_text(
            f"✅ Condição: {texto}\n\nQual o endereço de entrega?",
            reply_markup=teclado_endereco(doc_id, ggv, "custom")
        )

    elif aguardando == "endereco_entrega":
        condicao = ctx.user_data.get("condicao_pgto", "")
        atualizar(doc_id, endereco_entrega=texto, status="pronto_pfm")
        ctx.user_data["aguardando"] = None
        await update.message.reply_text(
            f"✅ Dados coletados\n\n"
            f"🏗 {ggv}\n💰 {condicao}\n📍 {texto}",
            reply_markup=teclado_pfm(doc_id, ggv)
        )

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
            if tipo == "orcamento":
                ctx.user_data.update({"doc_id": int(doc_id), "ggv": ggv, "aguardando": None})
                await query.edit_message_text(
                    f"📋 Orçamento | 🏗 {ggv}\n\nQual a condição de pagamento?",
                    reply_markup=teclado_condicao(doc_id, ggv)
                )
            else:
                atualizar(int(doc_id), status="confirmado")
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
            emoji, label = TIPOS.get(novo_tipo, ("📄", novo_tipo))
            label_ggv = ggv if ggv != "nao_identificado" else "❓ GGV não identificado"
            await query.edit_message_text(
                f"{emoji} {label} | 🏗 {label_ggv}\n\nTipo corrigido. Confirmar?",
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
            emoji, label = TIPOS.get(tipo, ("📄", tipo))
            label_ggv = novo_ggv if novo_ggv != "nao_identificado" else "❓ GGV não identificado"
            await query.edit_message_text(
                f"{emoji} {label} | 🏗 {label_ggv}\n\nGGV corrigido. Confirmar?",
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
            ctx.user_data.update({"doc_id": int(doc_id), "ggv": ggv, "condicao_pgto": label_pgto})
            await query.edit_message_text(
                f"✅ Pagamento: {label_pgto}\n\nQual o endereço de entrega?",
                reply_markup=teclado_endereco(doc_id, ggv, escolha)
            )

        elif acao == "end":
            _, doc_id, ggv, pgto, escolha = partes
            if escolha == "outro":
                ctx.user_data.update({"doc_id": int(doc_id), "ggv": ggv, "aguardando": "endereco_entrega"})
                await query.edit_message_text("✏️ Digite o endereço de entrega:")
                return
            endereco = ENDERECOS.get(escolha, escolha)
            condicao = CONDICOES.get(pgto, ctx.user_data.get("condicao_pgto", pgto))
            atualizar(int(doc_id), endereco_entrega=endereco, status="pronto_pfm")
            await query.edit_message_text(
                f"✅ Dados coletados\n\n"
                f"🏗 {ggv}\n💰 {condicao}\n📍 {endereco}",
                reply_markup=teclado_pfm(doc_id, ggv)
            )

        elif acao == "pfm":
            _, doc_id, ggv = partes
            await query.edit_message_text("⏳ Gerando PFM...")
            caminho, codigo = gerar_pfm(int(doc_id))
            with open(caminho, "rb") as f:
                await ctx.bot.send_document(
                    chat_id=DONO_ID,
                    document=f,
                    filename=f"{codigo}.docx",
                    caption=f"📄 {codigo} gerado."
                )
            await ctx.bot.send_message(chat_id=DONO_ID, text=f"✅ {codigo} enviado. Pronto para fiada 9.")

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
