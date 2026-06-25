"""
claude_extractor.py — Extração de dados de documentos via Claude API.

Recebe bytes de imagem ou PDF e retorna um dicionário estruturado com os dados.
Usa Claude com visão (multimodal) para entender documentos variados.
"""

import base64
import json
from loguru import logger
import anthropic

from app.config import CLAUDE_API_KEY, CLAUDE_MODEL


# Cliente Claude (reutilizado entre chamadas)
_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

# Prompt base para extração de orçamentos
_PROMPT_ORCAMENTO = """
Você está analisando um documento de orçamento, cotação ou pedido de compra de uma obra de construção civil no Brasil.

Extraia os seguintes dados e retorne SOMENTE um JSON válido, sem explicações:

{
  "tipo": "orcamento",
  "fornecedor": "razão social ou nome do fornecedor",
  "cnpj": "CNPJ ou CPF somente dígitos, sem formatação",
  "email": "email do fornecedor ou null",
  "whatsapp": "telefone do fornecedor ou null",
  "condicao_pagamento": "condição de pagamento (ex: À vista PIX, 30 dias, parcelado)",
  "prazo_entrega": "prazo de entrega descrito no documento ou null",
  "valor_total": 0.00,
  "observacoes": "observações importantes ou null",
  "itens": [
    {
      "ordem": 1,
      "descricao": "descrição do item",
      "unidade": "unidade (m², kg, sc, un, etc.)",
      "quantidade": 0.00,
      "valor_unitario": 0.00,
      "valor_total": 0.00
    }
  ]
}

Regras:
- Valores numéricos sempre como número (ex: 4904.69), nunca como string
- Se não encontrar um campo, use null
- CNPJ/CPF somente os dígitos (ex: "77488385000889")
- Retorne APENAS o JSON, sem markdown, sem explicação
"""

_PROMPT_COMPROVANTE = """
Você está analisando um comprovante de pagamento PIX brasileiro.

Extraia os seguintes dados e retorne SOMENTE um JSON válido, sem explicações:

{
  "tipo": "comprovante",
  "data_pagamento": "data no formato YYYY-MM-DD",
  "valor": 0.00,
  "nome_destino": "nome do destinatário",
  "cnpj_destino": "CNPJ ou CPF do destinatário somente dígitos",
  "chave_pix": "chave PIX usada (CNPJ, CPF, email, telefone ou aleatória)",
  "id_transacao": "ID/E2E da transação PIX se visível"
}

Regras:
- valor como número (ex: 4904.69)
- data no formato YYYY-MM-DD
- CNPJ/CPF somente dígitos
- Retorne APENAS o JSON
"""


async def extrair_documento(file_bytes: bytes, mime_type: str) -> dict:
    """
    Envia documento para Claude e retorna dicionário com dados extraídos.

    mime_type: 'image/jpeg', 'image/png', 'application/pdf'
    """
    logger.debug(f"Enviando para Claude ({CLAUDE_MODEL}), tamanho: {len(file_bytes)} bytes")

    # Determina o tipo de fonte para a API
    if mime_type == "application/pdf":
        source = {
            "type": "base64",
            "media_type": "application/pdf",
            "data": base64.standard_b64encode(file_bytes).decode("utf-8"),
        }
    else:
        # Garante mime_type válido para imagem
        img_type = mime_type if mime_type in ("image/jpeg", "image/png", "image/webp") else "image/jpeg"
        source = {
            "type": "base64",
            "media_type": img_type,
            "data": base64.standard_b64encode(file_bytes).decode("utf-8"),
        }

    # Primeiro tenta identificar o tipo de documento
    # Por simplicidade no MVP, assume orçamento e tenta comprovante se falhar
    prompt = _PROMPT_ORCAMENTO

    try:
        response = _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image" if mime_type != "application/pdf" else "document", "source": source},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )

        texto = response.content[0].text.strip()
        logger.debug(f"Resposta Claude: {texto[:200]}...")

        # Remove markdown code blocks se Claude os adicionou mesmo pedindo para não
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]

        dados = json.loads(texto)
        logger.info(f"Extração concluída: tipo={dados.get('tipo')}, fornecedor={dados.get('fornecedor')}")
        return dados

    except json.JSONDecodeError as e:
        logger.error(f"Claude retornou JSON inválido: {e}")
        raise ValueError(f"Não foi possível interpretar a resposta da IA: {e}")

    except anthropic.APIError as e:
        logger.error(f"Erro na API Claude: {e}")
        raise RuntimeError(f"Erro ao consultar IA: {e}")
