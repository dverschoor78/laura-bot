"""
migrate.py — Inicializa o banco de dados e roda migrations pendentes.

Uso:
    python scripts/migrate.py

Roda todos os arquivos .sql de app/db/migrations/ em ordem alfabética.
Registra cada migration na tabela _migrations para não rodar duas vezes.
"""

import sqlite3
import os
import sys
from pathlib import Path

# Garante que o script encontra o .env mesmo rodando de fora do diretório raiz
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

DB_PATH = os.getenv("DB_PATH", str(ROOT / "data" / "laura.db"))
MIGRATIONS_DIR = ROOT / "app" / "db" / "migrations"


def get_connection():
    os.makedirs(Path(DB_PATH).parent, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def run_migrations():
    conn = get_connection()
    cursor = conn.cursor()

    # Garante que a tabela de controle existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            nome         TEXT UNIQUE NOT NULL,
            executado_em TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.commit()

    # Lista migrations já executadas
    cursor.execute("SELECT nome FROM _migrations")
    executadas = {row[0] for row in cursor.fetchall()}

    # Roda migrations em ordem alfabética
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not sql_files:
        print("Nenhuma migration encontrada.")
        return

    novas = 0
    for sql_file in sql_files:
        nome = sql_file.stem  # ex: '001_initial'
        if nome in executadas:
            print(f"  [ok] {nome} — já executada, pulando")
            continue

        print(f"  [>>] {nome} — executando...")
        sql = sql_file.read_text(encoding="utf-8")
        cursor.executescript(sql)

        # Registra como executada (o script SQL já insere, mas garantimos aqui)
        cursor.execute(
            "INSERT OR IGNORE INTO _migrations (nome) VALUES (?)", (nome,)
        )
        conn.commit()
        novas += 1
        print(f"  [ok] {nome} — concluída")

    conn.close()
    if novas == 0:
        print("Banco já está atualizado. Nenhuma nova migration.")
    else:
        print(f"\n{novas} migration(s) executada(s) com sucesso.")
        print(f"Banco: {DB_PATH}")


if __name__ == "__main__":
    print(f"Projeto Laura — Migrations")
    print(f"Banco: {DB_PATH}")
    print("-" * 40)
    run_migrations()
