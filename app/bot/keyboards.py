"""
keyboards.py — Botões inline reutilizáveis.

Centraliza a criação de teclados para manter consistência visual.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def teclado_confirmacao(prefixo: str, doc_id: int) -> InlineKeyboardMarkup:
    """
    Teclado padrão de confirmação: ✅ Confirmar | ❌ Cancelar.

    prefixo: identifica o tipo de ação (ex: 'doc', 'pfm', 'pgto')
    doc_id: ID do registro no banco
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirmar", callback_data=f"{prefixo}:confirmar:{doc_id}"),
            InlineKeyboardButton("❌ Cancelar",  callback_data=f"{prefixo}:cancelar:{doc_id}"),
        ]
    ])


def teclado_confirmacao_com_correcao(prefixo: str, doc_id: int) -> InlineKeyboardMarkup:
    """
    Teclado de confirmação com opção de corrigir dados.
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirmar", callback_data=f"{prefixo}:confirmar:{doc_id}"),
            InlineKeyboardButton("✏️ Corrigir",  callback_data=f"{prefixo}:corrigir:{doc_id}"),
            InlineKeyboardButton("❌ Cancelar",  callback_data=f"{prefixo}:cancelar:{doc_id}"),
        ]
    ])
