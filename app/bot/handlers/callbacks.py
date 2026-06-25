"""
callbacks.py — Responde aos botões inline (confirmar, cancelar, corrigir).

Formato do callback_data: "{prefixo}:{acao}:{id}"
Exemplos:
  "doc:confirmar:42"
  "doc:cancelar:42"
  "doc:corrigir:42"
"""

import json
from loguru import logger
from telegram import Update
from telegram.ext import ContextTypes

from app.db.connection import get_connection
from app.bot.guards import apenas_dono


@apenas_dono
async def handler_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Roteador de callbacks — delega para o handler correto pelo prefixo."""
    query = update.callback_query
    await query.answer()  # remove o "carregando" do botão

    try:
        prefixo, acao, id_str = query.data.split(":")
        registro_id = int(id_str)
    except (ValueError, AttributeError):
        logger.warning(f"Callback inválido recebido: {query.data}")
        await query.edit_message_text("❌ Ação inválida.")
        return

    if prefixo == "doc":
        await _callback_documento(query, acao, registro_id)
    else:
        logger.warning(f"Prefixo de callback desconhecido: {prefixo}")
        await query.edit_message_text("❌ Ação não reconhecida.")


async def _callback_documento(query, acao: str, doc_id: int):
    """Processa confirmação/cancelamento de um documento."""

    if acao == "confirmar":
        with get_connection() as conn:
            conn.execute(
                "UPDATE documentos SET status='confirmado' WHERE id=?",
                (doc_id,)
            )
            # Registra auditoria
            conn.execute(
                """
                INSERT INTO auditoria (tabela, registro_id, acao, telegram_user_id)
                VALUES ('documentos', ?, 'confirmado', ?)
                """,
                (doc_id, str(query.from_user.id))
            )

        logger.info(f"AUDITORIA | documento #{doc_id} confirmado pelo usuário {query.from_user.id}")
        await query.edit_message_text(
            f"✅ Documento #{doc_id} confirmado e registrado.\n\n"
            "_(As próximas fases irão gerar o PFM e registrar o lançamento)_",
            parse_mode="Markdown",
        )

    elif acao == "cancelar":
        with get_connection() as conn:
            conn.execute(
                "UPDATE documentos SET status='descartado' WHERE id=?",
                (doc_id,)
            )
            conn.execute(
                """
                INSERT INTO auditoria (tabela, registro_id, acao, telegram_user_id)
                VALUES ('documentos', ?, 'descartado', ?)
                """,
                (doc_id, str(query.from_user.id))
            )

        logger.info(f"AUDITORIA | documento #{doc_id} descartado pelo usuário {query.from_user.id}")
        await query.edit_message_text(f"❌ Documento #{doc_id} descartado.")

    elif acao == "corrigir":
        await query.edit_message_text(
            f"✏️ Correção do documento #{doc_id}:\n\n"
            "Esta funcionalidade será implementada na Fase 2.\n"
            "Por enquanto, cancele e reenvie o documento com os dados corretos.",
        )
