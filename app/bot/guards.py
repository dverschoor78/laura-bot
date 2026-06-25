"""
guards.py — Decoradores de segurança para handlers do bot.

O bot só aceita mensagens do TELEGRAM_USER_ID configurado no .env.
Qualquer outro usuário recebe uma mensagem de acesso negado.
"""

import functools
from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from app.config import TELEGRAM_USER_ID


def apenas_dono(func):
    """
    Decorador que bloqueia qualquer usuário que não seja o dono do bot.
    Usar em todos os handlers do Telegram.
    """
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != TELEGRAM_USER_ID:
            logger.warning(f"Acesso negado para user_id={user_id}")
            await update.effective_message.reply_text(
                "⛔ Acesso não autorizado."
            )
            return
        return await func(update, context)
    return wrapper
