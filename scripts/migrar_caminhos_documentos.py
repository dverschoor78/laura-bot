"""Converte os caminhos do Windows guardados em documentos (caminho e caminho_pfm) para os do
servidor — o formato que a Laura grava desde que passou a rodar nele (2026-08-07).

Antes:  data\\uploads\\20260701_173422.jpg
        C:\\Users\\denni\\OneDrive\\00 Obras\\2026-06 GGV03\\04 Compras\\GGV03-004 - ....docx
Depois: data/uploads/20260701_173422.jpg
        /mnt/onedrive/00 Obras/2026-06 GGV03/04 Compras/GGV03-004 - ....pdf

Sem isso, o cockpit dos pedidos criados no Windows mostra "Nenhum arquivo disponível": o
servidor não acha o arquivo pelo caminho antigo. Só troca quando o arquivo existe no destino; o
PDF do pedido gravado como .docx (o DOCX saiu do fluxo em 2026-07-02) passa para o .pdf de mesmo
nome, se ele existir. O que não existe fica como está e é listado.

Uso (no servidor, dentro de /opt/laura-bot — "data/uploads/..." é relativo a ela):
    .venv/bin/python scripts/migrar_caminhos_documentos.py              # dry-run, só mostra
    .venv/bin/python scripts/migrar_caminhos_documentos.py --aplicar    # grava de verdade

Idempotente: caminho que já é do servidor é ignorado.
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

PREFIXO_WINDOWS = r"C:\Users\denni\OneDrive"
ONEDRIVE_SERVIDOR = "/mnt/onedrive"


def convertido(caminho, prefixo_windows: str, onedrive: str):
    """Caminho do servidor correspondente a um caminho do Windows; None se não é do Windows ou
    não há para onde converter (outra pasta do Windows)."""
    if not caminho or ("\\" not in caminho and not re.match(r"^[A-Za-z]:", caminho)):
        return None
    c = caminho.replace("\\", "/")
    prefixo = prefixo_windows.replace("\\", "/").rstrip("/")
    if c.lower().startswith(prefixo.lower() + "/"):
        return f"{onedrive.rstrip('/')}/{c[len(prefixo) + 1:]}"
    if re.match(r"^[A-Za-z]:/", c):
        return None
    return c  # relativo (data/uploads/...), como o bot grava hoje


def migrar(db_path: str, prefixo_windows: str, onedrive: str, aplicar: bool) -> int:
    con = sqlite3.connect(db_path) if aplicar else sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    mudancas, faltam = [], []
    for coluna in ("caminho", "caminho_pfm"):
        for doc_id, tipo, antes in con.execute(
                f"SELECT id, tipo, {coluna} FROM documentos WHERE {coluna} IS NOT NULL ORDER BY id"):
            depois = convertido(antes, prefixo_windows, onedrive)
            if depois is None:
                continue
            if (not Path(depois).exists() and depois.lower().endswith(".docx")
                    and Path(depois[:-5] + ".pdf").exists()):
                depois = depois[:-5] + ".pdf"
            (mudancas if Path(depois).exists() else faltam).append((doc_id, tipo, coluna, antes, depois))

    for doc_id, tipo, coluna, _, depois in mudancas:
        print(f"  doc {doc_id} ({tipo}, {coluna}) -> {depois}")
    if faltam:
        print(f"\nNão encontrados no servidor — ficam como estão ({len(faltam)}):")
        for doc_id, tipo, coluna, antes, _ in faltam:
            print(f"  doc {doc_id} ({tipo}, {coluna}): {antes}")

    if aplicar and mudancas:
        for doc_id, _, coluna, antes, depois in mudancas:
            con.execute(f"UPDATE documentos SET {coluna}=? WHERE id=? AND {coluna}=?", (depois, doc_id, antes))
        con.commit()
        print(f"\n{len(mudancas)} caminho(s) migrado(s).")
    else:
        print(f"\nDry-run — nada gravado. {len(mudancas)} caminho(s) a migrar; rode com --aplicar.")
    con.close()
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default="data/laura.db", help="caminho do banco (padrão: data/laura.db)")
    ap.add_argument("--prefixo", default=PREFIXO_WINDOWS,
                    help=f"pasta do OneDrive no Windows (padrão: {PREFIXO_WINDOWS})")
    ap.add_argument("--onedrive", default=ONEDRIVE_SERVIDOR,
                    help=f"OneDrive montado no servidor (padrão: {ONEDRIVE_SERVIDOR})")
    ap.add_argument("--aplicar", action="store_true", help="grava as mudanças (sem isso, dry-run)")
    args = ap.parse_args()
    if not Path(args.db).exists():
        sys.exit(f"Banco não encontrado: {args.db}")
    sys.exit(migrar(args.db, args.prefixo, args.onedrive, args.aplicar))
