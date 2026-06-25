"""
setup.py — Inicializa o banco de dados rodando as migrations.

Chamado automaticamente na inicialização do bot (app/bot/main.py).
Seguro de chamar múltiplas vezes — verifica o que já foi executado.
"""

from pathlib import Path
from loguru import logger

from app.db.connection import get_connection

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def initialize_database():
    """
    Roda todas as migrations pendentes em ordem alfabética.
    Registra cada migration em _migrations para não repetir.
    """
    with get_connection() as conn:
        # Garante que a tabela de controle existe
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                nome         TEXT UNIQUE NOT NULL,
                executado_em TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

    # Pega migrations já executadas
    with get_connection() as conn:
        rows = conn.execute("SELECT nome FROM _migrations").fetchall()
        executadas = {row["nome"] for row in rows}

    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    novas = 0

    for sql_file in sql_files:
        nome = sql_file.stem
        if nome in executadas:
            logger.debug(f"Migration '{nome}' já executada, pulando.")
            continue

        logger.info(f"Executando migration: {nome}")
        sql = sql_file.read_text(encoding="utf-8")

        with get_connection() as conn:
            conn.executescript(sql)
            conn.execute(
                "INSERT OR IGNORE INTO _migrations (nome) VALUES (?)", (nome,)
            )

        novas += 1
        logger.info(f"Migration '{nome}' concluída.")

    if novas == 0:
        logger.debug("Banco de dados já está atualizado.")
    else:
        logger.info(f"{novas} migration(s) executada(s).")
