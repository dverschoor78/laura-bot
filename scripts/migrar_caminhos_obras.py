"""Converte obras.pasta_onedrive de caminho absoluto do Windows pra caminho relativo.

Antes:  C:\\Users\\denni\\OneDrive\\00 Obras\\2026-06 GGV03
Depois: 00 Obras/2026-06 GGV03

O caminho relativo é resolvido em runtime contra ONEDRIVE_PATH do .env (ver
_raiz_obra() em bot.py) — o mesmo banco passa a funcionar no Windows
(ONEDRIVE_PATH=C:\\Users\\denni\\OneDrive) e no servidor Linux
(ONEDRIVE_PATH=/mnt/onedrive).

Uso:
    python scripts/migrar_caminhos_obras.py               # dry-run, só mostra
    python scripts/migrar_caminhos_obras.py --aplicar     # grava de verdade

Idempotente: caminho já relativo (ou vazio) é ignorado.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

PREFIXO_PADRAO = r"C:\Users\denni\OneDrive"


def migrar(db_path: str, prefixo: str, aplicar: bool) -> int:
    prefixo_norm = prefixo.replace("\\", "/").rstrip("/").lower()
    con = sqlite3.connect(db_path)
    obras = con.execute(
        "SELECT codigo, pasta_onedrive FROM obras WHERE pasta_onedrive != ''"
    ).fetchall()

    mudancas = []
    for codigo, pasta in obras:
        pasta_norm = pasta.replace("\\", "/")
        if pasta_norm.lower().startswith(prefixo_norm + "/"):
            novo = pasta_norm[len(prefixo_norm) + 1:]
            mudancas.append((codigo, pasta, novo))
        else:
            print(f"  {codigo}: já relativo ou fora do prefixo — mantido ({pasta!r})")

    if not mudancas:
        print("Nada a migrar.")
        con.close()
        return 0

    for codigo, antes, depois in mudancas:
        print(f"  {codigo}: {antes!r}\n      ->  {depois!r}")

    if aplicar:
        for codigo, _, depois in mudancas:
            con.execute(
                "UPDATE obras SET pasta_onedrive=? WHERE codigo=?", (depois, codigo)
            )
        con.commit()
        print(f"\n{len(mudancas)} obra(s) migrada(s). Lembre do ONEDRIVE_PATH no .env "
              "e de reiniciar o bot.")
    else:
        print(f"\nDry-run — nada gravado. Rode com --aplicar pra efetivar "
              f"({len(mudancas)} obra(s)).")
    con.close()
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default="data/laura.db", help="caminho do banco (padrão: data/laura.db)")
    ap.add_argument("--prefixo", default=PREFIXO_PADRAO,
                    help=f"prefixo absoluto a remover (padrão: {PREFIXO_PADRAO})")
    ap.add_argument("--aplicar", action="store_true", help="grava as mudanças (sem isso, dry-run)")
    args = ap.parse_args()
    if not Path(args.db).exists():
        sys.exit(f"Banco não encontrado: {args.db}")
    sys.exit(migrar(args.db, args.prefixo, args.aplicar))
