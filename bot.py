import os
import hashlib
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()
TOKEN    = os.environ["TELEGRAM_BOT_TOKEN"]
DONO_ID  = int(os.environ["TELEGRAM_USER_ID"])
UPLOADS  = Path("data/uploads")
UPLOADS.mkdir(parents=True, exist_ok=True)

hashes_vistos = set()  # memória simples enquanto o bot estiver rodando

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
    elif update.message.document:
        tg_file = await update.message.document.get_file()
        nome = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{update.message.document.file_name}"
    else:
        await update.message.reply_text("Recebi. Ainda não sei o que fazer com isso.")
        return

    conteudo = await tg_file.download_as_bytearray()
    hash_arquivo = hashlib.sha256(conteudo).hexdigest()

    if hash_arquivo in hashes_vistos:
        await update.message.reply_text(f"⚠️ Este arquivo já foi recebido antes. Ignorando.")
        return

    hashes_vistos.add(hash_arquivo)
    (UPLOADS / nome).write_bytes(conteudo)
    await update.message.reply_text(f"✅ Arquivo salvo: {nome}\nHash: {hash_arquivo[:16]}...")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, receber_arquivo))
app.add_handler(MessageHandler(filters.ALL, lambda u, c: u.message.reply_text("Recebi. Ainda não sei o que fazer com isso.") if u.effective_user.id == DONO_ID else None))
app.run_polling()
