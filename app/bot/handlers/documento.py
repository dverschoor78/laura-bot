"""
documento.py — Handler principal do MVP: recebe foto ou PDF.

Fluxo:
1. Recebe o arquivo do Telegram
2. Baixa e salva em data/uploads/
3. Calcula hash SHA256 (detecta duplicatas)
4. Registra no SQLite como 'recebido'
5. Envia para Claude API
6. Mostra extração para o usuário
7. Aguarda confirmação via botões inline
"""

import json
from pathlib import Path
from datetime import datetime
from loguru import logger
from telegram import Update, Message
from telegram.ext import ContextTypes

from app.config import UPLOADS_DIR
from app.bot.guards import apenas_dono
from app.bot.keyboards import teclado_confirmacao_com_correcao
from app.db.connection import get_connection
from app.extractors.claude_extractor import extrair_documento
from app.utils.hasher import sha256_bytes
from app.utils.formatters import formatar_moeda, formatar_cnpj


@apenas_dono
async def handler_documento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe foto ou documento PDF e inicia o fluxo de extração."""
    message = update.message
    await message.reply_text("📄 Recebi o documento. Analisando...")

    # ----- 1. Baixa o arquivo do Telegram -----
    file_bytes, file_name, file_id, mime_type = await _baixar_arquivo(message)
    if file_bytes is None:
        await message.reply_text("❌ Não consegui baixar o arquivo. Tente novamente.")
        return

    # ----- 2. Calcula hash (idempotência) -----
    hash_sha256 = sha256_bytes(file_bytes)

    # ----- 3. Verifica duplicata -----
    with get_connection() as conn:
        existente = conn.execute(
            "SELECT id, status, criado_em FROM documentos WHERE hash_sha256 = ?",
            (hash_sha256,)
        ).fetchone()

    if existente:
        data = existente["criado_em"][:10]
        await message.reply_text(
            f"⚠️ Este arquivo já foi processado em {data}.\n"
            f"ID do registro: #{existente['id']} (status: {existente['status']})\n\n"
            "Se precisar reprocessar, entre em contato."
        )
        return

    # ----- 4. Salva arquivo em disco -----
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = Path(file_name).suffix if file_name else (".jpg" if "image" in (mime_type or "") else ".pdf")
    caminho = UPLOADS_DIR / f"{timestamp}_{hash_sha256[:8]}{ext}"
    caminho.write_bytes(file_bytes)
    logger.info(f"Arquivo salvo: {caminho}")

    # ----- 5. Registra no banco como 'recebido' -----
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documentos (tipo, nome_arquivo, caminho_salvo, hash_sha256,
                                    telegram_file_id, telegram_message_id, status)
            VALUES (?, ?, ?, ?, ?, ?, 'recebido')
            """,
            ("desconhecido", file_name, str(caminho), hash_sha256,
             file_id, message.message_id)
        )
        doc_id = cursor.lastrowid

    logger.info(f"Documento #{doc_id} registrado no banco (hash: {hash_sha256[:16]}...)")

    # ----- 6. Envia para Claude API -----
    try:
        await message.reply_text("🤖 Extraindo dados com IA...")
        dados = await extrair_documento(file_bytes, mime_type or "image/jpeg")
    except Exception as e:
        logger.error(f"Erro na extração Claude (doc #{doc_id}): {e}")
        with get_connection() as conn:
            conn.execute(
                "UPDATE documentos SET status='erro', erro_extracao=? WHERE id=?",
                (str(e), doc_id)
            )
        await message.reply_text(
            "❌ Não consegui extrair os dados deste documento.\n"
            "Tente reenviar com melhor iluminação ou em PDF."
        )
        return

    # ----- 7. Salva extração no banco -----
    dados_json = json.dumps(dados, ensure_ascii=False)
    with get_connection() as conn:
        conn.execute(
            "UPDATE documentos SET dados_extraidos=?, status='processando', processado_em=datetime('now','localtime') WHERE id=?",
            (dados_json, doc_id)
        )

    # ----- 8. Monta preview para o usuário -----
    preview = _formatar_preview(dados, doc_id)

    # ----- 9. Envia preview e pede confirmação -----
    await message.reply_text(
        preview,
        parse_mode="Markdown",
        reply_markup=teclado_confirmacao_com_correcao("doc", doc_id),
    )


async def _baixar_arquivo(message: Message):
    """Baixa foto ou documento do Telegram. Retorna (bytes, nome, file_id, mime_type)."""
    try:
        if message.photo:
            # Pega a maior resolução disponível
            photo = message.photo[-1]
            tg_file = await photo.get_file()
            file_bytes = await tg_file.download_as_bytearray()
            return bytes(file_bytes), "foto.jpg", photo.file_id, "image/jpeg"

        elif message.document:
            doc = message.document
            tg_file = await doc.get_file()
            file_bytes = await tg_file.download_as_bytearray()
            return bytes(file_bytes), doc.file_name, doc.file_id, doc.mime_type

    except Exception as e:
        logger.error(f"Erro ao baixar arquivo do Telegram: {e}")

    return None, None, None, None


def _formatar_preview(dados: dict, doc_id: int) -> str:
    """Formata os dados extraídos para exibição ao usuário."""
    linhas = [f"📋 *Dados extraídos* (#{doc_id})\n"]

    tipo = dados.get("tipo", "desconhecido")
    linhas.append(f"Tipo: *{tipo}*\n")

    # Fornecedor
    if forn := dados.get("fornecedor"):
        linhas.append(f"*Fornecedor:* {forn}")
    if cnpj := dados.get("cnpj"):
        linhas.append(f"*CNPJ/CPF:* {formatar_cnpj(cnpj)}")

    # Valor total
    if valor := dados.get("valor_total"):
        linhas.append(f"*Valor total:* {formatar_moeda(float(valor))}")

    # Condições de pagamento
    if cond := dados.get("condicao_pagamento"):
        linhas.append(f"*Condição:* {cond}")

    # Itens (resumo)
    itens = dados.get("itens", [])
    if itens:
        linhas.append(f"\n*Itens ({len(itens)}):*")
        for item in itens[:5]:  # mostra até 5 itens
            desc = item.get("descricao", "?")[:40]
            val = formatar_moeda(float(item["valor_total"])) if item.get("valor_total") else ""
            linhas.append(f"  • {desc} {val}")
        if len(itens) > 5:
            linhas.append(f"  ... e mais {len(itens) - 5} item(ns)")

    linhas.append("\n*Tudo certo?*")
    return "\n".join(linhas)
