# Guia de Instalação — Projeto Laura

> Versão 1.0 — 2026-06-25

---

## Pré-requisitos

- Servidor Proxmox com pelo menos 4 GB RAM disponíveis e 2 vCPUs livres
- Acesso ao console do Proxmox (via web UI ou SSH)
- ISO do Ubuntu Server 24.04 LTS já no storage do Proxmox
- Token do Telegram Bot (criado via @BotFather)
- Chave da Claude API (console.anthropic.com)

---

## Fase 0 — Criar a VM no Proxmox

### 0.1 No console web do Proxmox (https://seu-proxmox:8006)

1. Clicar em **Create VM**
2. Preencher:
   - **VM ID:** próximo disponível (ex: 101)
   - **Name:** `laura`
3. **OS tab:**
   - ISO image: selecionar `ubuntu-24.04-live-server-amd64.iso`
   - Type: Linux
   - Version: 6.x - 2.6 Kernel
4. **System tab:** deixar padrão (BIOS: SeaBIOS)
5. **Disks tab:**
   - Bus: VirtIO Block
   - Size: **20 GB**
6. **CPU tab:**
   - Sockets: 1
   - Cores: **2**
7. **Memory tab:**
   - Memory: **2048 MB** (2 GB)
8. **Network tab:**
   - Bridge: vmbr0 (sua rede local)
   - Model: VirtIO
9. Confirmar e **Finish**

### 0.2 Iniciar a VM e instalar Ubuntu

1. Selecionar a VM, clicar em **Start**
2. Abrir **Console** (noVNC)
3. Seguir o instalador Ubuntu:
   - **Language:** English (facilita buscar erros no Google)
   - **Keyboard:** Portuguese (Brazil)
   - **Network:** configurar IP fixo (recomendado, ex: 192.168.1.200)
   - **Storage:** Use entire disk (sem LVM para simplificar)
   - **Profile:**
     - Name: `Dennis Verschoor`
     - Server name: `laura`
     - Username: `laura`
     - Password: (senha forte, anotar)
   - **SSH:** ✅ Install OpenSSH server
   - **Featured snaps:** não instalar nenhum
4. Aguardar instalação e reiniciar

---

## Fase 1 — Configuração inicial da VM

### Conectar via SSH

Do seu Windows (PowerShell ou terminal):
```bash
ssh laura@192.168.1.200
```

### 1.1 Atualizar o sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Instalar dependências do sistema

```bash
sudo apt install -y \
    git \
    python3-pip \
    python3-venv \
    libreoffice-core \
    libreoffice-writer \
    cifs-utils \
    curl \
    htop \
    nano
```

> **Por que libreoffice-core e libreoffice-writer?** Para converter DOCX em PDF em modo headless (sem interface gráfica). O comando `libreoffice --headless --convert-to pdf arquivo.docx` faz a conversão.

### 1.3 Configurar firewall

```bash
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status
```

Só a porta 22 (SSH) precisa estar aberta. O bot Telegram usa conexão de saída (polling), não precisa de porta aberta.

---

## Fase 2 — Montar OneDrive via SMB

O OneDrive está sincronizado no Windows do Dennis. Vamos acessar via compartilhamento de rede (SMB/CIFS).

### 2.1 No Windows — Compartilhar a pasta OneDrive

1. Abrir Explorador de Arquivos
2. Clicar com botão direito em `C:\Users\denni\OneDrive`
3. **Propriedades → Compartilhamento → Compartilhar**
4. Adicionar usuário e dar permissão de **Leitura/Gravação**
5. Anotar o caminho: `\\NOME-PC\OneDrive`

> Para descobrir o nome do PC no Windows: `echo %computername%` no CMD.

### 2.2 Na VM — Criar ponto de montagem

```bash
sudo mkdir -p /mnt/onedrive
```

### 2.3 Criar arquivo de credenciais SMB

```bash
sudo nano /etc/smb-credentials
```

Conteúdo:
```
username=denni
password=SUA_SENHA_WINDOWS
domain=WORKGROUP
```

Proteger o arquivo:
```bash
sudo chmod 600 /etc/smb-credentials
```

### 2.4 Configurar montagem automática

```bash
sudo nano /etc/fstab
```

Adicionar no final (substituir NOME-PC pelo nome real do computador Windows):
```
//NOME-PC/OneDrive /mnt/onedrive cifs credentials=/etc/smb-credentials,uid=laura,gid=laura,iocharset=utf8,vers=3.0,_netdev 0 0
```

### 2.5 Montar e testar

```bash
sudo mount -a
ls /mnt/onedrive
```

Você deve ver os arquivos do OneDrive. Se aparecer erro, verificar:
- Nome do PC está correto
- Compartilhamento foi ativado no Windows
- As credenciais estão corretas

---

## Fase 3 — Configurar o projeto

### 3.1 Clonar o repositório

```bash
cd /home/laura
git clone https://github.com/SEU-USUARIO/laura-bot.git
cd laura-bot
```

### 3.2 Criar ambiente virtual Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3 Configurar variáveis de ambiente

```bash
cp .env.example .env
nano .env
```

Preencher com os valores reais:
```env
TELEGRAM_BOT_TOKEN=seu_token_do_botfather
TELEGRAM_USER_ID=seu_id_do_telegram
CLAUDE_API_KEY=sua_chave_anthropic
ONEDRIVE_PATH=/mnt/onedrive
GGV_ATIVO=GGV03
LOG_LEVEL=INFO
DB_PATH=/home/laura/laura-bot/data/laura.db
```

> Para descobrir seu TELEGRAM_USER_ID: fale com @userinfobot no Telegram.

### 3.4 Inicializar o banco de dados

```bash
python scripts/migrate.py
```

---

## Fase 4 — Configurar serviço systemd

Para o bot iniciar automaticamente e reiniciar se cair.

### 4.1 Criar arquivo de serviço

```bash
sudo nano /etc/systemd/system/laura.service
```

Conteúdo:
```ini
[Unit]
Description=Laura Bot - Gestão GGV
After=network.target

[Service]
Type=simple
User=laura
WorkingDirectory=/home/laura/laura-bot
EnvironmentFile=/home/laura/laura-bot/.env
ExecStart=/home/laura/laura-bot/venv/bin/python -m app.bot.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 4.2 Ativar e iniciar

```bash
sudo systemctl daemon-reload
sudo systemctl enable laura
sudo systemctl start laura
sudo systemctl status laura
```

### 4.3 Ver logs em tempo real

```bash
sudo journalctl -u laura -f
```

---

## Fase 5 — Backup automático

### 5.1 Criar script de backup

O arquivo `scripts/backup.sh` já está no repositório. Apenas marcar como executável:

```bash
chmod +x /home/laura/laura-bot/scripts/backup.sh
```

### 5.2 Configurar cron diário

```bash
crontab -e
```

Adicionar:
```
0 3 * * * /home/laura/laura-bot/scripts/backup.sh >> /home/laura/laura-bot/logs/backup.log 2>&1
```

Isso roda o backup todo dia às 3h da manhã.

---

## Verificação final

Checklist de instalação completa:

- [ ] VM criada e Ubuntu instalado
- [ ] SSH funcionando
- [ ] UFW ativo (só porta 22)
- [ ] Dependências do sistema instaladas
- [ ] OneDrive montado em /mnt/onedrive
- [ ] Repositório clonado
- [ ] venv criado e dependências Python instaladas
- [ ] .env configurado com valores reais
- [ ] Banco de dados inicializado
- [ ] Serviço systemd ativo e rodando
- [ ] Bot responde no Telegram
- [ ] Cron de backup configurado
