"""
main.py — Ponto de entrada do bot Laura.

Inicializa o banco, configura os handlers e inicia o polling.
"""

import sys
from loguru import logger
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from app.config import TELEGRAM_BOT_TOKEN, LOG_LEVEL, LOGS_DIR
from app.db.setup import initialize_database
from app.bot.handlers.start import cmd_start, cmd_ajuda, cmd_pendentes
from app.bot.handlers.documento import handler_documento
from app.bot.handlers.callbacks import handler_callback


def configurar_logs():
    """Configura loguru: console + arquivo com rotação."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger.remove()  # remove o handler padrão

    # Console
    logger.add(
        sys.stdout,
        level=LOG_LEVEL,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
        colorize=True,
    )

    # Arquivo com rotação (novo arquivo a cada dia, guarda 30 dias)
    logger.add(
        LOGS_DIR / "laura.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{line} | {message}",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
    )

    # Arquivo separado só para auditoria financeira
    logger.add(
        LOGS_DIR / "auditoria.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
        filter=lambda record: "AUDITORIA" in record["message"],
        rotation="1 month",
        retention="1 year",
        encoding="utf-8",
    )


def main():
    configurar_logs()
    logger.info("Projeto Laura iniciando...")

    # Inicializa o banco de dados (cria tabelas se necessário)
    logger.info("Inicializando banco de dados...")
    initialize_database()

    # Cria a aplicação do bot
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # ----- Registra handlers -----

    # Comandos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))
    app.add_handler(CommandHandler("pendentes", cmd_pendentes))

    # Arquivos recebidos (foto, documento, vídeo não aceito)
    app.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.ALL, handler_documento)
    )

    # Botões inline (confirmar/cancelar)
    app.add_handler(CallbackQueryHandler(handler_callback))

    logger.info("Bot Laura pronto. Aguardando mensagens...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
