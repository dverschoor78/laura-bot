import os
import hashlib
import sqlite3
import base64
import anthropic
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()
TOKEN       = os.environ["TELEGRAM_BOT_TOKEN"]
DONO_ID     = int(os.environ["TELEGRAM_USER_ID"])
CLAUDE_KEY  = os.environ["CLAUDE_API_KEY"]
UPLOADS     = Path("data/uploads")
DB_PATH     = Path("data/laura.db")
UPLOADS.mkdir(parents=True, exist_ok=True)

claude = anthropic.Anthropic(api_key=CLAUDE_KEY)

PROMPT = """
Analise este documento de obra (orçamento, cotação ou comprovante de pagamento).
Extraia e responda em português, de forma simples e direta:

- Tipo: (orçamento / comprovante de pagamento / outro)
- Fornecedor:
- CNPJ/CPF:
- Itens principais: (liste até 5)
- Valor total:
- Condição de pagamento:
- Observações importantes:

Se não encontrar algum campo, escreva "não identificado".
"""

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS documentos (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                nome      TEXT,
                caminho   TEXT,
                hash      TEXT UNIQUE,
                status    TEXT DEFAULT 'recebido',
                criado_em TEXT DEFAULT (datetime('now','localtime'))
            )
        """)

def ja_existe(hash_arquivo):
    with sqlite3.connect(DB_PATH) as con:
        return con.execute("SELECT id FROM documentos WHERE hash = ?", (hash_arquivo,)).fetchone()

def registrar(nome, caminho, hash_arquivo):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("INSERT INTO documentos (nome, caminho, hash) VALUES (?,?,?)",
                    (nome, str(caminho), hash_arquivo))

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
        mime = "image/jpeg"
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

    caminho = UPLOADS / nome
    caminho.write_bytes(conteudo)
    registrar(nome, caminho, hash_arquivo)
    await update.message.reply_text(f"✅ Arquivo salvo. Analisando com IA...")

    # Envia para Claude
    dados_b64 = base64.standard_b64encode(conteudo).decode()
    tipo_conteudo = "document" if mime == "application/pdf" else "image"

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

    await update.message.reply_text(f"🤖 O que encontrei:\n\n{resposta.content[0].text}")

init_db()
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, receber_arquivo))
app.add_handler(MessageHandler(filters.ALL, lambda u, c: u.message.reply_text("Recebi. Ainda não sei o que fazer com isso.") if u.effective_user.id == DONO_ID else None))
app.run_polling()
