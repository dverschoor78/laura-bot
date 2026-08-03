#!/usr/bin/env bash
# Setup da Laura num container LXC Debian limpo (rodar como root, de dentro de /opt/laura/deploy).
# Passo a passo completo: docs/DEPLOY.md
set -euo pipefail

echo "== Laura — setup do servidor =="

apt-get update
apt-get install -y python3 python3-venv git rclone fuse3
PYVER=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
    echo "ERRO: Python $PYVER encontrado, mas a Laura exige >= 3.12."
    exit 1
fi
echo "Python $PYVER OK"

timedatectl set-timezone America/Sao_Paulo || true

cd /opt/laura-bot/

python3 -m venv .venv

.venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
playwright install --with-deps chromium

mkdir -p data logs

cp -s deploy/laura-bot.service deploy/rclone-onedrive.service /etc/systemd/system/
systemctl daemon-reload

echo
echo "== Setup concluído. Próximos passos (docs/DEPLOY.md, seções 4 em diante): =="
echo "  1. rclone config              (criar o remote 'onedrive')"
echo "  2. copiar .env e data/        (do Windows, via Tailscale/scp)"
echo "  3. migrar caminhos do banco   (scripts/migrar_caminhos_obras.py --aplicar)"
echo "  4. testar com LAURA_ENV=test"
echo "  5. systemctl enable --now rclone-onedrive laura"
