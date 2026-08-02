#!/usr/bin/env bash
# Setup da Laura num container LXC Debian/Ubuntu limpo (rodar como root, de dentro de /opt/laura).
# Passo a passo completo: docs/DEPLOY.md
set -euo pipefail

echo "== Laura — setup do servidor =="

# 1. Python >= 3.12 (Debian 13 / Ubuntu 24.04 têm; Debian 12 NÃO — recriar o CT com template mais novo)
apt-get update
apt-get install -y python3 python3-venv git rclone fuse3
PYVER=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
    echo "ERRO: Python $PYVER encontrado, mas a Laura exige >= 3.12."
    echo "Solução: recriar o container com template Debian 13 (trixie) ou Ubuntu 24.04."
    exit 1
fi
echo "Python $PYVER OK"

# 2. Fuso horário — o banco usa datetime('now','localtime')
timedatectl set-timezone America/Sao_Paulo || true

# 3. Ambiente Python isolado + dependências
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r ../requirements.txt
.venv/bin/playwright install --with-deps chromium

# 4. Pastas de runtime
mkdir -p data logs

# 5. Units do systemd (não habilita ainda — faltam .env, banco e rclone config)
cp deploy/laura.service deploy/rclone-onedrive.service /etc/systemd/system/
systemctl daemon-reload

echo
echo "== Setup concluído. Próximos passos (docs/DEPLOY.md, seções 4 em diante): =="
echo "  1. rclone config              (criar o remote 'onedrive')"
echo "  2. copiar .env e data/        (do Windows, via Tailscale/scp)"
echo "  3. migrar caminhos do banco   (scripts/migrar_caminhos_obras.py --aplicar)"
echo "  4. testar com LAURA_ENV=test"
echo "  5. systemctl enable --now rclone-onedrive laura"
