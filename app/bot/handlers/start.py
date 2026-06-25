"""
start.py — Handlers dos comandos básicos: /start, /ajuda, /pendentes.
"""

from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger

from app.config import TELEGRAM_USER_ID, GGV_ATIVO
from app.bot.guards import apenas_dono


@apenas_dono
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler do /start — apresentação do bot."""
    await update.message.reply_text(
        f"👷 *Projeto Laura — {GGV_ATIVO}*\n\n"
        "Olá, Dennis! Estou pronto para trabalhar.\n\n"
        "*O que posso fazer:*\n"
        "• Mande uma foto ou PDF de um orçamento\n"
        "• Mande um comprovante PIX\n"
        "• Mande o extrato mensal do Mercado Pago (CSV)\n\n"
        "Use /ajuda para ver todos os comandos.",
        parse_mode="Markdown",
    )
    logger.info(f"Bot iniciado pelo usuário {update.effective_user.id}")


@apenas_dono
async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler do /ajuda."""
    await update.message.reply_text(
        "📋 *Comandos disponíveis:*\n\n"
        "/start — Apresentação\n"
        "/pendentes — Lista lançamentos A PAGAR\n"
        "/ajuda — Esta mensagem\n\n"
        "*Envio direto:*\n"
        "• Foto ou PDF de orçamento → gera PFM\n"
        "• Foto de comprovante PIX → registra pagamento\n"
        "• CSV do Mercado Pago → conciliação mensal",
        parse_mode="Markdown",
    )


@apenas_dono
async def cmd_pendentes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler do /pendentes — lista lançamentos A PAGAR."""
    from app.db.connection import get_connection
    from app.utils.formatters import formatar_moeda, formatar_data

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT l.id, l.descricao, l.valor_a_pagar, l.data_vencimento,
                   f.razao_social as fornecedor
            FROM lancamentos l
            LEFT JOIN fornecedores f ON l.fornecedor_id = f.id
            WHERE l.status = 'a_pagar'
            ORDER BY l.data_vencimento ASC NULLS LAST, l.criado_em ASC
            LIMIT 20
        """).fetchall()

    if not rows:
        await update.message.reply_text("✅ Nenhum lançamento pendente.")
        return

    total = sum(r["valor_a_pagar"] or 0 for r in rows)
    linhas = [f"*Lançamentos A PAGAR — {GGV_ATIVO}*\n"]

    for r in rows:
        venc = formatar_data(r["data_vencimento"]) if r["data_vencimento"] else "sem venc."
        valor = formatar_moeda(r["valor_a_pagar"])
        forn = r["fornecedor"] or "?"
        linhas.append(f"• {forn[:25]}\n  {valor} — {venc}")

    linhas.append(f"\n*Total: {formatar_moeda(total)}*")

    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")
