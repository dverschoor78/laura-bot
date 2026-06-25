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
- Itens principais (até 5):
- Valor total:
- Condição de pagamento:
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

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS documentos (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                nome      TEXT,
                caminho   TEXT,
                hash      TEXT UNIQUE,
                tipo      TEXT DEFAULT 'desconhecido',
                ggv       TEXT DEFAULT 'nao_identificado',
                status    TEXT DEFAULT 'recebido',
                criado_em TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        for col in ["tipo", "ggv"]:
            try:
                con.execute(f"ALTER TABLE documentos ADD COLUMN {col} TEXT")
            except Exception:
                pass

def ja_existe(hash_arquivo):
    with sqlite3.connect(DB_PATH) as con:
        return con.execute("SELECT id FROM documentos WHERE hash = ?", (hash_arquivo,)).fetchone()

def registrar(nome, caminho, hash_arquivo, tipo, ggv):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "INSERT INTO documentos (nome, caminho, hash, tipo, ggv) VALUES (?,?,?,?,?)",
            (nome, str(caminho), hash_arquivo, tipo, ggv)
        )
        return cur.lastrowid

def atualizar(doc_id, **campos):
    sets = ", ".join(f"{k}=?" for k in campos)
    with sqlite3.connect(DB_PATH) as con:
        con.execute(f"UPDATE documentos SET {sets} WHERE id=?", (*campos.values(), doc_id))

def parse_resposta(texto):
    """Extrai tipo e GGV das primeiras linhas da resposta do Claude."""
    tipo, ggv = "nao_relacionado", "nao_identificado"
    linhas = texto.strip().splitlines()
    corpo = []
    for linha in linhas:
        if linha.startswith("TIPO:"):
            tipo = linha.split(":", 1)[1].strip()
        elif linha.startswith("GGV:"):
            ggv = linha.split(":", 1)[1].strip()
        else:
            corpo.append(linha)
    return tipo, ggv, "\n".join(corpo).strip()

def montar_teclado(doc_id, tipo, ggv):
    emoji_tipo = TIPOS.get(tipo, ("📄", tipo))[0]
    label_ggv = ggv if ggv != "nao_identificado" else "❓GGV"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirmar",        callback_data=f"ok:{doc_id}:{tipo}:{ggv}"),
            InlineKeyboardButton(f"🔄 {emoji_tipo}Tipo", callback_data=f"sel_tipo:{doc_id}:{tipo}:{ggv}"),
        ],
        [
            InlineKeyboardButton(f"🏗 {label_ggv}",     callback_data=f"sel_ggv:{doc_id}:{tipo}:{ggv}"),
            InlineKeyboardButton("❌ Cancelar",          callback_data=f"cancelar:{doc_id}"),
        ]
    ])

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
            f"⚠️ Formato *{mime}* ainda não é suportado.\n\n"
            "Aceito hoje:\n"
            "• 📷 Foto (JPEG, PNG, GIF, WEBP)\n"
            "• 📄 PDF\n\n"
            "CSV e Excel chegam nas próximas versões.",
            parse_mode="Markdown"
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
    doc_id = registrar(nome, caminho, hash_arquivo, tipo, ggv)

    emoji, label_tipo = TIPOS.get(tipo, ("📄", tipo))
    label_ggv = ggv if ggv != "nao_identificado" else "❓ GGV não identificado"

    await update.message.reply_text(
        f"{emoji} *{label_tipo}* | 🏗 *{label_ggv}*\n\n{corpo}\n\n_Confirmar ou ajustar?_",
        parse_mode="Markdown",
        reply_markup=montar_teclado(doc_id, tipo, ggv)
    )

async def responder_botao(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    partes = query.data.split(":")
    acao = partes[0]

    if acao == "ok":
        _, doc_id, tipo, ggv = partes
        if ggv == "nao_identificado":
            await query.answer("⚠️ Selecione o GGV antes de confirmar.", show_alert=True)
            return
        atualizar(int(doc_id), status="confirmado")
        emoji, label = TIPOS.get(tipo, ("📄", tipo))
        await query.edit_message_text(f"✅ Confirmado: {emoji} {label} | 🏗 {ggv}")

    elif acao == "cancelar":
        doc_id = partes[1]
        atualizar(int(doc_id), status="cancelado")
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
            f"{emoji} *{label}* | 🏗 *{label_ggv}*\n\n_Tipo corrigido. Confirmar?_",
            parse_mode="Markdown",
            reply_markup=montar_teclado(int(doc_id), novo_tipo, ggv)
        )

    elif acao == "sel_ggv":
        _, doc_id, tipo, ggv = partes
        botoes = [[InlineKeyboardButton(g, callback_data=f"set_ggv:{doc_id}:{tipo}:{g}")]
                  for g in GGVS]
        botoes.append([InlineKeyboardButton("❓ Não identificado", callback_data=f"set_ggv:{doc_id}:{tipo}:nao_identificado")])
        await query.edit_message_reply_markup(InlineKeyboardMarkup(botoes))

    elif acao == "set_ggv":
        _, doc_id, tipo, novo_ggv = partes
        atualizar(int(doc_id), ggv=novo_ggv)
        emoji, label = TIPOS.get(tipo, ("📄", tipo))
        label_ggv = novo_ggv if novo_ggv != "nao_identificado" else "❓ GGV não identificado"
        await query.edit_message_text(
            f"{emoji} *{label}* | 🏗 *{label_ggv}*\n\n_GGV corrigido. Confirmar?_",
            parse_mode="Markdown",
            reply_markup=montar_teclado(int(doc_id), tipo, novo_ggv)
        )

init_db()
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, receber_arquivo))
app.add_handler(CallbackQueryHandler(responder_botao))
app.add_handler(MessageHandler(filters.ALL, lambda u, c: u.message.reply_text("Recebi. Ainda não sei o que fazer com isso.") if u.effective_user.id == DONO_ID else None))
app.run_polling()
