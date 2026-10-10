# Deploy da Laura — Container LXC no Proxmox

> Criado em 2026-07-10. Alvo real: container **109 (laura)** no node `grow1` do Proxmox
> do Eric — Debian LXC (community-scripts), unprivileged, 2 vCPU, 2 GB RAM, 20 GB disco.
>
> **Atualizado em 2026-10-09**: o corte de produção foi executado em agosto/2026. Caminho e
> nome de serviço abaixo são os reais (`/opt/laura-bot`, `laura-bot.service`) — a primeira
> versão deste roteiro dizia `/opt/laura` e `laura.service`. Estado atual do servidor:
> `docs/ARQUITETURA.md`, seção 2.2.

## Visão geral

A Laura fala com o Telegram por **polling** (`run_polling()`): só faz conexões **de saída**
(Telegram API, Anthropic API, BrasilAPI, OneDrive). Não precisa de IP público, porta
aberta, domínio nem HTTPS.

> O domínio `laura.deltad.com.br` existe e está ativo, mas **não é usado pelo bot hoje** —
> fica reservado pra uma futura interface web (relatórios, dashboard).

Acesso remoto de manutenção (Dennis, do celular ou de casa): **Tailscale** no container —
também só tráfego de saída, nada a configurar no firewall.

## 1. O que pedir ao Eric (uma vez, no Proxmox)

No CT 109 → Options → Features, habilitar:

- **FUSE** — obrigatório pro rclone montar o OneDrive (`/dev/fuse` num CT unprivileged)
- **Nesting** — evita atrito com o Chromium headless (geração de PDF via Playwright)

Reiniciar o container depois de mudar as features.

Conferir também a versão do template: a Laura exige **Python ≥ 3.12**.
Debian 13 (trixie) e Ubuntu 24.04 servem; **Debian 12 não** (Python 3.11) — nesse caso é
recriar o CT com template mais novo (o `setup.sh` detecta e avisa).

## 2. Clonar o repositório

O repositório é **privado** (`github.com/dverschoor78/laura-bot`). No container:

```bash
cd /opt
git clone https://github.com/dverschoor78/laura-bot.git laura-bot
cd laura-bot
```

Pro clone funcionar num repo privado, usar um **fine-grained personal access token**
(GitHub → Settings → Developer settings → tokens, só leitura de conteúdo, só neste repo)
como senha do clone — ou adicionar uma deploy key. Nunca gravar o token em arquivo do repo.

> O caminho `/opt/laura-bot` é o assumido pelas units do systemd. Se mudar, ajustar
> `deploy/laura-bot.service` antes do passo 3.

## 3. Setup automático

```bash
cd /opt/laura-bot
bash deploy/setup.sh
```

O script: instala Python/venv/git/rclone/fuse3, valida Python ≥ 3.12, seta o fuso
`America/Sao_Paulo` (o banco usa `datetime('now','localtime')`), cria o `.venv`, instala as
dependências (`pip install .`), baixa o Chromium do Playwright (`--with-deps`) e copia as
units do systemd (sem habilitar ainda).

## 4. Montar o OneDrive (rclone)

```bash
rclone config          # criar remote: nome "onedrive", tipo "onedrive", login Microsoft
```

O login abre uma URL pra autorizar no navegador — dá pra fazer do celular/PC e colar o
token de volta (opção "headless machine" do próprio rclone config).

Testar e ativar a montagem:

```bash
rclone lsd onedrive:                          # deve listar "00 Obras" etc.
systemctl enable --now rclone-onedrive
ls "/mnt/onedrive/00 Obras"                   # deve listar as pastas das obras
```

## 5. Transferir segredos e dados (fora do git)

`.env`, `data/laura.db` e `data/uploads/` **nunca passam pelo GitHub**. Transferir direto
do Windows do Dennis (Tailscale + scp, ou qualquer canal seguro):

```bash
# exemplo, rodando NO WINDOWS (PowerShell), com Tailscale nos dois lados:
scp .env root@100.x.y.z:/opt/laura-bot/.env
scp data/laura.db root@100.x.y.z:/opt/laura-bot/data/laura.db
scp -r data/uploads root@100.x.y.z:/opt/laura-bot/data/
```

No `.env` do servidor, ajustar/garantir:

```
ONEDRIVE_PATH=/mnt/onedrive
```

⚠️ **Instância única**: a partir do momento em que o banco foi copiado, **parar o bot no
Windows e não subir de novo** — duas Lauras com o mesmo token brigam pelo polling, e os
bancos divergem. O corte é: parar no Windows → copiar → subir no servidor.

## 6. Migrar os caminhos do banco

`obras.pasta_onedrive` guarda caminhos absolutos do Windows
(`C:\Users\denni\OneDrive\...`). Converter pra relativo (resolvido contra `ONEDRIVE_PATH`):

```bash
cd /opt/laura-bot
.venv/bin/python scripts/migrar_caminhos_obras.py            # dry-run, confere o que muda
.venv/bin/python scripts/migrar_caminhos_obras.py --aplicar  # grava
```

Proteção no código: se um caminho Windows não migrado chegar num host Linux,
`_raiz_obra()` cai em `data/pfms/` (local) em vez de gravar em pasta inexistente.

`documentos.caminho` e `documentos.caminho_pfm` também guardavam caminhos do Windows
(`data\uploads\...`, `C:\Users\denni\OneDrive\...`) — achado em 2026-10-10, quando o cockpit
dos pedidos de julho mostrava "Nenhum arquivo disponível". Converter para os do servidor (só os
que existem lá; o resto fica como está e é listado):

```bash
cd /opt/laura-bot
.venv/bin/python scripts/migrar_caminhos_documentos.py            # dry-run, confere o que muda
.venv/bin/python scripts/migrar_caminhos_documentos.py --aplicar  # grava
```

## 7. Testar antes de produção

```bash
cd /opt/laura-bot
LAURA_ENV=test .venv/bin/python bot.py
```

Mandar um documento de teste pelo Telegram, conferir a resposta e um PDF gerado
(valida Chromium + fontes). `Ctrl+C` pra sair. Modo teste usa banco e pastas separados.

## 8. Subir em produção

```bash
systemctl enable --now laura-bot
systemctl status laura-bot        # deve estar "active (running)"
journalctl -u laura-bot -f        # acompanhar o log ao vivo
```

## 9. Operação

| Ação | Comando |
|---|---|
| Ver log | `journalctl -u laura-bot -f` |
| Reiniciar (após `git pull`) | `systemctl restart laura-bot` |
| Parar | `systemctl stop laura-bot` |
| Atualizar código | `cd /opt/laura-bot && git pull && systemctl restart laura-bot` |
| Status do OneDrive | `systemctl status rclone-onedrive` |

**Backup**: snapshot do CT no Proxmox (pedir ao Eric um agendamento) já cobre tudo —
banco, uploads, config. O que é insubstituível: `data/laura.db`, `data/uploads/`, `.env`.

## Checklist do corte de produção

> Corte executado em agosto/2026; itens conferidos contra o servidor em 2026-10-09.

- [x] Features FUSE + Nesting habilitadas no CT (Eric)
- [x] `setup.sh` concluído sem erro
- [x] `rclone lsd onedrive:` lista as pastas reais
- [x] `.env` copiado, com `ONEDRIVE_PATH=/mnt/onedrive`
- [x] Bot do Windows **PARADO**
- [x] `data/` copiado (laura.db + uploads)
- [x] Migração de caminhos aplicada (`--aplicar`) — GGV00/GGV03 com caminho relativo
- [x] Teste em `LAURA_ENV=test` OK (mensagem + PDF) — obra de teste GGV99
- [x] `systemctl enable --now laura-bot`
- [x] Documento real processado de ponta a ponta, arquivo apareceu no OneDrive
