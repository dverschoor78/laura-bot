"""
backfill_itens_pedido.py — popula itens_pedido a partir dos pedidos já cadastrados, lendo o
texto de dados_claude com a mesma lógica de _itens() usada em bot.py. Roda uma vez, ou sempre
que precisar recompor a tabela a partir do texto original (nunca apaga o texto em si).
"""
import re
import sqlite3
from pathlib import Path

DB_PATH = Path("data/laura.db")

ITEM_RE = re.compile(
    r"^\d+\.\s+(.+?)\s+\(([0-9,.]+)\s+([A-Za-zÀ-ÿ]{1,4}[²³0-9]{0,2})\)\s*[—–\-]+\s*R\$\s*([0-9.,]+)"
    r"(?:\s*cada\s*=\s*R\$\s*([0-9.,]+))?",
    re.IGNORECASE,
)


def _parse_brl(s):
    s = s.strip().replace(" ", "")
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    if "." in s:
        if len(s.rsplit(".", 1)[1]) == 3:
            return float(s.replace(".", ""))
    return float(s.replace(",", "."))


def _parse_qtde(s):
    """Quantidade nunca usa a regra de milhar — "." é sempre decimal aqui (ex: '12.000' = doze)."""
    s = s.strip().replace(" ", "")
    if not s:
        return 0.0
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    return float(s)


def _fmt_brl(v):
    s = f"{v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def itens(dados):
    resultado, capturando = [], False
    for linha in dados.splitlines():
        stripped = linha.strip().lstrip("- *")
        if re.match(r"^(itens|materiais)", stripped, re.IGNORECASE) and ":" in stripped:
            capturando = True
            inline = stripped.split(":", 1)[1].strip().strip("*").strip()
            if not inline:
                continue
            stripped = inline
        if capturando:
            if not stripped:
                continue
            if re.match(r"^(valor total|condição|condicao|prazo|validade|observ)", stripped, re.IGNORECASE):
                break
            m = ITEM_RE.match(stripped)
            if m:
                desc, qtde_str, und, val1, val2 = m.groups()
                qtde_v = _parse_qtde(qtde_str)
                if val2:
                    unit_v = _parse_brl(val1)
                    total_v = round(qtde_v * unit_v, 2)
                else:
                    total_v = _parse_brl(val1)
                    unit_v = total_v / qtde_v if qtde_v else 0
                resultado.append({
                    "desc": desc.strip(), "und": und.upper(), "qtde": qtde_str,
                    "unit": _fmt_brl(unit_v), "total": _fmt_brl(total_v), "_total_v": total_v,
                })
            elif stripped:
                resultado.append(stripped)
    return resultado


def salvar_itens_pedido(con, pfm_codigo, lista_itens):
    con.execute("DELETE FROM itens_pedido WHERE pfm_codigo=?", (pfm_codigo,))
    for i, item in enumerate(lista_itens, start=1):
        if isinstance(item, dict):
            con.execute(
                "INSERT INTO itens_pedido "
                "(pfm_codigo, numero, descricao, unidade, quantidade, valor_unitario, valor_total) "
                "VALUES (?,?,?,?,?,?,?)",
                (pfm_codigo, i, item["desc"], item["und"],
                 _parse_qtde(item["qtde"]), _parse_brl(item["unit"]), item["_total_v"])
            )
        else:
            con.execute(
                "INSERT INTO itens_pedido (pfm_codigo, numero, descricao) VALUES (?,?,?)",
                (pfm_codigo, i, str(item))
            )


def main():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.execute("""
        CREATE TABLE IF NOT EXISTS itens_pedido (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            pfm_codigo            TEXT NOT NULL,
            numero                INTEGER,
            descricao             TEXT NOT NULL,
            unidade               TEXT,
            quantidade            REAL,
            valor_unitario        REAL,
            valor_total           REAL,
            insumo_sinapi_codigo  INTEGER,
            criado_em             TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    pedidos = con.execute("""
        SELECT l.pfm_codigo, d.dados_claude
        FROM lancamentos l JOIN documentos d ON d.id = l.doc_id
        ORDER BY l.pfm_codigo
    """).fetchall()

    total_itens = 0
    for pfm_codigo, dados in pedidos:
        lista = itens(dados)
        salvar_itens_pedido(con, pfm_codigo, lista)
        con.commit()
        estruturados = sum(1 for it in lista if isinstance(it, dict))
        print(f"{pfm_codigo}: {len(lista)} itens ({estruturados} estruturados)")
        total_itens += len(lista)

    print(f"\nOK {len(pedidos)} pedidos processados, {total_itens} itens gravados no total")


if __name__ == "__main__":
    main()
