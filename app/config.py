"""
config.py — Configuração centralizada do Projeto Laura.

Todas as variáveis de ambiente são lidas aqui, uma única vez.
O resto do código importa deste módulo, nunca lê os.getenv() diretamente.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega o .env da raiz do projeto
_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env")


def _require(name: str) -> str:
    """Lê variável de ambiente obrigatória. Lança erro claro se não existir."""
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(
            f"Variável de ambiente obrigatória não configurada: {name}\n"
            f"Verifique o arquivo .env (use .env.example como base)."
        )
    return value


# ----- Telegram -----
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_USER_ID: int = int(_require("TELEGRAM_USER_ID"))

# ----- Claude API -----
CLAUDE_API_KEY: str = _require("CLAUDE_API_KEY")
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

# ----- Caminhos -----
ONEDRIVE_PATH: Path = Path(os.getenv("ONEDRIVE_PATH", "/mnt/onedrive"))
DB_PATH: Path = Path(os.getenv("DB_PATH", str(_ROOT / "data" / "laura.db")))
UPLOADS_DIR: Path = _ROOT / "data" / "uploads"
LOGS_DIR: Path = _ROOT / "logs"

# ----- Projeto ativo -----
GGV_ATIVO: str = os.getenv("GGV_ATIVO", "GGV03")

# ----- Caminhos OneDrive do projeto ativo -----
GGV_AQUISICAO_DIR: Path = (
    ONEDRIVE_PATH / "00 Obras" / f"2026-06 {GGV_ATIVO}" / "04 Aquisição e Execução"
)
GGV_FINANCEIRO_DIR: Path = (
    ONEDRIVE_PATH / "00 Obras" / f"2026-06 {GGV_ATIVO}" / "01 Controle financeiro"
)
GGV_EXTRATOS_DIR: Path = GGV_FINANCEIRO_DIR / "Extratos"

# ----- Logs -----
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ----- Timeout de confirmação (segundos) -----
# Após este tempo sem resposta, a conversa é cancelada automaticamente
CONFIRMATION_TIMEOUT: int = int(os.getenv("CONFIRMATION_TIMEOUT", "600"))  # 10 minutos
