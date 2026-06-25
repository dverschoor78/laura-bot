"""
formatters.py — Funções de formatação para exibição ao usuário.
"""

from datetime import datetime


def formatar_moeda(valor: float | None) -> str:
    """Formata valor numérico como moeda brasileira. Ex: 4904.69 → 'R$ 4.904,69'"""
    if valor is None:
        return "R$ —"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_cnpj(cnpj: str | None) -> str:
    """Formata CNPJ sem pontuação para exibição. Ex: '77488385000889' → '77.488.385/0008-89'"""
    if not cnpj:
        return "—"
    digits = "".join(c for c in cnpj if c.isdigit())
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"
    return cnpj


def formatar_data(data_str: str | None) -> str:
    """Converte data ISO (YYYY-MM-DD) para formato brasileiro (DD/MM/YYYY)."""
    if not data_str:
        return "—"
    try:
        dt = datetime.strptime(data_str[:10], "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return data_str


def limpar_cnpj(cnpj: str | None) -> str:
    """Remove formatação do CNPJ, deixa só os dígitos."""
    if not cnpj:
        return ""
    return "".join(c for c in cnpj if c.isdigit())
