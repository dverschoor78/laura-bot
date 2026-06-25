"""
connection.py — Gerencia conexão com o banco SQLite.

Uso:
    from app.db.connection import get_connection

    with get_connection() as conn:
        conn.execute("SELECT ...")
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from loguru import logger

from app.config import DB_PATH


def _ensure_db_dir():
    """Cria o diretório do banco se não existir."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def get_raw_connection() -> sqlite3.Connection:
    """
    Retorna uma conexão SQLite configurada.
    Use preferencialmente via get_connection() (context manager).
    """
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row   # permite acessar colunas por nome: row["campo"]
    conn.execute("PRAGMA journal_mode=WAL")   # melhor performance com leituras simultâneas
    conn.execute("PRAGMA foreign_keys=ON")    # garante integridade referencial
    return conn


@contextmanager
def get_connection():
    """
    Context manager para conexão SQLite.
    Faz commit automático ao sair; rollback em caso de erro.

    Exemplo:
        with get_connection() as conn:
            conn.execute("INSERT INTO ...")
    """
    conn = get_raw_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro no banco de dados, rollback realizado: {e}")
        raise
    finally:
        conn.close()
