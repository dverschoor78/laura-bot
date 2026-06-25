#!/bin/bash
# backup.sh — Backup diário do banco SQLite para o OneDrive
# Configurar no cron: 0 3 * * * /home/laura/laura-bot/scripts/backup.sh

set -e

# Carrega variáveis do .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$ROOT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

DB_PATH="${DB_PATH:-$ROOT_DIR/data/laura.db}"
ONEDRIVE_PATH="${ONEDRIVE_PATH:-/mnt/onedrive}"
BACKUP_DIR="$ONEDRIVE_PATH/01-Laura/backups"
DATA=$(date +%Y-%m-%d)
BACKUP_FILE="$BACKUP_DIR/laura-backup-$DATA.db"

# Cria pasta de backup se não existir
mkdir -p "$BACKUP_DIR"

# Verifica se o banco existe
if [ ! -f "$DB_PATH" ]; then
    echo "$(date) [ERRO] Banco não encontrado: $DB_PATH"
    exit 1
fi

# Copia o banco (sqlite3 usa WAL mode, cópia simples é segura)
cp "$DB_PATH" "$BACKUP_FILE"
echo "$(date) [OK] Backup salvo: $BACKUP_FILE"

# Remove backups com mais de 30 dias
find "$BACKUP_DIR" -name "laura-backup-*.db" -mtime +30 -delete
echo "$(date) [OK] Backups antigos (>30 dias) removidos"

# Conta backups restantes
COUNT=$(find "$BACKUP_DIR" -name "laura-backup-*.db" | wc -l)
echo "$(date) [INFO] Total de backups: $COUNT"
