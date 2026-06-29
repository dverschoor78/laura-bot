# Arquitetura do Projeto Laura

> Versão: 2026-06-29 — reflete o estado real do sistema

---

## 1. Visão Geral

A Laura é um bot Telegram pessoal para gestão de compras de obras GGV.

Dennis envia fotos ou PDFs de orçamentos pelo Telegram. O bot extrai os dados
com IA, apresenta para confirmação, gera o PFM Word numerado, salva no OneDrive
e registra o lançamento A PAGAR no banco.

**Tecnologias em uso:** Python 3.12 · python-telegram-bot 22 · SQLite · Claude API
(Anthropic) · python-docx · OneDrive (pasta local mapeada)

---

## 2. Componentes

```
Telegram ──────► bot.py ──────► Claude API (haiku-4-5)
                   │
                   ├──────────► data/laura.db  (SQLite)
                   ├──────────► data/uploads/  (arquivos recebidos)
                   └──────────► OneDrive/GGV03/04 Aquisição e Execução/
                                (PFMs gerados em .docx)
```

- **`bot.py`** — monólito único com toda a lógica: banco, IA, PFM, handlers Telegram
- **`data/laura.db`** — banco SQLite com três tabelas (ver seção 3)
- **`data/uploads/`** — arquivos temporários recebidos pelo bot
- **Claude API** — extração de dados dos documentos; modelo `claude-haiku-4-5-20251001`
- **OneDrive** — destino final dos PFMs; pasta local acessada via `GGV_ONEDRIVE`
- **`templates/PFM-template.docx`** — existe no repositório mas não é usado; o PFM é
  gerado programaticamente via python-docx, sem template Jinja2

---

## 3. Banco de Dados

**`documentos`** — registro de cada arquivo recebido e seu ciclo de vida

| Campo | Propósito |
|---|---|
| `id` | Chave primária |
| `hash` | SHA256 do arquivo — detecta duplicatas |
| `tipo` | Classificação: orcamento · comprovante_pix · extrato_mp |
| `ggv` | GGV identificado: GGV00–GGV03 ou nao_identificado |
| `dados_claude` | Texto bruto retornado pelo Claude; campos extraídos via `_campo()` na leitura |
| `condicao_pgto`, `data_entrega`, `endereco_entrega`, `desconto_rs` | Dados coletados durante o fluxo de confirmação |
| `pfm_numero` | Número sequencial por GGV (ex: 9 → GGV03-009) |
| `status` | Ciclo de vida: recebido → confirmado → pfm_gerado → cancelado |

---

**`lancamentos`** — registros financeiros A PAGAR / PAGO

| Campo | Propósito |
|---|---|
| `doc_id` | Referência lógica ao documento de origem (sem FK explícita) |
| `pfm_codigo` | Chave do lançamento (ex: GGV03-009) — UNIQUE |
| `fornecedor`, `valor` | Dados financeiros principais |
| `status` | a_pagar · pago · pendente_revisao · substituido |

Relação: um documento origina um lançamento. `pfm_codigo` é a chave de cruzamento.

---

**`fornecedores`** — cadastro importado dos PFMs do GGV01

Campos relevantes: `nome`, `razao_social`, `cnpj`, `cpf`, `chave_pix`, `email`,
`whatsapp`, `logradouro`, `bairro`, `cidade`, `uf`.

Uso: `buscar_fornecedor()` tenta primeiro por CNPJ, depois pelo primeiro token do nome.
Quando encontrado, os dados do cadastro prevalecem sobre os dados extraídos pelo Claude.
Sem relação de FK com as demais tabelas.

---

## 4. Fluxos

**Fluxo A — Orçamento → PFM → Lançamento**

```
Dennis envia foto ou PDF
  → bot calcula SHA256, detecta duplicatas
  → salva em data/uploads/
  → envia para Claude API com PROMPT estruturado
  → Claude retorna tipo, GGV e campos extraídos
  → bot exibe para confirmação (botões inline)
  → Dennis confirma (ou edita tipo, GGV, campos)
  → bot coleta condição de pagamento e endereço de entrega
  → Dennis aciona "Gerar PFM"
  → gerar_pfm() cria o .docx via python-docx
  → salva em OneDrive/GGV03/04 Aquisição e Execução/
  → registra lançamento A PAGAR em lancamentos
  → envia o .docx para Dennis no Telegram
```

**Fluxo B — Consulta de pedido por código**

```
Dennis digita o código (ex: GGV03-009)
  → regex PFM_CODIGO_RE detecta o código no texto
  → buscar_pedido() consulta documentos + lancamentos
  → preparar_visualizacao_pedido() verifica arquivos em disco
  → mostrar_pedido() formata a tela
  → bot exibe tela do pedido com botões de ação
```

---

## 5. Estrutura do bot.py

Referências para navegação no arquivo (1418 linhas):

| Bloco | Referência | O que faz |
|---|---|---|
| Imports e inicialização | `load_dotenv()`, `claude = anthropic...` | Dependências, variáveis de ambiente, cliente Claude |
| Constantes e configuração | `TIPOS`, `DELTAD`, `GGV_ONEDRIVE` | Mapeamentos de tipos, GGVs, dados DeltaD, endereços |
| Domínio — Pedido | `StatusPedido`, `Pedido` | Enum de status e dataclass com 17 campos |
| Integração Claude | `PROMPT` | Prompt de extração estruturada |
| Banco de dados | `init_db()`, `buscar_fornecedor()` | Criação de tabelas, CRUD |
| Geração de PFM | `gerar_pfm()`, `_campo()`, `_itens()` | Helpers de parsing e formatação; geração do Word |
| Domínio — consulta | `buscar_pedido()`, `mostrar_pedido()` | Pipeline de visualização do pedido |
| Teclados | `parse_resposta()`, `teclado_confirmacao()` | Parse da resposta Claude e botões inline |
| Handlers Telegram | `receber_arquivo()`, `receber_texto()`, `responder_botao()` | Handlers de mensagens e callbacks |
| Inicialização | `app.run_polling()` | Registro dos handlers e loop principal |

---

## 6. Limitações Conhecidas

- **Monólito** — toda a lógica está em `bot.py`. Aceitável hoje; dificulta testes
  automatizados e manutenção em longa escala.

- **`responder_botao()` é dispatcher único** — função de ~280 linhas que trata todas
  as ações de botões inline. Ponto de maior acoplamento do sistema.

- **`gerar_pfm()` acumula responsabilidades** — gera o Word, grava no banco e cria
  o lançamento na mesma função. Dificulta testes e extensão futura.

- **`dados_claude` armazena texto bruto** — campos não são estruturados no banco;
  toda extração ocorre na leitura via `_campo()`. Mudanças no formato do Claude
  podem afetar a leitura de documentos antigos.

- **`pfm_caminho` não existe como coluna** — o path do arquivo .docx é reconstruído
  a cada consulta com base em `GGV_ONEDRIVE` + `pfm_codigo`. Inconsistente se a
  estrutura de pastas mudar.

- **BD fornecedores com dados incorretos** — MO Construção com CNPJ errado;
  PRUDENTÓPOLIS com split incorreto. Afeta `buscar_fornecedor()`.

---

## 7. Próxima Decisão Arquitetural

**ADR-001** formalizará a decisão de manter o monólito em `bot.py`.
O documento definirá a condição de revisão dessa decisão
(volume de código, necessidade de testes, novas fases do produto).
