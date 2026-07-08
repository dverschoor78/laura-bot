"""Parsing e exibição de NF-e. Ver docstring de nfe/__init__.py.

_campo/_campo_vazio/_fmt_brl são cópias intencionais dos utilitários de
bot.py (não a fonte única) — mantidas aqui para este módulo não depender de
bot.py (mesma convenção de financeiro/lancamento.py, que também não importa
de bot.py). São utilitários genéricos e estáveis, não específicos de NF-e.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

_MARCADORES_VAZIO = ("não identificad", "nao identificad", "não especificad", "nao especificad",
                     "não informad", "nao informad", "não encontrad", "nao encontrad")
_VALORES_VAZIO = {"n/a", "—", "-", ""}

def _campo_vazio(val: str) -> bool:
    """True se o valor extraído é um marcador de 'não achei', em qualquer gênero/frase
    (ex: 'Não identificada', 'não identificado no documento') — não só o masculino exato."""
    v = val.strip().lower()
    return v in _VALORES_VAZIO or v.startswith(_MARCADORES_VAZIO)

def _campo(dados, nome):
    for linha in dados.splitlines():
        stripped = linha.strip().lstrip("- *")
        if stripped.lower().startswith(nome.lower() + ":"):
            val = stripped.split(":", 1)[1].strip().strip("*").strip()
            if not _campo_vazio(val):
                return val
    return "A PREENCHER"

def _fmt_brl(v):
    s = f"{v:,.2f}"                                        # "6,292.93"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")  # "6.292,93"

def parse_nfe(corpo: str) -> dict:
    """Extrai campos da NF-e do texto retornado pelo Claude."""
    valor_str = _campo(corpo, "Valor total")
    try:
        valor_v = float(valor_str.replace("R$", "").replace(".", "").replace(",", ".").strip())
    except Exception:
        valor_v = None
    return {
        "numero":    _campo(corpo, "Número da NF"),
        "cnpj":      _campo(corpo, "CNPJ/CPF do emitente"),
        "emitente":  _campo(corpo, "Nome do emitente"),
        "valor_fmt": valor_str,
        "valor_v":   valor_v,
        "data":      _campo(corpo, "Data de emissão"),
        "descricao": _campo(corpo, "Descrição do serviço/produto"),
    }

def mostrar_nfe(dados: dict, candidatos: list) -> str:
    linhas = ["NF-e identificada.\n"]
    if dados["emitente"] != "A PREENCHER":
        linhas.append(f"{dados['emitente']} — {dados['valor_fmt']}")
    else:
        linhas.append(dados["valor_fmt"])
    if dados["numero"]   != "A PREENCHER": linhas.append(f"NF {dados['numero']}")
    if dados["data"]     != "A PREENCHER": linhas.append(dados["data"])
    if dados["descricao"] != "A PREENCHER": linhas.append(dados["descricao"])
    linhas.append("")
    if not candidatos:
        linhas.append("Nenhum pedido pago sem NF-e encontrado.")
        return "\n".join(linhas)
    fortes = [c for c in candidatos if c["score"] > 0]
    if fortes:
        linhas.append("A qual pedido vincular esta NF-e?\n")
        for c in fortes:
            valor_fmt = f"R$ {_fmt_brl(c['valor_lanc'])}" if c["valor_lanc"] else "—"
            linhas.append(f"🟢 #{c['pfm_codigo']} · {c['fornecedor']} · {valor_fmt}")
    else:
        linhas.append("Escolha o pedido manualmente:\n")
        for c in candidatos:
            valor_fmt = f"R$ {_fmt_brl(c['valor_lanc'])}" if c["valor_lanc"] else "—"
            linhas.append(f"🟢 #{c['pfm_codigo']} · {c['fornecedor']} · {valor_fmt}")
    return "\n".join(linhas)

def teclado_candidatos_nfe(doc_id: int, candidatos: list):
    botoes = []
    for c in candidatos:
        botoes.append([InlineKeyboardButton(
            f"#{c['pfm_codigo']}",
            callback_data=f"nfe_confirmar:{doc_id}:{c['pfm_codigo']}"
        )])
    botoes.append([InlineKeyboardButton("✖ Nenhum destes — descartar arquivo",
                                        callback_data=f"nfe_cancelar:{doc_id}")])
    return InlineKeyboardMarkup(botoes)
