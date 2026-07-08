import os
import re
import json
import unicodedata
import shutil
import hashlib
import sqlite3
import base64
import urllib.request
import anthropic
from num2words import num2words
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from financeiro.lancamento import (init_db_financeiro, sugerir_categoria, CategoriaLancamento,
                                   vincular_nfe, buscar_candidatos_nfe)
from financeiro.consultas import procurar_item
from nfe import parse_nfe, mostrar_nfe, teclado_candidatos_nfe
from compras import (init_db_compras, criar_ou_buscar_lista_aberta, buscar_lista,
                      atualizar_lista, encerrar_lista, listar_listas_obra,
                      sugerir_itens, adicionar_item, remover_item, listar_itens,
                      GrauConfianca, OrigemReferencia)

load_dotenv()
TOKEN       = os.environ["TELEGRAM_BOT_TOKEN"]
DONO_ID     = int(os.environ["TELEGRAM_USER_ID"])
CLAUDE_KEY  = os.environ["CLAUDE_API_KEY"]
TEST_MODE = os.environ.get("LAURA_ENV", "prod") == "test"
DB_PATH   = Path("data/laura_test.db") if TEST_MODE else Path("data/laura.db")
UPLOADS   = Path("data/test_uploads")  if TEST_MODE else Path("data/uploads")
UPLOADS.mkdir(parents=True, exist_ok=True)

claude = anthropic.Anthropic(api_key=CLAUDE_KEY)

TIPOS = {
    "orcamento":        ("📋", "Orçamento"),
    "comprovante_pix":  ("💰", "Comprovante PIX"),
    "nota_fiscal":      ("🧾", "Nota Fiscal"),
    "foto_entrega":     ("📦", "Foto/arquivo de entrega"),
    "extrato_mp":       ("🏦", "Extrato MP"),
    "lista_materiais":  ("📝", "Lista de materiais"),
    "nao_relacionado":  ("🗑", "Não é da obra"),
}
GGVS = ["GGV00", "GGV01", "GGV02", "GGV03"]

MESES = ["janeiro","fevereiro","março","abril","maio","junho",
         "julho","agosto","setembro","outubro","novembro","dezembro"]

# Nome histórico da constante — contém os dados da VII (Verschoor Investimentos Imobiliários
# Ltda, dona dos empreendimentos), não da DeltaD (Verschoor Construções Civis Ltda, nome
# fantasia "DeltaD Engenharia", CNPJ 48.494.891/0001-06). Por decisão de 2026-07-01, a DeltaD
# não participa do fluxo de compras — é só mais um fornecedor da VII. Ver ESTADO.md.
DELTAD = {
    "nome":  "Verschoor Investimentos Imobiliários Ltda",
    "cnpj":  "58.358.802/0001-58",
    "ie":    "Isento",
    "end":   "Av. dos Pioneiros, 1380 – Centro – Carambeí/PR – CEP 84.145-000",
    "email": "dennis@deltad.com.br",
    "fone":  "(42) 99127-1255",
}
DELTAD_CNPJ_DIGITS = re.sub(r"\D", "", DELTAD["cnpj"])  # "58358802000158"

# CNPJs das próprias empresas de Dennis — nunca podem virar "fornecedor" (ex: aparecem como
# Pagador/Sacado em boletos bancários). VII (dona dos empreendimentos) + DeltaD Engenharia
# (Verschoor Construções Civis Ltda, responsável técnica, paga boletos como CREA/ONR/prefeitura).
CNPJS_PROPRIOS_DIGITS = {DELTAD_CNPJ_DIGITS, "48494891000106"}

GGV_ENCARREGADO = {
    "GGV03": "Sabiá",
}

GGV_DESC = {
    "GGV01": "GGV01 — Matrícula 39.333, Quadra 05 Lote 02, JD das Nações, Carambeí-PR",
    "GGV02": "GGV02 — Matrícula 39.337, Quadra 05 Lote 06, JD das Nações, Carambeí-PR",
    "GGV03": "GGV03 — Matrícula 39.339, Quadra 05 Lote 08, JD das Nações, Carambeí-PR",
    "GGV00": "GGV00 — Despesas Gerais",
}

GGV_ONEDRIVE = {
    "GGV03": Path(r"C:\Users\denni\OneDrive\00 Obras\2026-06 GGV03\04 Aquisição e Execução"),
}

CONDICOES = {
    "pix_avista":  "PIX à vista",
    "pix_50_50":   "PIX 50% entrada + 50% na entrega",
}

ENDERECOS = {
    "obra_GGV01": "Rua Índia em frente ao nº139, Loteamento JD das Nações - Carambeí-PR CEP 84.145-000",
    "obra_GGV02": "Rua Índia em frente ao nº139, Loteamento JD das Nações - Carambeí-PR CEP 84.145-000",
    "obra_GGV03": "Rua Índia em frente ao nº139, Loteamento JD das Nações - Carambeí-PR CEP 84.145-000",
    "casa":        "Avenida dos Pioneiros, fundos Frederica's Coffie Huis - Carambeí-PR CEP 84.145-000",
    "escritorio":  "Avenida dos Pioneiros, 1380 - Carambeí-PR CEP 84.145-000",
    "chacara":     "Avenida dos Pioneiros, 5125 - Carambeí-PR CEP 84.145-000",
}

def _opcoes_endereco(ggv):
    """Opções de endereço de entrega — mesmo conjunto usado no Pedido de Compra e na Lista
    de Compras (Dennis, 2026-07-05: "endereço de entrega é o mesmo conceito nos dois... a
    Lista deve reaproveitar essa mesma experiência, não criar um fluxo paralelo mais
    simples", aplicação de "Entradas diferentes podem existir. Processos diferentes não.").
    Cada opção é (rótulo, chave); resolução da chave em endereço real é _resolver_endereco().
    Botão "Obra" só aparece com ggv definido — a Lista de Compras pode chegar aqui sem obra."""
    opcoes = []
    if ggv:
        opcoes.append((f"🏗 Obra ({ggv})", f"obra_{ggv}"))
    opcoes += [
        ("🏠 Casa", "casa"),
        ("🏢 Escritório", "escritorio"),
        ("🌳 Chácara", "chacara"),
        ("✏️ Outro (digitar)", "outro"),
    ]
    return opcoes

def _resolver_endereco(escolha):
    """Resolve a chave de escolha (ex: 'obra_GGV03', 'casa') no endereço real — usada pelo
    único handler _cb_endsel, compartilhado entre Pedido de Compra e Lista de Compras."""
    if escolha.startswith("obra_"):
        ggv_key = escolha[5:]
        return buscar_obra(ggv_key).get("endereco_entrega") or ENDERECOS.get(escolha, escolha)
    return ENDERECOS.get(escolha, escolha)

GGV_CODIGO_RE = re.compile(r"^\s*(GGV\d{2})\s*$", re.IGNORECASE)

class StatusPedido(str, Enum):
    A_PAGAR          = "a_pagar"
    PAGO             = "pago"
    PENDENTE_REVISAO = "pendente_revisao"
    SUBSTITUIDO      = "substituido"
    SEM_LANCAMENTO   = "sem_lancamento"

@dataclass
class Pedido:
    # Identificação
    codigo: str
    doc_id: int
    ggv:    str

    # Domínio
    status:             StatusPedido
    fornecedor:         str
    cnpj:               str
    valor_orcamento:    float
    desconto:           float
    valor_negociado:    float
    condicao_pagamento: str
    vencimento:         str
    entrega_prevista:   str

    # Datas de registro — base para construir o histórico
    doc_criado_em:  Optional[str] = None
    lanc_criado_em: Optional[str] = None
    data_pagamento: Optional[str] = None
    doc_id_nfe:            Optional[int] = None
    nfe_numero:            Optional[str] = None
    nfe_data:              Optional[str] = None
    doc_id_comprovante:    Optional[int] = None
    identificador_comprovante: Optional[str] = None
    qtd_fotos_entrega:     int = 0
    obs_entrega:           Optional[str] = None
    entregue_em:           Optional[str] = None
    categoria:             Optional[str] = None
    qtd_parcelas:          int = 0
    total_pago:            float = 0.0
    observacoes:           Optional[str] = None

    # Arquivos — populados por preparar_visualizacao_pedido()
    caminho_orcamento: Optional[str] = None
    caminho_pfm:       Optional[str] = None

    # Histórico — populado por preparar_visualizacao_pedido()
    historico: list = field(default_factory=list)

PROMPT = """
Você recebeu um arquivo enviado para um sistema de gestão de obras de construção civil.

PASSO 1 — Classifique o documento:
[orcamento]        — cotação, orçamento, pedido de compra, lista de materiais com preços;
                     também boleto, fatura ou conta a pagar de taxa/imposto/serviço público
                     (ex: anuidade CREA, emolumentos de cartório/ONR, IPTU e taxas de prefeitura,
                     conta de energia Copel, conta de água/esgoto Sanepar)
[comprovante_pix]  — comprovante de pagamento PIX ou transferência bancária
[nota_fiscal]      — Nota Fiscal eletrônica (NF-e), DANFE, NFS-e ou recibo fiscal
[extrato_mp]       — extrato do Mercado Pago ou extrato bancário
[nao_relacionado]  — qualquer outro documento não relacionado a obras

PASSO 2 — Identifique o empreendimento (GGV):
GGV01 — Matrícula 39.333, Quadra 05 Lote 02
GGV02 — Matrícula 39.337, Quadra 05 Lote 06
GGV03 — Matrícula 39.339, Quadra 05 Lote 08
GGV00 — despesas gerais compartilhadas
nao_identificado — se não conseguir determinar

PASSO 3 — Extraia os dados em português conforme o tipo:

Se [orcamento]:
- Fornecedor: (em boleto bancário, é o Beneficiário/Cedente — NUNCA o Pagador/Sacado, que é
  sempre a própria empresa que está comprando; não confunda os dois)
- Ramo de atividade: (ex: Comércio de Materiais de Construção, Serralheria, Elétrica — informe como aparece no documento ou deduza pelo contexto)
- Resumo da compra: (2 a 4 palavras que identifiquem o item principal do orçamento — ex: "aço", "tubos caixa d'água", "material elétrico", "portas"; vai virar nome de arquivo)
- CNPJ/CPF:
- Chave PIX: (só extraia se estiver claramente rotulada como PIX/chave de pagamento do
  fornecedor, perto dos dados de cobrança/beneficiário; NUNCA use um telefone ou identificador
  de outra pessoa/entidade que apareça no documento por outro motivo — ex: "Responsável pela
  Iluminação Pública" numa fatura de energia não é a chave PIX do fornecedor. Na dúvida, não
  preencha)
- Número do orçamento: (número ou código do orçamento emitido pelo fornecedor, se houver)
- Vendedor: (nome do vendedor ou representante que emitiu o orçamento, se houver)
- Telefone do vendedor: (telefone ou WhatsApp do vendedor, se houver)
- Itens (formato: N. Descrição do produto (QTDE UND) — R$ TOTAL; liste TODAS as linhas de
  cobrança do documento, mesmo as que não têm quantidade/unidade clara — ex: uma fatura de
  energia pode ter uma linha "Valor ref. conta do mês anterior" sem kWh associado; nesse caso
  use QTDE=1 e UND=UN, mas NUNCA omita a linha só porque ela foge do padrão das demais):
- Valor total: (o valor total cobrado no documento, como fonte independente da soma dos itens —
  extraia mesmo que a soma dos itens não bata exatamente, nunca ajuste um pra bater com o outro)
- Desconto (valor em R$, se houver; se informado em %, calcule o valor sobre o total):
- Condição de pagamento:
- Prazo de entrega: (lead time ou data de entrega do material — NÃO a validade da proposta)
- Vencimento: (data de vencimento do pagamento, se o documento for boleto/fatura — diferente de
  prazo de entrega, que é sobre a entrega do material)
- Validade da proposta: (data até quando o preço é válido)
- Observações:

Se [comprovante_pix]:
- Data do pagamento:
- Valor:
- Favorecido:
- CNPJ/CPF do favorecido:
- Chave PIX:
- Instituição financeira:
- ID da transação: (prefira o ID EndToEnd do Pix — começa com "E", ex: E10573521202506... — se não estiver visível, use o número da transação do Mercado Pago; extraia APENAS o código, sem texto adicional)
- Identificador / Observação:

Se [nota_fiscal]:
- Número da NF:
- CNPJ/CPF do emitente:
- Nome do emitente:
- Valor total:
- Data de emissão:
- Descrição do serviço/produto: (resumo do que foi fornecido)

Se [extrato_mp]:
- Período:
- Número de transações identificadas:
- Resumo:

Se [nao_relacionado]:
- Descreva brevemente o que é o documento.

IMPORTANTE: use SOMENTE os campos da lista do tipo que você classificou no PASSO 1. Nunca misture
campos de outro tipo — por exemplo, se classificou como [orcamento] (inclusive boleto/fatura),
não escreva "Favorecido", "Chave PIX" ou "Instituição financeira" (esses são só de
[comprovante_pix]), mesmo que o documento pareça visualmente um recibo de banco.

Responda EXATAMENTE neste formato (sem colchetes, sem barra, escolha um valor de cada):
TIPO:orcamento
GGV:GGV03

Valores aceitos para TIPO: orcamento, comprovante_pix, nota_fiscal, extrato_mp, nao_relacionado
Valores aceitos para GGV: GGV00, GGV01, GGV02, GGV03, nao_identificado

Em seguida, os dados extraídos conforme o tipo identificado acima.
"""

def _raiz_obra(ggv: str) -> Optional[Path]:
    """Pasta raiz da obra no OneDrive (ex: '00 Obras/2026-06 GGV03'). None se não configurada."""
    obra = buscar_obra(ggv)
    raiz = obra.get("pasta_onedrive", "")
    return Path(raiz) if raiz else None

def _pasta_pfm(ggv: str) -> Path:
    if TEST_MODE:
        pasta = Path("data/test_pfms")
    else:
        raiz  = _raiz_obra(ggv)
        pasta = (raiz / "04 Compras") if raiz else Path("data/pfms")
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta

def _pasta_orcamentos(ggv: str) -> Path:
    pasta = _pasta_pfm(ggv) / "00 Orçamentos"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta

def _pasta_controle_financeiro(ggv: str) -> Path:
    if TEST_MODE:
        pasta = Path("data/test_pfms") / "01 Controle financeiro"
    else:
        raiz  = _raiz_obra(ggv)
        pasta = (raiz / "01 Controle financeiro") if raiz else Path("data/pfms") / "01 Controle financeiro"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta

def _pasta_entrega(ggv: str) -> Path:
    if TEST_MODE:
        pasta = Path("data/test_pfms") / "05 Entrega"
    else:
        raiz  = _raiz_obra(ggv)
        pasta = (raiz / "05 Entrega") if raiz else Path("data/pfms") / "05 Entrega"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta

def _nome_arquivo_seguro(s: str, max_len: int = 60) -> str:
    """Remove caracteres inválidos em nome de arquivo do Windows. Vazio/"A PREENCHER" -> ""."""
    if not s or s == "A PREENCHER":
        return ""
    s = re.sub(r'[<>:"/\\|?*]', "", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s[:max_len].strip()

def _slug_arquivo(s: str, max_len: int = 40) -> str:
    """Slug em minúsculo, sem acento, palavras separadas por hífen — usado no nome dos PDFs
    da Lista de Compras (ex: "Materiais Elétricos" -> "materiais-eletricos")."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:max_len].strip("-")

def _nome_base_pfm(pfm_codigo: str, fornecedor: str, resumo: str, prefixo: str = "") -> str:
    """Monta o nome de arquivo do PFM: 'GGV03-008 - Fornecedor - Resumo'."""
    partes = [f"{prefixo}{pfm_codigo}"]
    for campo in (fornecedor, resumo):
        seguro = _nome_arquivo_seguro(campo)
        if seguro:
            partes.append(seguro)
    return " - ".join(partes)

def _parse_data_qualquer(data_str):
    """Interpreta uma data em qualquer formato já visto na extração real — numérico
    (DD/MM/AAAA), "DD de mês de AAAA", ou "DD/nome-do-mês/AAAA" (achado 2026-07-06 em
    lancamentos.data_pagamento real: "25/junho/2026 às 12:41:40" — nenhum dos dois formatos
    acima cobria esse caso). Hora/minuto no final (ex: " às HH:MM:SS") é ignorada. Retorna
    `None` quando não reconhece — nunca adivinha (2026-07-06: usado pra "há quanto tempo",
    onde chutar "hoje" seria pior que admitir que não sabe)."""
    if not data_str or data_str == "A PREENCHER":
        return None
    s = data_str.strip()
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mth, d = m.groups()
        try:
            return datetime(int(y), int(mth), int(d))
        except ValueError:
            return None
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", s)
    if m:
        d, mth, y = m.groups()
        if len(y) == 2:
            y = "20" + y
        try:
            return datetime(int(y), int(mth), int(d))
        except ValueError:
            pass
    m = re.match(r"(\d{1,2})/(\D[^/]*)/(\d{4})", s, re.IGNORECASE)
    if m:
        d, mes_nome, y = m.groups()
        if mes_nome.strip().lower() in MESES:
            try:
                return datetime(int(y), MESES.index(mes_nome.strip().lower()) + 1, int(d))
            except ValueError:
                pass
    m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", s, re.IGNORECASE)
    if m:
        d, mes_nome, y = m.groups()
        if mes_nome.lower() in MESES:
            try:
                return datetime(int(y), MESES.index(mes_nome.lower()) + 1, int(d))
            except ValueError:
                pass
    return None

def _data_para_arquivo(data_str: str) -> str:
    """Converte data extraída pra AAAA-MM-DD. Usa hoje se não conseguir reconhecer."""
    dt = _parse_data_qualquer(data_str)
    return dt.strftime("%Y-%m-%d") if dt else datetime.now().strftime("%Y-%m-%d")

def _tempo_decorrido(data_str):
    """'há quanto tempo' de forma legível, a partir de qualquer formato de data já visto
    (Consultoria de Recompra, 2026-07-06). `None` quando a data não é reconhecível — melhor
    omitir do que mostrar um tempo errado."""
    dt = _parse_data_qualquer(data_str)
    if dt is None:
        return None
    dias = (datetime.now() - dt).days
    if dias < 0:
        return None
    if dias < 30:
        return "menos de 1 mês"
    meses = dias // 30
    if meses < 12:
        return f"{meses} mês" if meses == 1 else f"{meses} meses"
    anos = meses // 12
    return f"{anos} ano" if anos == 1 else f"{anos} anos"

def _arquivar_documento(pfm_codigo: str, sufixo: str, caminho_original, data_str, pasta_fn):
    """Copia um documento vinculado a um pedido para a pasta certa, nome padronizado. Falha silenciosa."""
    if not caminho_original or not Path(caminho_original).exists():
        return
    ggv = pfm_codigo.split("-")[0]
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT fornecedor FROM lancamentos WHERE pfm_codigo=?", (pfm_codigo,)).fetchone()
    fornecedor   = row[0] if row else ""
    data_arquivo = _data_para_arquivo(data_str)
    nome = f"{data_arquivo} {pfm_codigo}"
    forn_seguro = _nome_arquivo_seguro(fornecedor)
    if forn_seguro:
        nome += f" {forn_seguro}"
    nome += f" - {sufixo}"
    ext = Path(caminho_original).suffix
    destino = pasta_fn(ggv) / f"{nome}{ext}"
    try:
        shutil.copy2(caminho_original, destino)
    except OSError:
        pass

def _arquivar_doc_financeiro(pfm_codigo: str, sufixo: str, caminho_original, data_str: str):
    """Copia comprovante/NF-e para '01 Controle financeiro', nome padronizado."""
    _arquivar_documento(pfm_codigo, sufixo, caminho_original, data_str, _pasta_controle_financeiro)

def _total_pago(pfm_codigo: str) -> float:
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT COALESCE(SUM(valor), 0) FROM parcelas_pagamento WHERE pfm_codigo=?", (pfm_codigo,)
        ).fetchone()
    return row[0] or 0.0

def _recalcular_status_pagamento(pfm_codigo: str, valor: float, data_pagamento: str = None) -> bool:
    """Sincroniza status/valor_pago de `lancamentos` com a soma real das parcelas já registradas
    contra o `valor` atual do pedido. Chamada tanto ao registrar uma parcela quanto depois de uma
    revisão que muda o valor — uma revisão pode fazer a soma já paga alcançar (ou deixar de
    alcançar) o valor corrigido, e o status precisa refletir isso, não só o PDF. Nunca inventa
    parcela nova, só reconcilia o que já existe. Retorna True se o pedido está quitado."""
    total_pago = _total_pago(pfm_codigo)
    quitado = bool(valor) and total_pago >= valor - 0.01
    with sqlite3.connect(DB_PATH) as con:
        if quitado:
            con.execute(
                "UPDATE lancamentos SET status='pago', valor_pago=?, "
                "data_pagamento=COALESCE(?, data_pagamento) WHERE pfm_codigo=?",
                (total_pago, data_pagamento, pfm_codigo)
            )
        else:
            con.execute(
                "UPDATE lancamentos SET status='a_pagar', valor_pago=? WHERE pfm_codigo=?",
                (total_pago, pfm_codigo)
            )
    return quitado

def _registrar_parcela(pfm_codigo, valor, data_pagamento, doc_id_comprovante, identificador_comprovante) -> int:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "INSERT INTO parcelas_pagamento (pfm_codigo, valor, data_pagamento, doc_id_comprovante, identificador_comprovante) "
            "VALUES (?,?,?,?,?)",
            (pfm_codigo, valor, data_pagamento, doc_id_comprovante, identificador_comprovante)
        )
        return cur.lastrowid

def _listar_parcelas(pfm_codigo):
    with sqlite3.connect(DB_PATH) as con:
        return con.execute(
            "SELECT id, valor, data_pagamento, doc_id_recibo, doc_id_recibo_assinado, status "
            "FROM parcelas_pagamento WHERE pfm_codigo=? ORDER BY id",
            (pfm_codigo,)
        ).fetchall()

def _buscar_parcela(parcela_id: int):
    with sqlite3.connect(DB_PATH) as con:
        return con.execute(
            "SELECT id, pfm_codigo, valor, data_pagamento, doc_id_recibo, doc_id_recibo_assinado, status "
            "FROM parcelas_pagamento WHERE id=?", (parcela_id,)
        ).fetchone()

# ── Banco ──────────────────────────────────────────────────────────────────

def _migrar_obras(con):
    """Pré-popula a tabela obras a partir dos dados que eram hardcoded. Idempotente."""
    dados = [
        ("GGV00", "Despesas Gerais", "", "", "",
         "Dennis Verschoor", "(42) 99127-1255", "", 1),
        ("GGV01", "Matrícula 39.333, Quadra 05 Lote 02, JD das Nações, Carambeí-PR",
         "Rua Índia em frente ao nº139, JD das Nações - Carambeí-PR CEP 84.145-000",
         "", "", "Dennis Verschoor", "(42) 99127-1255", "", 1),
        ("GGV02", "Matrícula 39.337, Quadra 05 Lote 06, JD das Nações, Carambeí-PR",
         "Rua Índia em frente ao nº139, JD das Nações - Carambeí-PR CEP 84.145-000",
         "", "", "Dennis Verschoor", "(42) 99127-1255", "", 1),
        ("GGV03", "Matrícula 39.339, Quadra 05 Lote 08, JD das Nações, Carambeí-PR",
         "Rua Índia em frente ao nº139, JD das Nações - Carambeí-PR CEP 84.145-000",
         "Sabiá", "(42) 98439-9498",
         "Dennis Verschoor", "(42) 99127-1255",
         r"C:\Users\denni\OneDrive\00 Obras\2026-06 GGV03\04 Aquisição e Execução", 1),
    ]
    for d in dados:
        con.execute("""
            INSERT OR IGNORE INTO obras
            (codigo, descricao, endereco_entrega, encarregado_nome, encarregado_fone,
             responsavel_nome, responsavel_fone, pasta_onedrive, ativa)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, d)

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS documentos (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                nome             TEXT,
                caminho          TEXT,
                hash             TEXT UNIQUE,
                tipo             TEXT DEFAULT 'desconhecido',
                ggv              TEXT DEFAULT 'nao_identificado',
                dados_claude     TEXT,
                condicao_pgto    TEXT,
                data_entrega     TEXT,
                endereco_entrega TEXT,
                desconto_rs      TEXT,
                pfm_numero       INTEGER,
                status           TEXT DEFAULT 'recebido',
                criado_em        TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        for col in ["tipo", "ggv", "dados_claude", "condicao_pgto", "data_entrega", "endereco_entrega", "desconto_rs TEXT", "pfm_numero INTEGER", "vencimento_pgto TEXT", "encarregado TEXT", "rev_numero INTEGER DEFAULT 0", "caminho_pfm TEXT"]:
            try:
                con.execute(f"ALTER TABLE documentos ADD COLUMN {col}")
            except Exception:
                pass
        con.execute("""
            CREATE TABLE IF NOT EXISTS lancamentos (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id                INTEGER NOT NULL,
                pfm_codigo            TEXT NOT NULL UNIQUE,
                ggv                   TEXT,
                fornecedor            TEXT,
                valor                 REAL,
                data_prevista_entrega TEXT,
                vencimento_pagamento  TEXT,
                status                TEXT DEFAULT 'a_pagar',
                criado_em             TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        for col in ["valor_pago REAL", "data_pagamento TEXT", "doc_id_comprovante INTEGER",
                    "identificador_comprovante TEXT", "doc_id_entrega INTEGER",
                    "obs_entrega TEXT", "entregue_em TEXT", "doc_id_recibo INTEGER"]:
            try:
                con.execute(f"ALTER TABLE lancamentos ADD COLUMN {col}")
            except Exception:
                pass
        con.execute("""
            CREATE TABLE IF NOT EXISTS entrega_fotos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pfm_codigo  TEXT NOT NULL,
                doc_id      INTEGER NOT NULL,
                legenda     TEXT,
                criado_em   TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS parcelas_pagamento (
                id                         INTEGER PRIMARY KEY AUTOINCREMENT,
                pfm_codigo                 TEXT NOT NULL,
                valor                      REAL,
                data_pagamento             TEXT,
                doc_id_comprovante         INTEGER,
                identificador_comprovante  TEXT,
                doc_id_recibo              INTEGER,
                doc_id_recibo_assinado     INTEGER,
                status                     TEXT DEFAULT 'pago',
                criado_em                  TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS itens_pedido (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                pfm_codigo            TEXT NOT NULL,
                numero                INTEGER,
                descricao             TEXT NOT NULL,
                unidade               TEXT,
                quantidade            REAL,
                valor_unitario        REAL,
                valor_total           REAL,
                insumo_sinapi_codigo  INTEGER,
                criado_em             TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS obras (
                codigo            TEXT PRIMARY KEY,
                descricao         TEXT,
                endereco_entrega  TEXT,
                encarregado_nome  TEXT,
                encarregado_fone  TEXT,
                responsavel_nome  TEXT,
                responsavel_fone  TEXT,
                pasta_onedrive    TEXT,
                ativa             INTEGER DEFAULT 1,
                criado_em         TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        _migrar_obras(con)
        con.execute("""
            CREATE TABLE IF NOT EXISTS fornecedores (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                nome         TEXT NOT NULL,
                razao_social TEXT,
                cnpj         TEXT,
                cpf          TEXT,
                chave_pix    TEXT,
                email        TEXT,
                whatsapp     TEXT,
                contato      TEXT,
                logradouro   TEXT,
                numero       TEXT,
                bairro       TEXT,
                cidade       TEXT,
                uf           TEXT,
                cep          TEXT,
                origem       TEXT,
                criado_em    TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(cnpj),
                UNIQUE(cpf)
            )
        """)
        for col in ["ramo TEXT", "receita_pendente INTEGER DEFAULT 0", "emite_nf INTEGER", "cnae TEXT"]:
            try:
                con.execute(f"ALTER TABLE fornecedores ADD COLUMN {col}")
            except Exception:
                pass
    init_db_financeiro(DB_PATH)
    init_db_compras(DB_PATH)

def buscar_obra(codigo):
    """Retorna dict com dados da obra ou {} se não encontrada."""
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT codigo, descricao, endereco_entrega, encarregado_nome, encarregado_fone, "
            "responsavel_nome, responsavel_fone, pasta_onedrive FROM obras WHERE codigo=?",
            (codigo,)
        ).fetchone()
    if not row:
        return {}
    keys = ["codigo", "descricao", "endereco_entrega", "encarregado_nome",
            "encarregado_fone", "responsavel_nome", "responsavel_fone", "pasta_onedrive"]
    return dict(zip(keys, row))

_COLUNAS_OBRA = {"descricao", "endereco_entrega", "encarregado_nome", "encarregado_fone",
                 "responsavel_nome", "responsavel_fone", "pasta_onedrive", "ativa"}

def atualizar_obra(codigo, **kwargs):
    colunas_invalidas = set(kwargs) - _COLUNAS_OBRA
    if colunas_invalidas:
        raise ValueError(f"Coluna(s) não permitida(s) em atualizar_obra: {colunas_invalidas}")
    cols = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [codigo]
    with sqlite3.connect(DB_PATH) as con:
        con.execute(f"UPDATE obras SET {cols} WHERE codigo=?", vals)

def criar_obra(codigo, descricao=""):
    """Insere nova obra. Retorna True se criada, False se já existia."""
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "INSERT OR IGNORE INTO obras (codigo, descricao, ativa) VALUES (?, ?, 1)",
            (codigo.upper(), descricao)
        )
        return cur.rowcount == 1

def ja_existe(hash_arquivo):
    if TEST_MODE:
        return None
    with sqlite3.connect(DB_PATH) as con:
        return con.execute("SELECT id FROM documentos WHERE hash = ?", (hash_arquivo,)).fetchone()

def registrar(nome, caminho, hash_arquivo, tipo, ggv, dados_claude):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "INSERT INTO documentos (nome, caminho, hash, tipo, ggv, dados_claude) VALUES (?,?,?,?,?,?)",
            (nome, str(caminho), hash_arquivo, tipo, ggv, dados_claude)
        )
        return cur.lastrowid

_COLUNAS_DOCUMENTO = {"tipo", "ggv", "dados_claude", "condicao_pgto", "data_entrega",
                      "endereco_entrega", "desconto_rs", "pfm_numero", "status",
                      "vencimento_pgto", "encarregado", "rev_numero", "caminho_pfm"}

def atualizar(doc_id, **campos):
    colunas_invalidas = set(campos) - _COLUNAS_DOCUMENTO
    if colunas_invalidas:
        raise ValueError(f"Coluna(s) não permitida(s) em atualizar: {colunas_invalidas}")
    sets = ", ".join(f"{k}=?" for k in campos)
    with sqlite3.connect(DB_PATH) as con:
        con.execute(f"UPDATE documentos SET {sets} WHERE id=?", (*campos.values(), doc_id))

def _autopreencher_endereco(doc_id, ggv):
    """Preenche endereco_entrega com o padrão da obra, se o pedido ainda não tiver nenhum
    definido. Nunca sobrescreve uma escolha já feita (manual ou de edição anterior)."""
    if ggv == "nao_identificado":
        return
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT endereco_entrega FROM documentos WHERE id=?", (doc_id,)).fetchone()
    if row and row[0]:
        return
    padrao = buscar_obra(ggv).get("endereco_entrega")
    if padrao:
        atualizar(doc_id, endereco_entrega=padrao)

def _descartar_documento(doc_id, force=False) -> bool:
    """Apaga o registro e o arquivo de um documento que não virou nada (cancelado, sem
    correspondência). Libera o hash para o mesmo arquivo poder ser reenviado depois.

    Por padrão, nunca apaga um documento que já virou um pedido de verdade (pfm_numero
    preenchido) — protege contra botão "Cancelar" de mensagem antiga do Telegram (ainda
    clicável) acertando um documento que já foi usado há muito tempo. Use force=True só quando
    a exclusão é intencional e explícita (ex: _excluir_pedido, depois de confirmação do usuário).
    Retorna True se descartou, False se recusou por segurança."""
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT caminho, pfm_numero FROM documentos WHERE id=?", (doc_id,)).fetchone()
        if not row:
            return False
        caminho, pfm_numero = row
        if pfm_numero is not None and not force:
            return False
        con.execute("DELETE FROM documentos WHERE id=?", (doc_id,))
    if caminho:
        try:
            Path(caminho).unlink(missing_ok=True)
        except OSError:
            pass
    return True

def _excluir_pedido(pfm_codigo):
    """Apaga um pedido inteiro (cadastro errado): lançamento, parcelas, fotos de entrega e
    todos os documentos vinculados (orçamento, comprovantes, NF-e, recibos). Não mexe em
    arquivos já arquivados no OneDrive — só no registro da Laura e nos uploads originais."""
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT doc_id, doc_id_comprovante, doc_id_nfe, doc_id_recibo FROM lancamentos WHERE pfm_codigo=?",
            (pfm_codigo,)
        ).fetchone()
        doc_ids = set(row) if row else set()

        parcelas = con.execute(
            "SELECT doc_id_comprovante, doc_id_recibo, doc_id_recibo_assinado FROM parcelas_pagamento WHERE pfm_codigo=?",
            (pfm_codigo,)
        ).fetchall()
        for p in parcelas:
            doc_ids.update(p)

        fotos = con.execute("SELECT doc_id FROM entrega_fotos WHERE pfm_codigo=?", (pfm_codigo,)).fetchall()
        doc_ids.update(f[0] for f in fotos)

        doc_ids.discard(None)

        con.execute("DELETE FROM parcelas_pagamento WHERE pfm_codigo=?", (pfm_codigo,))
        con.execute("DELETE FROM entrega_fotos WHERE pfm_codigo=?", (pfm_codigo,))
        con.execute("DELETE FROM lancamentos WHERE pfm_codigo=?", (pfm_codigo,))

    for doc_id in doc_ids:
        _descartar_documento(doc_id, force=True)

def registrar_lancamento(doc_id, pfm_codigo, ggv, fornecedor, valor_v, data_entrega, categoria=None):
    """Insere lançamento A PAGAR. Idempotente: se pfm_codigo já existe, retorna o existente."""
    forn_ok  = fornecedor and fornecedor != "A PREENCHER"
    valor_ok = valor_v and valor_v > 0
    status   = "a_pagar" if (forn_ok and valor_ok) else "pendente_revisao"
    cat_val  = categoria.value if categoria else None
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            """INSERT OR IGNORE INTO lancamentos
               (doc_id, pfm_codigo, ggv, fornecedor, valor, data_prevista_entrega, status, categoria)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (doc_id, pfm_codigo, ggv, fornecedor, valor_v, data_entrega, status, cat_val)
        )
        ja_existia = cur.rowcount == 0
        if ja_existia:
            row = con.execute(
                "SELECT status FROM lancamentos WHERE pfm_codigo=?", (pfm_codigo,)
            ).fetchone()
            status = row[0] if row else status
    return status, ja_existia

def _dados_doc(doc_id):
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT dados_claude FROM documentos WHERE id=?", (doc_id,)).fetchone()
    return row[0] if row else ""

_CAMPOS_RESUMO_RE = re.compile(
    r"^\s*-\s*\*{0,2}(Desconto|Condição de pagamento|Prazo de entrega|Data.prazo de entrega)\b",
    re.IGNORECASE
)

PFM_CODIGO_RE = re.compile(r"\b(GGV\d{2}-\d{3}(?:-R\d+)?)\b", re.IGNORECASE)

def _dados_display(dados):
    """Remove do texto do Claude os campos que já aparecem no bloco de resumo."""
    linhas = [l for l in dados.split('\n') if not _CAMPOS_RESUMO_RE.match(l)]
    return '\n'.join(linhas).strip()

def _resumo_gerar(doc_id):
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT dados_claude, tipo, ggv, condicao_pgto, data_entrega, desconto_rs, "
            "vencimento_pgto, encarregado, endereco_entrega FROM documentos WHERE id=?",
            (doc_id,)
        ).fetchone()
    if not row:
        return "Documento não encontrado.", None
    dados, tipo, ggv, condicao, data_ent, desconto_rs, vencimento, encarregado, endereco = row

    label_ggv = f"Obra {ggv}" if ggv != "nao_identificado" else "Obra não identificada"

    def _v(val):
        return None if (not val or val == "A PREENCHER") else val

    nome_claude = _v(_campo(dados, "Fornecedor"))
    cnpj        = _v(_campo(dados, "CNPJ/CPF"))
    pix         = _v(_campo(dados, "Chave PIX"))
    forn_db     = buscar_fornecedor(nome_claude, cnpj)
    if forn_db:
        fornecedor = forn_db.get("razao_social") or forn_db.get("nome") or nome_claude or "Fornecedor não identificado"
        cnpj = cnpj or forn_db.get("cnpj") or forn_db.get("cpf")
        pix  = pix or forn_db.get("chave_pix")
    else:
        fornecedor = nome_claude or "Fornecedor não identificado"
    vendedor   = _v(_campo(dados, "Vendedor"))
    vend_fone  = _v(_campo(dados, "Telefone do vendedor"))
    cond       = _v(condicao) or _v(_campo(dados, "Condição de pagamento"))
    entrega    = _v(data_ent) or _v(_campo(dados, "Prazo de entrega"))
    venc_txt   = _v(vencimento) or _v(_campo(dados, "Vencimento"))
    validade   = _v(_campo(dados, "Validade da proposta"))
    obs        = _obs(dados).strip()
    _obra      = buscar_obra(ggv)
    enc        = _v(encarregado) or _obra.get("encarregado_nome")

    subtotal_v, desconto_v, total_final_v = _calcular_totais(dados, desconto_rs)

    SEP = "──────────────────────────────────"
    linhas = []

    # Bloco 1 — Obra
    linhas.append(f"<b>{_esc_html(label_ggv)}</b>")
    linhas.append(SEP)

    # Bloco 2 — Fornecedor + dados de pagamento do fornecedor
    linhas.append(_esc_html(fornecedor))
    if cnpj: linhas.append(f"CNPJ  {_esc_html(cnpj)}")
    if pix:  linhas.append(f"PIX   {_esc_html(pix)}")
    if vendedor:
        cont = _esc_html(vendedor)
        if vend_fone:
            cont += f"  {_esc_html(vend_fone)}"
        linhas.append(f"Contato   {cont}")
    linhas.append(SEP)

    # Bloco 3 — Itens + Total
    bloco_itens = _bloco_itens(dados)
    for linha in bloco_itens.splitlines():
        if linha.strip():
            linhas.append(_esc_html(linha.strip()))
    if subtotal_v > 0:
        linhas.append(f"Total — R$ {_fmt_brl(subtotal_v)}")
    valor_total_doc = _totais_divergem(dados, subtotal_v)
    if valor_total_doc:
        linhas.append(
            f"⚠️ Valor total do documento: R$ {_fmt_brl(valor_total_doc)} — confira os itens"
        )
    linhas.append(SEP)

    # Bloco 4 — Financeiro (desconto → valor final → condição → vencimento)
    if desconto_v > 0 and subtotal_v > 0:
        pct = desconto_v / subtotal_v * 100
        linhas.append(f"Desconto — R$ {_fmt_brl(desconto_v)} ({pct:.0f}%)")
    if total_final_v > 0:
        linhas.append(f"<b>Valor final — R$ {_fmt_brl(total_final_v)}</b>")
    else:
        linhas.append("<b>Valor final: não informado</b>")
    linhas.append(_esc_html(cond) if cond else "Pagamento: não informado")
    linhas.append(_esc_html(venc_txt) if venc_txt else "Vencimento: não informado")
    linhas.append(SEP)

    # Bloco 5 — Logística
    linhas.append(f"Entrega: {_esc_html(entrega) if entrega else 'não informada'}")
    linhas.append(f"Endereço: {_esc_html(endereco) if endereco else 'não informado'}")
    if validade:
        linhas.append(f"Válido até: {_esc_html(validade)}")
    if enc:
        enc_fone = _obra.get("encarregado_fone", "")
        enc_txt  = f"{_esc_html(enc)} {enc_fone}".strip() if enc_fone else _esc_html(enc)
        linhas.append(f"Dúvidas: Dennis {DELTAD['fone']} ou {enc_txt}, encarregado")
    else:
        linhas.append(f"Dúvidas: Dennis {DELTAD['fone']}")
    linhas.append(SEP)

    # Bloco 6 — Observações (sempre mostrado)
    linhas.append(f"Obs: {_esc_html(obs) if obs else 'não informado'}")

    # Atenção quando obra não definida
    if ggv == "nao_identificado":
        linhas.append(SEP)
        linhas.append("⚠️ Defina a obra antes de gerar o Pedido de Compra.")

    return "\n".join(linhas), teclado_orcamento(doc_id, tipo, ggv)

_FORN_COLS = ["nome", "razao_social", "cnpj", "cpf", "chave_pix", "email",
              "whatsapp", "logradouro", "numero", "bairro", "cidade", "uf", "cep", "ramo", "cnae"]

def _formatar_cnae(codigo) -> Optional[str]:
    """7 dígitos (ex: 4744099) -> formato oficial do Cartão CNPJ (ex: '47.44-0-99')."""
    if not codigo:
        return None
    s = re.sub(r"\D", "", str(codigo)).zfill(7)
    if len(s) != 7:
        return None
    return f"{s[0:2]}.{s[2:4]}-{s[4]}-{s[5:7]}"

def _consultar_receita(cnpj_digits: str, timeout: float = 4.0) -> Optional[dict]:
    """Consulta CNPJ na Receita Federal via BrasilAPI. Nunca levanta — retorna None em qualquer falha."""
    try:
        req = urllib.request.Request(
            f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_digits}",
            headers={"User-Agent": "laura-bot"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        telefone     = data.get("ddd_telefone_1") or data.get("ddd_telefone_2") or None
        cnae_cod     = _formatar_cnae(data.get("cnae_fiscal"))
        cnae_desc    = data.get("cnae_fiscal_descricao") or None
        cnae_str     = f"{cnae_cod} - {cnae_desc}" if cnae_cod and cnae_desc else (cnae_desc or None)
        return {
            "razao_social": data.get("razao_social") or None,
            "cidade":       (data.get("municipio") or "").title() or None,
            "uf":           data.get("uf") or None,
            "email":        data.get("email") or None,
            "telefone":     telefone,
            "ramo":         cnae_desc,
            "cnae":         cnae_str,
        }
    except Exception:
        return None

def _criar_fornecedor_auto(nome_claude, cnpj_claude, ramo_claude, doc_id, chave_pix_claude=None):
    """Cadastra um fornecedor novo a partir de um orçamento com CNPJ ainda não conhecido.
    Tenta enriquecer com dado oficial da Receita; se a consulta falhar, marca para sincronizar depois."""
    if not cnpj_claude or cnpj_claude == "A PREENCHER":
        return
    cnpj_digits = re.sub(r"\D", "", cnpj_claude)
    # Só bloqueia a VII (dona do empreendimento, nunca é fornecedora). A DeltaD PODE ser cadastrada
    # aqui de verdade — ela é uma empresa técnica que fatura a VII por serviços (ex: GGV03-002),
    # diferente do guard de buscar_fornecedor() que ignora ambas por segurança contra Pagador
    # confundido com Fornecedor em boleto.
    if len(cnpj_digits) != 14 or cnpj_digits == DELTAD_CNPJ_DIGITS:
        return
    receita = _consultar_receita(cnpj_digits)
    # Ramo: prefere o que o Claude leu no documento (mais específico ao contexto da compra);
    # cai pro CNAE oficial da Receita só se o documento não tiver essa informação
    ramo_doc = ramo_claude if ramo_claude and ramo_claude != "A PREENCHER" else None
    ramo = ramo_doc or (receita.get("ramo") if receita else None)
    pix  = chave_pix_claude if chave_pix_claude and chave_pix_claude != "A PREENCHER" else None
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT OR IGNORE INTO fornecedores "
            "(nome, cnpj, razao_social, cidade, uf, ramo, cnae, email, whatsapp, chave_pix, origem, receita_pendente) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (nome_claude, cnpj_claude,
             receita["razao_social"] if receita else None,
             receita["cidade"] if receita else None,
             receita["uf"] if receita else None,
             ramo,
             receita.get("cnae") if receita else None,
             receita.get("email") if receita else None,
             receita.get("telefone") if receita else None,
             pix, f"Cadastro automático — doc {doc_id}",
             0 if receita else 1)
        )

def buscar_fornecedor(nome_claude, cnpj_claude=None):
    """Busca no BD: 1º por CNPJ exato, 2º por prefixo do nome."""
    with sqlite3.connect(DB_PATH) as con:
        sel = f"SELECT {', '.join(_FORN_COLS)} FROM fornecedores"

        # 1. CNPJ — mais confiável; ignora os nossos próprios CNPJs (dado de fatura extraído errado,
        # ex: Pagador de um boleto confundido com Fornecedor)
        if cnpj_claude and cnpj_claude != "A PREENCHER":
            cnpj_digits = re.sub(r"\D", "", cnpj_claude)
            if cnpj_digits not in CNPJS_PROPRIOS_DIGITS:
                row = con.execute(
                    f"{sel} WHERE REPLACE(REPLACE(REPLACE(cnpj,'.','' ),'/',''),'-','') = ? LIMIT 1",
                    (cnpj_digits,)
                ).fetchone()
                if row:
                    return dict(zip(_FORN_COLS, row))

        # 2. Prefixo do primeiro token do nome (evita falsos positivos de substring)
        if nome_claude and nome_claude != "A PREENCHER":
            primeiro = nome_claude.strip().upper().split()[0]
            row = con.execute(
                f"{sel} WHERE UPPER(nome) LIKE ? OR UPPER(razao_social) LIKE ? LIMIT 1",
                (f"{primeiro}%", f"{primeiro}%")
            ).fetchone()
            if row:
                return dict(zip(_FORN_COLS, row))

    return None

# ── PFM ───────────────────────────────────────────────────────────────────

def _esc_html(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

_MARCADORES_VAZIO = ("não identificad", "nao identificad", "não especificad", "nao especificad",
                     "não informad", "nao informad", "não encontrad", "nao encontrad")
_VALORES_VAZIO = {"n/a", "—", "-", ""}

def _campo_vazio(val: str) -> bool:
    """True se o valor extraído é um marcador de 'não achei', em qualquer gênero/frase
    (ex: 'Não identificada', 'não identificado no documento') — não só o masculino exato."""
    v = val.strip().lower()
    return v in _VALORES_VAZIO or v.startswith(_MARCADORES_VAZIO)

def _campo(dados, nome):
    for linha in dados.splitlines():
        stripped = linha.strip().lstrip("- *")
        if stripped.lower().startswith(nome.lower() + ":"):
            val = stripped.split(":", 1)[1].strip().strip("*").strip()
            if not _campo_vazio(val):
                return val
    return "A PREENCHER"

def _substituir_campo(dados, nome, novo_valor):
    linhas = dados.splitlines()
    for i, linha in enumerate(linhas):
        stripped = linha.strip().lstrip("- *")
        if stripped.lower().startswith(nome.lower() + ":"):
            linhas[i] = f"{nome}: {novo_valor}"
            return "\n".join(linhas)
    return dados + f"\n{nome}: {novo_valor}"

# Campos que legitimamente vêm depois de "Itens:" no template do PROMPT (Fase [orcamento]) —
# lista fechada, usada pra marcar o fim do bloco de itens com segurança. Mais confiável que a
# heurística antiga ("primeira linha sem número que tem ':'"), que falhava sempre que uma
# variação de formatação da Claude não incluía ':' na própria linha do cabeçalho "Itens" —
# nesse caso a função não achava o bloco original e caía num fallback que só ACRESCENTAVA o
# texto novo no fim do documento, nunca substituindo (ver LICOES_EXTRACAO.md, Lição #1).
_CAMPOS_APOS_ITENS_RE = r"^(valor total|desconto|condi[cç][aã]o|prazo|validade|observ)"

def _bloco_itens(dados):
    linhas = dados.splitlines()
    capturando, resultado = False, []
    for linha in linhas:
        stripped = linha.strip().lstrip("- *")
        if re.match(r"^(itens|materiais)\b", stripped, re.IGNORECASE):
            capturando = True
            inline = stripped.split(":", 1)[1].strip().strip("*").strip() if ":" in stripped else ""
            if inline:
                resultado.append(inline)
            continue
        if capturando:
            if stripped and re.match(_CAMPOS_APOS_ITENS_RE, stripped, re.IGNORECASE):
                break
            resultado.append(linha)
    return "\n".join(resultado).strip() or "Nenhum item encontrado."

def _substituir_itens(dados, novo_bloco):
    linhas = dados.splitlines()
    inicio, fim, capturando = None, len(linhas), False
    for i, linha in enumerate(linhas):
        stripped = linha.strip().lstrip("- *")
        if re.match(r"^(itens|materiais)\b", stripped, re.IGNORECASE):
            inicio = i
            capturando = True
            continue
        if capturando:
            if stripped and re.match(_CAMPOS_APOS_ITENS_RE, stripped, re.IGNORECASE):
                fim = i
                break
    if inicio is None:
        # Não achou o cabeçalho "Itens:" original — nunca acrescentar cegamente no fim (isso
        # corrompe o registro pra sempre: toda edição seguinte voltaria a só acrescentar, nunca
        # substituir, porque a próxima busca acharia ESTE acréscimo como se fosse o bloco real).
        # Em vez disso, insere antes do primeiro campo conhecido que vier depois de Itens.
        for i, linha in enumerate(linhas):
            stripped = linha.strip().lstrip("- *")
            if re.match(_CAMPOS_APOS_ITENS_RE, stripped, re.IGNORECASE):
                return "\n".join(linhas[:i] + ["Itens:"] + novo_bloco.splitlines() + [""] + linhas[i:])
        return dados + f"\nItens:\n{novo_bloco}"
    return "\n".join(linhas[:inicio + 1] + novo_bloco.splitlines() + linhas[fim:])

def _recalcular_itens(dados: str) -> str:
    """Após edição de itens, recalcula total de cada linha (qtde × unit) e atualiza Valor total."""
    linhas_out = []
    capturando = False
    novo_total = 0.0
    for linha in dados.splitlines():
        stripped = linha.strip().lstrip("- *")
        if re.match(r"^(itens|materiais)\b", stripped, re.IGNORECASE):
            capturando = True
            linhas_out.append(linha)
            continue
        if capturando:
            if re.match(_CAMPOS_APOS_ITENS_RE, stripped, re.IGNORECASE):
                capturando = False
                linhas_out.append(linha)
                continue
            m = ITEM_RE.match(stripped)
            if m:
                desc, qtde_str, und, val1, val2 = m.groups()
                qtde_v = _parse_qtde(qtde_str)
                num_m = re.match(r"^(\d+)\.", stripped)
                num = num_m.group(1) if num_m else "?"
                if val2:
                    unit_v  = _parse_brl(val1)
                    total_v = round(qtde_v * unit_v, 2)
                    novo_total += total_v
                    linhas_out.append(
                        f"{num}. {desc.strip()} ({qtde_str} {und.upper()}) — R$ {_fmt_brl(unit_v)} cada = R$ {_fmt_brl(total_v)}"
                    )
                    continue
                else:
                    novo_total += _parse_brl(val1)
            linhas_out.append(linha)
            continue
        linhas_out.append(linha)
    resultado = "\n".join(linhas_out)
    if novo_total > 0:
        resultado = _substituir_campo(resultado, "Valor total", f"R$ {_fmt_brl(novo_total)}")
    return resultado

ITEM_RE = re.compile(
    r"^\d+\.\s+(.+?)\s+\(([0-9,.]+)\s+([A-Za-zÀ-ÿ]{1,15}[²³0-9]{0,2})\)\s*[—–\-]+\s*R\$\s*([0-9.,]+)"
    r"(?:\s*cada\s*=\s*R\$\s*([0-9.,]+))?",
    re.IGNORECASE,
)

def _parse_brl(s):
    s = s.strip().replace(" ", "")
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    if "." in s:
        # sem vírgula: "." é separador de milhar quando o último grupo tem 3 dígitos
        # (ex: "5.000" = 5000,0), senão é decimal (ex: "5.5" = 5,5, "10.99" = 10,99)
        if len(s.rsplit(".", 1)[1]) == 3:
            return float(s.replace(".", ""))
    return float(s.replace(",", "."))

def _parse_qtde(s):
    """Quantidade de item de compra — diferente de valor monetário, "." aqui é sempre separador
    decimal, nunca de milhar (ex: '12.000' significa doze, não doze mil — o Claude às vezes usa
    ponto com 3 casas decimais pra escrever quantidade inteira). Compra de material de obra nunca
    tem quantidade real na casa dos milhares num item só."""
    s = s.strip().replace(" ", "")
    if not s:
        return 0.0
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    return float(s)

def _fmt_brl(v):
    s = f"{v:,.2f}"                                        # "6,292.93"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")  # "6.292,93"

def _fmt_qtde(v: float) -> str:
    if float(v).is_integer():
        return f"{int(v):,}".replace(",", ".")
    return _fmt_brl(v)

def _valor_por_extenso(valor: float) -> str:
    """'R$ 6.960,00' -> 'seis mil, novecentos e sessenta reais'; trata reais e centavos."""
    return num2words(valor, lang="pt_BR", to="currency")

def _itens(dados):
    """Retorna lista de dicts {desc, und, qtde, unit, total, _total_v} ou strings como fallback.
    Aceita tanto item(ns) na mesma linha do rótulo 'Itens:' (comum quando há um item só) quanto o
    formato usual de vários itens em linhas separadas abaixo do rótulo."""
    resultado, capturando = [], False
    for linha in dados.splitlines():
        stripped = linha.strip().lstrip("- *")
        if re.match(r"^(itens|materiais)\b", stripped, re.IGNORECASE):
            capturando = True
            inline = stripped.split(":", 1)[1].strip().strip("*").strip() if ":" in stripped else ""
            if not inline:
                continue
            stripped = inline
        if capturando:
            if not stripped:
                continue
            if re.match(_CAMPOS_APOS_ITENS_RE, stripped, re.IGNORECASE):
                break
            m = ITEM_RE.match(stripped)
            if m:
                desc, qtde_str, und, val1, val2 = m.groups()
                qtde_v = _parse_qtde(qtde_str)
                if val2:
                    unit_v  = _parse_brl(val1)
                    total_v = round(qtde_v * unit_v, 2)
                else:
                    total_v = _parse_brl(val1)
                    unit_v  = total_v / qtde_v if qtde_v else 0
                resultado.append({
                    "desc":     desc.strip(),
                    "und":      und.upper(),
                    "qtde":     qtde_str,
                    "unit":     _fmt_brl(unit_v),
                    "total":    _fmt_brl(total_v),
                    "_total_v": total_v,
                })
            elif stripped:
                resultado.append(stripped)
    return resultado

def _salvar_itens_pedido(pfm_codigo, itens):
    """Substitui os itens estruturados de um pedido (`itens_pedido`) — usado na geração inicial
    e em toda revisão, sempre refletindo a lista mais recente. Itens que o ITEM_RE não conseguiu
    parsear (fallback string) ainda são salvos, só sem os campos numéricos."""
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM itens_pedido WHERE pfm_codigo=?", (pfm_codigo,))
        for i, item in enumerate(itens, start=1):
            if isinstance(item, dict):
                con.execute(
                    "INSERT INTO itens_pedido "
                    "(pfm_codigo, numero, descricao, unidade, quantidade, valor_unitario, valor_total) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (pfm_codigo, i, item["desc"], item["und"],
                     _parse_qtde(item["qtde"]), _parse_brl(item["unit"]), item["_total_v"])
                )
            else:
                con.execute(
                    "INSERT INTO itens_pedido (pfm_codigo, numero, descricao) VALUES (?,?,?)",
                    (pfm_codigo, i, str(item))
                )

def _obs(dados):
    """Extrai o texto de Observações — aceita tanto 'Observações: texto' na mesma linha
    (formato real, sempre usado na prática) quanto texto em linhas separadas abaixo do rótulo."""
    resultado, capturando = [], False
    for linha in dados.splitlines():
        stripped = linha.strip().lstrip("- *")
        if stripped.lower().startswith("observaç"):
            capturando = True
            if ":" in stripped:
                inline = stripped.split(":", 1)[1].strip().strip("*").strip()
                if inline:
                    resultado.append(inline)
            continue
        if capturando and stripped:
            resultado.append(stripped.lstrip("- *"))
    return "\n".join(resultado)

def _calcular_totais(dados, desconto_rs):
    """Retorna (subtotal_v, desconto_v, total_final_v) a partir dos dados extraídos."""
    itens = _itens(dados)
    subtotal_v = sum(i.get("_total_v", 0) for i in itens if isinstance(i, dict))
    if not subtotal_v:
        try:
            subtotal_v = _parse_brl(re.sub(r"[^\d,.]", "", _campo(dados, "Valor total")))
        except Exception:
            subtotal_v = 0.0
    desconto_v = 0.0
    desconto_raw = desconto_rs or (
        _campo(dados, "Desconto") if _campo(dados, "Desconto") != "A PREENCHER" else None
    )
    if desconto_raw:
        try:
            desconto_v = _parse_brl(re.sub(r"[^\d,.]", "", str(desconto_raw)))
        except Exception:
            desconto_v = 0.0
    return subtotal_v, desconto_v, subtotal_v - desconto_v

def _totais_divergem(dados, subtotal_v) -> Optional[float]:
    """Compara a soma dos itens (subtotal_v) com o campo 'Valor total' extraído
    independentemente pela Claude. As duas leituras vêm de passos diferentes do mesmo
    documento — quando divergem além de centavos de arredondamento, é sinal de que a extração
    perdeu (ou inventou) alguma linha de item, não que um dos dois esteja "certo por padrão".
    Retorna o valor total extraído quando diverge, ou None quando bate ou não há valor extraído
    (nesse caso `_calcular_totais` já usa a soma dos itens como o próprio Valor total)."""
    valor_total_raw = _campo(dados, "Valor total")
    if not valor_total_raw or valor_total_raw == "A PREENCHER":
        return None
    try:
        valor_total_v = _parse_brl(re.sub(r"[^\d,.]", "", valor_total_raw))
    except Exception:
        return None
    if valor_total_v > 0 and subtotal_v > 0 and abs(valor_total_v - subtotal_v) > 0.01:
        return valor_total_v
    return None

def proximo_pfm_numero(ggv):
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT MAX(pfm_numero) FROM documentos WHERE ggv=? AND pfm_numero IS NOT NULL",
            (ggv,)
        ).fetchone()
    return (row[0] or 0) + 1

_PC_CSS = """
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
@page { size: A4; margin: 0; }
body { font-family: 'Inter', system-ui, -apple-system, sans-serif; -webkit-font-smoothing: antialiased; }
.page { background: #fff; width: 210mm; min-height: 297mm; padding: 16mm 18mm 12mm; display: flex; flex-direction: column; }
.header { display: flex; justify-content: space-between; align-items: flex-start; }
.company-brand { font-size: 12px; font-weight: 600; letter-spacing: 0.01em; color: #111827; }
.company-meta { font-size: 9.5px; color: #9CA3AF; margin-top: 6px; line-height: 1.75; }
.doc-meta { text-align: right; }
.doc-tipo { font-size: 9px; font-weight: 500; letter-spacing: 0.14em; text-transform: uppercase; color: #9CA3AF; }
.doc-number { font-size: 27px; font-weight: 700; color: #111827; letter-spacing: -0.025em; line-height: 1; margin-top: 5px; }
.doc-date { font-size: 9.5px; color: #9CA3AF; margin-top: 7px; }
.rule { border: none; border-top: 1px solid #E5E7EB; }
.rule-gap { margin: 28px 0; }
.context-block { display: grid; grid-template-columns: 1fr 1fr; gap: 20px 48px; }
.ctx-label { font-size: 9px; font-weight: 600; letter-spacing: 0.15em; text-transform: uppercase; color: #9CA3AF; margin-bottom: 5px; }
.ctx-value { font-size: 10.5px; color: #6B7280; line-height: 1.7; }
.supplier { margin-top: 6px; }
.supplier-name { font-size: 22px; font-weight: 600; color: #111827; letter-spacing: -0.015em; line-height: 1.2; }
.supplier-trade { font-size: 11px; color: #6B7280; margin-top: 5px; }
.supplier-meta { font-size: 10px; color: #9CA3AF; margin-top: 3px; }
.section-label { font-size: 9px; font-weight: 600; letter-spacing: 0.15em; text-transform: uppercase; color: #9CA3AF; margin-bottom: 16px; }
.item { display: flex; justify-content: space-between; align-items: flex-start; padding: 13px 0; border-bottom: 1px solid #F9FAFB; }
.item:last-child { border-bottom: none; }
.item-left { display: flex; gap: 16px; }
.item-num { font-size: 10px; font-weight: 500; color: #D1D5DB; min-width: 20px; padding-top: 1px; flex-shrink: 0; }
.item-desc { font-size: 11.5px; font-weight: 500; color: #374151; line-height: 1.4; }
.item-qty { font-size: 10px; color: #9CA3AF; margin-top: 3px; }
.item-value { font-size: 11.5px; font-weight: 500; color: #374151; white-space: nowrap; }
.financial-outer { display: flex; justify-content: flex-end; margin-top: 24px; }
.financial-inner { min-width: 216px; }
.fin-row { display: flex; justify-content: space-between; gap: 48px; padding: 4px 0; }
.fin-l { font-size: 10px; color: #9CA3AF; }
.fin-v { font-size: 10px; color: #6B7280; }
.fin-rule { border: none; border-top: 1px solid #E5E7EB; margin: 10px 0; }
.fin-total-row { display: flex; justify-content: space-between; align-items: baseline; gap: 48px; }
.fin-total-l { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #111827; }
.fin-total-v { font-size: 20px; font-weight: 700; color: #111827; letter-spacing: -0.02em; }
.bottom { display: grid; grid-template-columns: 1fr 1fr; gap: 48px; }
.bottom-label { font-size: 9px; font-weight: 600; letter-spacing: 0.15em; text-transform: uppercase; color: #9CA3AF; margin-bottom: 10px; }
.bottom-main { font-size: 11.5px; font-weight: 500; color: #374151; margin-bottom: 5px; }
.bottom-detail { font-size: 10px; color: #6B7280; line-height: 1.7; }
.footer-tagline { margin-top: auto; padding-top: 16px; text-align: center; font-size: 11px; font-style: italic; color: #B8BFC9; letter-spacing: 0.01em; }
"""

def _gerar_html_pc(doc_id: int) -> str:
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT ggv, dados_claude, condicao_pgto, data_entrega, endereco_entrega, "
            "desconto_rs, vencimento_pgto, criado_em FROM documentos WHERE id=?",
            (doc_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Documento {doc_id} não encontrado.")
        ggv, dados, condicao, data_ent_db, end_db, desconto_rs, vencimento, criado_em = row
        pfm_row = con.execute(
            "SELECT pfm_codigo FROM lancamentos WHERE doc_id=? ORDER BY id DESC LIMIT 1",
            (doc_id,)
        ).fetchone()
    pfm_codigo  = pfm_row[0] if pfm_row else "—"
    obra        = buscar_obra(ggv)

    nome_claude = _campo(dados, "Fornecedor")
    cnpj_claude = _campo(dados, "CNPJ/CPF")
    forn_db     = buscar_fornecedor(nome_claude, cnpj_claude)
    if forn_db:
        fornecedor = forn_db.get("razao_social") or forn_db.get("nome") or nome_claude
        cnpj       = forn_db.get("cnpj") or forn_db.get("cpf") or cnpj_claude
        ramo       = forn_db.get("ramo") or _campo(dados, "Ramo de atividade")
        _cidade    = forn_db.get("cidade") or ""
        _uf        = forn_db.get("uf") or ""
        if len(_cidade) > 30 or "/" in _cidade or any(c.isdigit() for c in _cidade):
            _cidade = _uf = ""
        forn_local = " · ".join(filter(None, [_cidade, _uf]))
        pix        = forn_db.get("chave_pix") or _campo(dados, "Chave PIX")
    else:
        fornecedor = nome_claude
        cnpj       = cnpj_claude
        ramo       = _campo(dados, "Ramo de atividade")
        forn_local = ""
        pix        = _campo(dados, "Chave PIX")

    nr_orc    = _campo(dados, "Número do orçamento")
    vendedor  = _campo(dados, "Vendedor")
    vend_fone = _campo(dados, "Telefone do vendedor")

    itens      = _itens(dados)
    subtotal_v, desconto_v, total_final_v = _calcular_totais(dados, desconto_rs)
    desconto_pct = (desconto_v / subtotal_v * 100) if subtotal_v > 0 and desconto_v > 0 else 0

    now          = datetime.now()
    data_emissao = f"{now.day} de {MESES[now.month-1]} de {now.year}"

    def _h(s): return _esc_html(str(s)) if s and s != "A PREENCHER" else ""

    # Bloco Origem
    origem_linhas = []
    if _h(nr_orc):
        origem_linhas.append(f"Orçamento #{_h(nr_orc)}")
    resp_nome = obra.get("responsavel_nome") or "Dennis"
    resp_fone = obra.get("responsavel_fone") or DELTAD["fone"]
    origem_linhas.append("Negociado via WhatsApp")
    contatos = [f"{_h(resp_nome)} {_h(resp_fone)}".strip()]
    if _h(vendedor):
        v = _h(vendedor)
        if _h(vend_fone):
            v += f" {_h(vend_fone)}"
        contatos.append(v)
    origem_linhas.append(" &middot; ".join(contatos))
    origem_html = "<br>".join(origem_linhas)

    # Bloco Entrega
    enc_nome = obra.get("encarregado_nome", "")
    enc_fone = obra.get("encarregado_fone", "")
    endereco_real = _h(end_db) or _h(obra.get("endereco_entrega"))
    entrega_linhas = [endereco_real or f"Obra {ggv}"]
    if _h(data_ent_db):
        entrega_linhas.append(f"Até {_h(data_ent_db)}")
    if enc_nome:
        enc_str = f"Encarregado: {_h(enc_nome)}"
        if enc_fone:
            enc_str += f" {_h(enc_fone)}"
        entrega_linhas.append(enc_str)
    entrega_html = "<br>".join(entrega_linhas)

    # Itens
    items_html = ""
    for i, item in enumerate(itens, 1):
        if not isinstance(item, dict):
            items_html += f'<div class="item"><div class="item-left"><span class="item-num">{i:02d}</span><div><div class="item-desc">{_esc_html(str(item))}</div></div></div></div>'
            continue
        und      = _esc_html(item.get("und", "un"))
        qty_line = f'<div class="item-qty">{_esc_html(item["qtde"])} {und} &nbsp;&middot;&nbsp; R$ {_esc_html(item["unit"])}/{und}</div>' if item.get("qtde") else ""
        items_html += (
            f'<div class="item">'
            f'<div class="item-left"><span class="item-num">{i:02d}</span>'
            f'<div><div class="item-desc">{_esc_html(item.get("desc",""))}</div>{qty_line}</div></div>'
            f'<div class="item-value">R$ {_esc_html(item.get("total",""))}</div>'
            f'</div>'
        )

    # Financeiro
    fin_html = f'<div class="fin-row"><span class="fin-l">Subtotal</span><span class="fin-v">R$ {_fmt_brl(subtotal_v)}</span></div>'
    if desconto_v > 0:
        pct_str = f"{desconto_pct:.2f}".replace(".", ",")
        fin_html += f'<div class="fin-row"><span class="fin-l">Desconto {pct_str}%</span><span class="fin-v">&minus;R$ {_fmt_brl(desconto_v)}</span></div>'
    fin_html += f'<hr class="fin-rule"><div class="fin-total-row"><span class="fin-total-l">Total</span><span class="fin-total-v">R$ {_fmt_brl(total_final_v)}</span></div>'

    # Pagamento e entrega (bottom)
    pgto_detail = ""
    if _h(pix):
        pgto_detail += f"Chave: {_h(pix)}<br>"
    if _h(vencimento):
        pgto_detail += f"Vencimento: {_h(vencimento)}"
    end_entrega  = _h(end_db or obra.get("endereco_entrega", ""))

    # Fornecedor meta
    forn_meta_parts = []
    if _h(cnpj):
        forn_meta_parts.append(f"CNPJ {_h(cnpj)}")
    if forn_local:
        forn_meta_parts.append(_esc_html(forn_local))
    forn_meta = " &nbsp;&middot;&nbsp; ".join(forn_meta_parts)

    ramo_html  = f'<div class="supplier-trade">{_esc_html(ramo)}</div>' if _h(ramo) else ""
    forn_meta_html = f'<div class="supplier-meta">{forn_meta}</div>' if forn_meta else ""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Pedido de Compra #{pfm_codigo}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
<style>{_PC_CSS}</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div>
      <div class="company-brand">Verschoor Investimentos Imobiliários</div>
      <div class="company-meta">CNPJ {DELTAD['cnpj']} &nbsp;&middot;&nbsp; I.E. {DELTAD['ie']}<br>{_esc_html(DELTAD['end'])}</div>
    </div>
    <div class="doc-meta">
      <div class="doc-tipo">Pedido de Compra</div>
      <div class="doc-number">#{pfm_codigo}</div>
      <div class="doc-date">{data_emissao}</div>
    </div>
  </div>
  <hr class="rule rule-gap">
  <div class="context-block">
    <div><div class="ctx-label">Origem</div><div class="ctx-value">{origem_html}</div></div>
    <div><div class="ctx-label">Entrega</div><div class="ctx-value">{entrega_html}</div></div>
  </div>
  <hr class="rule rule-gap">
  <div class="section-label" style="margin-bottom:6px;">Fornecedor</div>
  <div class="supplier">
    <div class="supplier-name">{_esc_html(fornecedor)}</div>
    {ramo_html}
    {forn_meta_html}
  </div>
  <hr class="rule" style="margin-top:32px;margin-bottom:28px;">
  <div class="section-label">Itens solicitados</div>
  {items_html}
  <div class="financial-outer">
    <div class="financial-inner">{fin_html}</div>
  </div>
  <hr class="rule" style="margin-top:28px;margin-bottom:28px;">
  <div class="bottom">
    <div>
      <div class="bottom-label">Pagamento</div>
      <div class="bottom-main">{_h(condicao) or 'PIX à vista'}</div>
      <div class="bottom-detail">{pgto_detail}</div>
    </div>
    <div>
      <div class="bottom-label">Entrega</div>
      <div class="bottom-main">{_h(data_ent_db) or '—'}</div>
      <div class="bottom-detail">{end_entrega}</div>
    </div>
  </div>
  <div class="footer-tagline">Laura não é uma ferramenta que você usa. É uma memória que você carrega.</div>
</div>
</body>
</html>"""

async def _html_para_pdf(html_str: str, formato: str = "A4", paisagem: bool = False) -> bytes:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page()
        await page.set_content(html_str, wait_until="networkidle")
        pdf     = await page.pdf(format=formato, landscape=paisagem, print_background=True)
        await browser.close()
        return pdf

def _gerar_html_recibo(parcela_id: int) -> str:
    """Recibo de pagamento de uma parcela — mesmo estilo visual do PC 2.0, formato A5 paisagem."""
    parcela = _buscar_parcela(parcela_id)
    if not parcela:
        raise ValueError(f"Parcela {parcela_id} não encontrada.")
    _, pfm_codigo, valor_parcela, data_parcela, *_ = parcela
    pedido = buscar_pedido(pfm_codigo)
    if not pedido:
        raise ValueError(f"Pedido {pfm_codigo} não encontrado.")
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT dados_claude FROM documentos WHERE id=?", (pedido.doc_id,)).fetchone()
    dados = row[0] if row else ""

    nome_claude = _campo(dados, "Fornecedor")
    cnpj_claude = _campo(dados, "CNPJ/CPF")
    forn_db = buscar_fornecedor(nome_claude, cnpj_claude)
    if forn_db:
        prestador_nome = forn_db.get("razao_social") or forn_db.get("nome") or nome_claude
        prestador_doc  = forn_db.get("cnpj") or forn_db.get("cpf") or cnpj_claude
        prestador_end  = " ".join(filter(None, [forn_db.get("logradouro"), forn_db.get("numero")]))
        _cidade, _uf   = forn_db.get("cidade") or "", forn_db.get("uf") or ""
        prestador_local = " · ".join(filter(None, [_cidade, _uf]))
    else:
        prestador_nome, prestador_doc = pedido.fornecedor, pedido.cnpj
        prestador_end = prestador_local = ""

    itens = _itens(dados)
    if itens:
        def _desc_item(i):
            if not isinstance(i, dict):
                return str(i)
            if i.get("qtde") and i.get("und"):
                return f"{_fmt_qtde(_parse_qtde(i['qtde']))} {i['und']} de {i['desc']}"
            return i["desc"]
        descricao = "; ".join(_desc_item(i) for i in itens)
    else:
        descricao = pedido.fornecedor

    now          = datetime.now()
    data_emissao = f"{now.day} de {MESES[now.month-1]} de {now.year}"
    valor_fmt    = f"R$ {_fmt_brl(valor_parcela)}"
    valor_extenso = _valor_por_extenso(valor_parcela)
    texto_recibo = (
        f"Recebi de {DELTAD['nome']}, CNPJ {DELTAD['cnpj']}, a importância supra de {valor_fmt} "
        f"( {valor_extenso} ), referente à compra de {descricao} — Pedido de Compra #{pfm_codigo}. "
        "Por ser a expressão da verdade, dou quitação pela importância recebida e pela etapa de "
        "serviços/materiais prestados, firmando o presente recibo nesta data."
    )

    def _h(s):
        return _esc_html(str(s)) if s and s != "A PREENCHER" else ""

    contratado_linhas = [prestador_nome, prestador_doc]
    if _h(prestador_end):
        contratado_linhas.append(prestador_end)
    if _h(prestador_local):
        contratado_linhas.append(prestador_local)
    contratado_html = "<br>".join(_h(l) for l in contratado_linhas if _h(l))

    _recibo_css_extra = """
@page { size: A5 landscape; margin: 0; }
.page { width: 210mm; height: 148mm; min-height: 0; padding: 10mm 16mm; }
.recibo-titulo { font-size: 26px; font-weight: 700; color: #111827; letter-spacing: -0.02em; }
.recibo-codigo { font-size: 12px; font-weight: 500; color: #6B7280; margin-top: 3px; }
.assinatura-bloco { margin-top: auto; padding-top: 10mm; display: flex; justify-content: center; }
.assinatura-linha { width: 85mm; border-top: 1px solid #111827; padding-top: 6px; text-align: center; }
.assinatura-nome { font-size: 10.5px; font-weight: 600; color: #111827; }
.assinatura-doc { font-size: 9px; color: #6B7280; margin-top: 2px; }
"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><style>{_PC_CSS}{_recibo_css_extra}</style></head>
<body>
<div class="page">
  <div class="header" style="flex-direction:column; align-items:center; text-align:center;">
    <div class="recibo-titulo">RECIBO</div>
    <div class="recibo-codigo">Pedido #{_h(pfm_codigo)}</div>
    <div class="doc-date" style="margin-top:5px;">{_h(data_emissao)}</div>
  </div>
  <hr class="rule rule-gap" style="margin: 14px 0;">
  <div class="context-block">
    <div>
      <div class="ctx-label">Contratante</div>
      <div class="ctx-value">{_h(DELTAD['nome'])}<br>CNPJ {_h(DELTAD['cnpj'])}</div>
    </div>
    <div>
      <div class="ctx-label">Contratado</div>
      <div class="ctx-value">{contratado_html}</div>
    </div>
  </div>
  <div style="margin-top:16px;">
    <div class="section-label">Declaração</div>
    <div class="ctx-value" style="line-height:1.7;">{_h(texto_recibo)}</div>
  </div>
  <div class="financial-outer" style="margin-top:14px;">
    <div class="financial-inner">
      <div class="fin-total-row">
        <div class="fin-total-l">VALOR RECEBIDO</div>
        <div class="fin-total-v">{_h(valor_fmt)}</div>
      </div>
    </div>
  </div>
  <div class="bottom" style="margin-top:14px;">
    <div>
      <div class="bottom-label">Pago em</div>
      <div class="bottom-main">{_h(data_parcela) or _h(data_emissao)}</div>
    </div>
    <div>
      <div class="bottom-label">Forma de pagamento</div>
      <div class="bottom-main">PIX</div>
    </div>
  </div>
  <div class="assinatura-bloco">
    <div class="assinatura-linha">
      <div class="assinatura-nome">{_h(prestador_nome)}</div>
      <div class="assinatura-doc">{_h(prestador_doc)}</div>
    </div>
  </div>
</div>
</body>
</html>"""

def _gerar_html_lista(lista_id: int, com_precos: bool) -> str:
    """Lista de Compras em PDF — mesmo estilo visual do PC 2.0 (_PC_CSS reaproveitado sem
    CSS extra), sem bloco de fornecedor: a Lista é anterior à negociação (Política de
    Compras, Princípio 2), não tem fornecedor definido ainda.

    Duas variantes do mesmo documento, não duas funções paralelas (Dennis, 2026-07-05):
    `com_precos=True` — versão interna, com a referência de preço (SINAPI/própria) já
    calculada, pra o Dennis comparar contra as propostas recebidas.
    `com_precos=False` — versão pra encaminhar a fornecedores via WhatsApp pedindo
    orçamento; os campos de preço ficam em branco (o fornecedor preenche), pra nunca revelar
    a própria referência de preço numa negociação ainda não começou."""
    lista = buscar_lista(DB_PATH, lista_id)
    if not lista:
        raise ValueError(f"Lista de Compras {lista_id} não encontrada.")
    ggv = lista["ggv"]
    obra = buscar_obra(ggv) or {}
    endereco    = lista.get("endereco_entrega") or obra.get("endereco_entrega") or "—"
    observacoes = lista.get("observacoes") or "—"
    itens = listar_itens(DB_PATH, lista_id)

    now          = datetime.now()
    data_emissao = f"{now.day} de {MESES[now.month-1]} de {now.year}"

    items_html = ""
    for i, item in enumerate(itens, 1):
        qtde, und = item.get("quantidade"), item.get("unidade")
        if qtde is not None and und:
            detalhe = f"{_fmt_qtde_segura(qtde)} {und}"
        elif und:
            detalhe = und
        elif qtde is not None:
            detalhe = _fmt_qtde_segura(qtde)
        else:
            detalhe = ""
        extras = []
        if item.get("fabricante"):
            extras.append(_esc_html(item["fabricante"]))
        if item.get("codigo"):
            extras.append(f"cód. {_esc_html(item['codigo'])}")

        preco_ref = _melhor_referencia_preco(item) if com_precos else None
        if preco_ref is not None and und:
            extras.append(f"R$ {_fmt_brl(preco_ref)}/{und}")
        extra_str = " &middot; ".join(extras)
        if extra_str:
            detalhe = f"{detalhe} &middot; {extra_str}" if detalhe else extra_str
        qty_line = f'<div class="item-qty">{detalhe}</div>' if detalhe else ""

        if com_precos:
            total_item = preco_ref * qtde if (preco_ref is not None and qtde is not None) else None
            valor_html = f'<div class="item-value">R$ {_fmt_brl(total_item)}</div>' if total_item is not None else '<div class="item-value">—</div>'
        else:
            valor_html = '<div class="item-value" style="border-bottom:1px solid #D1D5DB;min-width:70px;">&nbsp;</div>'

        items_html += (
            f'<div class="item"><div class="item-left">'
            f'<span class="item-num">{i:02d}</span>'
            f'<div><div class="item-desc">{_esc_html(item["descricao"])}</div>{qty_line}</div>'
            f'</div>{valor_html}</div>'
        )
    if not items_html:
        items_html = '<div class="item-qty">Nenhum item nesta lista.</div>'

    if com_precos:
        total_referencia, total_parcial = _calcular_referencia_total(itens)
        total_str = f"R$ {_fmt_brl(total_referencia)}"
        if total_parcial:
            total_str += " (parcial)"
        financeiro_html = f"""
  <div class="financial-outer">
    <div class="financial-inner">
      <div class="fin-total-row"><span class="fin-total-l">Referência estimada</span><span class="fin-total-v">{total_str}</span></div>
    </div>
  </div>"""
        section_label = "Itens"
    else:
        financeiro_html = ""
        section_label = "Itens — solicitamos cotação de preço e prazo"

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Lista de Compras — Obra {_esc_html(ggv)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
<style>{_PC_CSS}</style>
</head>
<body>
<div class="page">
  <div class="header">
    <div>
      <div class="company-brand">Verschoor Investimentos Imobiliários</div>
      <div class="company-meta">CNPJ {DELTAD['cnpj']} &nbsp;&middot;&nbsp; I.E. {DELTAD['ie']}<br>{_esc_html(DELTAD['end'])}</div>
    </div>
    <div class="doc-meta">
      <div class="doc-tipo">Lista de Compras</div>
      <div class="doc-number" style="font-size:20px;">Obra {_esc_html(ggv)}</div>
      <div class="doc-date">{data_emissao}</div>
    </div>
  </div>
  <hr class="rule rule-gap">
  <div class="context-block">
    <div><div class="ctx-label">Endereço de entrega</div><div class="ctx-value">{_esc_html(endereco)}</div></div>
    <div><div class="ctx-label">Observações</div><div class="ctx-value">{_esc_html(observacoes)}</div></div>
  </div>
  <hr class="rule" style="margin-top:32px;margin-bottom:28px;">
  <div class="section-label">{section_label}</div>
  {items_html}{financeiro_html}
  <div class="footer-tagline">Laura não é uma ferramenta que você usa. É uma memória que você carrega.</div>
</div>
</body>
</html>"""

def gerar_pfm(doc_id, categoria=None, pfm_codigo_override=None):
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT ggv, dados_claude, condicao_pgto, data_entrega, endereco_entrega, desconto_rs, caminho FROM documentos WHERE id=?",
            (doc_id,)
        ).fetchone()
    if row is None:
        raise ValueError(f"Documento {doc_id} não encontrado no banco.")
    ggv, dados, condicao, data_entrega_db, endereco, desconto_rs, caminho_original = row

    nome_claude   = _campo(dados, "Fornecedor")
    cnpj_claude   = _campo(dados, "CNPJ/CPF")
    ramo_claude   = _campo(dados, "Ramo de atividade")
    resumo_claude = _campo(dados, "Resumo da compra")
    forn_db       = buscar_fornecedor(nome_claude, cnpj_claude)

    if forn_db:
        fornecedor = forn_db.get("razao_social") or forn_db.get("nome") or nome_claude
        cnpj       = forn_db.get("cnpj") or forn_db.get("cpf") or cnpj_claude
        pix        = forn_db.get("chave_pix") or _campo(dados, "Chave PIX")
        forn_logr  = " ".join(filter(None, [forn_db.get("logradouro"), forn_db.get("numero")]))
        forn_bairro = forn_db.get("bairro") or ""
        # Valida cidade: máx 30 chars, sem '/', sem dígitos — filtra dados errados do import
        _cidade = forn_db.get("cidade") or ""
        _uf     = forn_db.get("uf") or ""
        _cep    = forn_db.get("cep") or ""
        if len(_cidade) > 30 or "/" in _cidade or any(c.isdigit() for c in _cidade):
            _cidade = _uf = _cep = ""
        forn_cidade  = " / ".join(filter(None, [_cidade, _uf, _cep]))
        forn_email   = forn_db.get("email") or ""
        forn_fone    = forn_db.get("whatsapp") or ""
        forn_contato = forn_db.get("contato") or ""
        ramo         = forn_db.get("ramo") or ramo_claude
        cnpj_key = forn_db.get("cnpj") or forn_db.get("cpf")
        # Persiste ramo se ainda não estava cadastrado
        if not forn_db.get("ramo") and ramo_claude and ramo_claude != "A PREENCHER":
            if cnpj_key:
                with sqlite3.connect(DB_PATH) as _con:
                    _con.execute("UPDATE fornecedores SET ramo=? WHERE cnpj=? OR cpf=?",
                                 (ramo_claude, cnpj_key, cnpj_key))
        # Persiste chave PIX se ainda não estava cadastrada — assim o próximo pedido do mesmo
        # fornecedor já vem com o PIX preenchido, mesmo que o documento novo não repita o dado
        pix_claude = _campo(dados, "Chave PIX")
        if not forn_db.get("chave_pix") and pix_claude and pix_claude != "A PREENCHER":
            if cnpj_key:
                with sqlite3.connect(DB_PATH) as _con:
                    _con.execute("UPDATE fornecedores SET chave_pix=? WHERE cnpj=? OR cpf=?",
                                 (pix_claude, cnpj_key, cnpj_key))
            pix = pix_claude
    else:
        fornecedor  = nome_claude
        cnpj        = cnpj_claude
        pix         = _campo(dados, "Chave PIX")
        ramo        = ramo_claude
        forn_logr = forn_bairro = forn_cidade = forn_email = forn_fone = forn_contato = ""
        _criar_fornecedor_auto(nome_claude, cnpj_claude, ramo_claude, doc_id, pix)

    prazo        = _campo(dados, "Prazo de entrega")
    if prazo == "A PREENCHER":
        prazo = _campo(dados, "Data/prazo de entrega")
    data_entrega = data_entrega_db or "A PREENCHER"
    itens        = _itens(dados)
    obs          = _obs(dados)

    subtotal_v, desconto_v, total_final_v = _calcular_totais(dados, desconto_rs)
    valor = f"R$ {_fmt_brl(total_final_v)}" if total_final_v > 0 else _campo(dados, "Valor total")

    if pfm_codigo_override:
        pfm_codigo = pfm_codigo_override
    else:
        pfm_num    = proximo_pfm_numero(ggv)
        pfm_codigo = f"{ggv}-{pfm_num:03d}"
        atualizar(doc_id, pfm_numero=pfm_num, status="pfm_gerado")

    # itens_pedido sempre reflete o pedido base, mesmo quando esta chamada é uma revisão
    # (pfm_codigo aqui pode vir como "GGV03-007-R01" — nunca deve virar uma chave separada)
    pfm_codigo_base_itens = re.sub(r"-R\d+$", "", pfm_codigo)
    _salvar_itens_pedido(pfm_codigo_base_itens, itens)

    # NOTE: o DOCX deixou de ser gerado (2026-07-02) — o PDF (via _gerar_html_pc/_html_para_pdf)
    # é o único documento entregue. Esta função continua responsável por definir o código do
    # pedido, salvar os itens e registrar o lançamento financeiro.

    pasta = _pasta_pfm(ggv)
    pasta.mkdir(parents=True, exist_ok=True)
    prefixo   = "TESTE-" if TEST_MODE else ""
    nome_base = _nome_base_pfm(pfm_codigo, fornecedor, resumo_claude, prefixo)
    caminho   = pasta / f"{nome_base}.pdf"

    if pfm_codigo_override:
        lanc_status, ja_existia = "a_pagar", True
        # Revisão pode ter corrigido fornecedor/valor/data (ex: item com preço errado) — sem
        # isto, o lançamento (fonte do Cockpit da Obra e da Tela do Pedido) ficava com o valor
        # antigo pra sempre, mesmo com o PDF revisado mostrando o valor certo. Nunca inventa nem
        # apaga parcela — só reconcilia status/valor_pago contra a soma das parcelas já
        # registradas e o valor corrigido (ex: desconto negociado depois de já ter pago).
        with sqlite3.connect(DB_PATH) as _con:
            _con.execute(
                "UPDATE lancamentos SET fornecedor=?, valor=?, data_prevista_entrega=? WHERE pfm_codigo=?",
                (fornecedor, total_final_v, data_entrega_db, pfm_codigo_base_itens)
            )
        _recalcular_status_pagamento(pfm_codigo_base_itens, total_final_v)
    else:
        lanc_status, ja_existia = registrar_lancamento(
            doc_id, pfm_codigo, ggv, fornecedor, total_final_v, data_entrega_db, categoria
        )
        atualizar(doc_id, caminho_pfm=str(caminho))
        # Arquiva o orçamento original em "00 Orçamentos" — só na geração original, não em revisões
        if caminho_original and Path(caminho_original).exists():
            ext_original = Path(caminho_original).suffix
            destino = _pasta_orcamentos(ggv) / f"{nome_base}{ext_original}"
            try:
                shutil.copy2(caminho_original, destino)
            except OSError:
                pass
    return caminho, pfm_codigo, fornecedor, total_final_v, lanc_status, ja_existia

# ── Comprovante PIX ────────────────────────────────────────────────────────

def parse_comprovante(dados_claude: str) -> dict:
    """Extrai campos estruturados do texto retornado pelo Claude para comprovante_pix."""
    valor_str = _campo(dados_claude, "Valor")
    try:
        valor_v = _parse_brl(re.sub(r"[^\d,.]", "", valor_str)) if valor_str != "A PREENCHER" else 0.0
    except Exception:
        valor_v = 0.0
    return {
        "valor_v":      valor_v,
        "valor_fmt":    _fmt_brl(valor_v) if valor_v > 0 else valor_str,
        "data":         _campo(dados_claude, "Data do pagamento"),
        "favorecido":   _campo(dados_claude, "Favorecido"),
        "cnpj":         _campo(dados_claude, "CNPJ/CPF do favorecido"),
        "chave_pix":    _campo(dados_claude, "Chave PIX"),
        "instituicao":  _campo(dados_claude, "Instituição financeira"),
        "id_transacao": _campo(dados_claude, "ID da transação"),
        "obs":          _campo(dados_claude, "Identificador / Observação"),
    }

def buscar_candidatos_pix(valor_v: float, favorecido: str, cnpj: str) -> list:
    """Pontua TODOS os lançamentos A PAGAR com saldo em aberto e retorna a lista completa,
    ordenada por relevância (score, depois proximidade de valor) — não só os 3 melhores.
    Serve também como visão gerencial do que está pendente, não só como matching de comprovante."""
    cnpj_digits = re.sub(r"\D", "", cnpj) if cnpj and cnpj != "A PREENCHER" else ""
    fav_token   = favorecido.strip().upper().split()[0] if favorecido and favorecido != "A PREENCHER" else ""

    # Tenta validar o nome via CNPJ na tabela de fornecedores
    nome_canonico_token = ""
    if cnpj_digits:
        with sqlite3.connect(DB_PATH) as con:
            row = con.execute(
                "SELECT nome FROM fornecedores "
                "WHERE REPLACE(REPLACE(REPLACE(cnpj,'.',''),'/',''),'-','') = ? LIMIT 1",
                (cnpj_digits,)
            ).fetchone()
        if row:
            nome_canonico_token = row[0].strip().upper().split()[0]

    with sqlite3.connect(DB_PATH) as con:
        rows = con.execute(
            "SELECT pfm_codigo, ggv, fornecedor, valor FROM lancamentos WHERE status='a_pagar'"
        ).fetchall()

    candidatos = []
    for pfm_codigo, ggv, fornecedor, valor_lanc in rows:
        score     = 0
        forn_token = (fornecedor or "").strip().upper().split()[0] if fornecedor else ""

        # Valor — compara com o saldo restante (valor - parcelas já pagas), não o valor original,
        # porque pagamento parcelado é o caso normal, não exceção (ver parcelas_pagamento)
        saldo = valor_lanc - _total_pago(pfm_codigo) if valor_lanc else 0
        if valor_v > 0 and saldo > 0:
            if abs(valor_v - saldo) <= 0.01:
                score += 3
            elif abs(valor_v - saldo) / saldo <= 0.10:
                score += 1
            elif valor_v < saldo:
                score += 1  # pagamento parcial — valor livre, ver Fiada de pagamento parcelado

        # Nome — CNPJ validado tem peso maior que coincidência direta
        if nome_canonico_token and forn_token == nome_canonico_token:
            score += 3
        elif fav_token and forn_token == fav_token:
            score += 2

        if saldo > 0:
            candidatos.append({
                "pfm_codigo": pfm_codigo,
                "ggv":        ggv,
                "fornecedor": fornecedor,
                "valor_lanc": valor_lanc,
                "saldo":      saldo,
                "score":      score,
            })

    # Desempate por proximidade de valor — dentro do mesmo score, o saldo mais perto do valor
    # pago vem primeiro (em vez de ordem de inserção, que sempre favorecia os pedidos mais antigos)
    candidatos.sort(key=lambda c: (-c["score"], abs(valor_v - c["saldo"]) if valor_v > 0 else 0))
    return candidatos

def mostrar_comprovante_candidatos(dados: dict, candidatos: list) -> str:
    """Formata a mensagem de comprovante + candidatos para o Telegram. Sem IO."""
    def _conf(score):
        if score >= 5: return "exato"
        if score >= 3: return "próximo"
        return ""

    linhas = ["Pagamento identificado.\n"]
    if dados["favorecido"] != "A PREENCHER":
        linhas.append(f"{dados['favorecido']} — R$ {dados['valor_fmt']}")
    else:
        linhas.append(f"R$ {dados['valor_fmt']}")
    if dados["data"]        != "A PREENCHER": linhas.append(dados["data"])
    if dados["instituicao"] != "A PREENCHER": linhas.append(dados["instituicao"])
    if dados["obs"]         != "A PREENCHER": linhas.append(f"Ref: {dados['obs']}")

    linhas.append("")

    if not candidatos:
        linhas.append("Nenhum pedido em aberto corresponde a este pagamento.")
        return "\n".join(linhas)

    total_pendente = sum(c["saldo"] for c in candidatos)
    linhas.append(f"Qual pedido este pagamento quita? (total pendente: R$ {_fmt_brl(total_pendente)})\n")
    for c in candidatos:
        valor_fmt = f"R$ {_fmt_brl(c['saldo'])}" if c["saldo"] else "—"
        conf = _conf(c["score"])
        linha = f"🟡 #{c['pfm_codigo']} · {c['fornecedor']} · {valor_fmt}"
        if conf:
            linha += f" · {conf}"
        linhas.append(linha)

    return "\n".join(linhas)

# ── UI helpers ─────────────────────────────────────────────────────────────

def parse_resposta(texto):
    tipo, ggv = "nao_relacionado", "nao_identificado"
    corpo = []
    for linha in texto.strip().splitlines():
        if linha.startswith("TIPO:"):
            tipo = linha.split(":", 1)[1].strip().strip("[]").split("|")[0].strip()
        elif linha.startswith("GGV:"):
            ggv = linha.split(":", 1)[1].strip().strip("[]").split("|")[0].strip()
        else:
            corpo.append(linha)
    return tipo, ggv, "\n".join(corpo).strip()

def mostrar_cockpit_obra(obra):
    codigo    = obra.get("codigo", "")
    desc      = obra.get("descricao", "") or ""
    enc_nome  = obra.get("encarregado_nome", "") or ""
    enc_fone  = obra.get("encarregado_fone", "") or ""
    resp_nome = obra.get("responsavel_nome", "") or ""
    resp_fone = obra.get("responsavel_fone", "") or ""
    end       = obra.get("endereco_entrega", "") or ""

    # Header: "GGV03 — Condomínio residencial" + detalhe em linha separada
    if "," in desc:
        titulo, detalhe = desc.split(",", 1)
        titulo  = titulo.replace(codigo, "").strip()
        detalhe = detalhe.strip().rstrip(".")
    else:
        titulo  = desc.replace(codigo, "").strip() or "Sem descrição"
        detalhe = ""
    cabecalho = f"{codigo} — {titulo}"
    if detalhe:
        cabecalho += f"\n{detalhe}"

    SEP = "──────────────────────────────"

    # Placeholder financeiro — Fiada 5b-1
    financeiro = "⚪ Nenhum lançamento registrado"

    # Contatos com separador · consistente
    enc_txt  = f"Encarregado · {enc_nome} · {enc_fone}".strip(" ·") if enc_nome else "Encarregado · —"
    resp_txt = f"Responsável · {resp_nome} · {resp_fone}".strip(" ·") if resp_nome else "Responsável · —"

    # Endereço: remove CEP e troca " - " por " · "
    end_curto = re.sub(r"\s+CEP[\s\d\.\-]+$", "", end).replace(" - ", " · ") if end else ""

    contatos = f"{enc_txt}\n{resp_txt}"
    if end_curto:
        contatos += f"\nEntrega · {end_curto}"

    return f"{cabecalho}\n\n{SEP}\n{financeiro}\n{SEP}\n{contatos}"

_SAUDACOES_RE = re.compile(
    r"^\s*(oi|olá|ola|bom\s*dia|boa\s*tarde|boa\s*noite|hey|e\s*a[íi]|hello|hi|tudo\s*bem|tudo\s*bom)\W*$",
    re.IGNORECASE
)
_OBRAS_RE = re.compile(r"^\s*obras?\s*$", re.IGNORECASE)

def mostrar_boas_vindas():
    return (
        "Por onde quer começar?\n\n"
        "Obras — todas as obras e pedidos\n"
        "Ajuda — pedidos de compra, pagamentos e consultas"
    )

def teclado_boas_vindas():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Obras",  callback_data="menu_obras")],
        [InlineKeyboardButton("❓ Ajuda",  callback_data="menu_ajuda")],
        [InlineKeyboardButton("✖ Fechar", callback_data="obras_fechar")],
    ])

def mostrar_ajuda():
    return (
        "No que posso ajudar?\n\n"
        "<b>Cadastrar pedido de compra</b>\n"
        "Envie a foto ou arquivo do orçamento.\n\n"
        "<b>Confirmar pagamento</b>\n"
        "Envie o comprovante PIX.\n\n"
        "<b>Incluir nota fiscal</b>\n"
        "Envie o PDF ou foto da NF-e.\n\n"
        "<b>Registrar entrega</b>\n"
        "Envie a foto ou arquivo, ou use /entrega. Também disponível no botão 📦 Entregue dentro do pedido.\n\n"
        "<b>Montar lista de compras</b>\n"
        "Use /lista e envie a lista — texto, foto ou PDF. Laura interpreta os itens pra você. "
        "Para voltar numa lista já gerada, digite o código da obra e toque em 📝 Listas de Compras.\n\n"
        "<b>Consultas diretas</b>\n"
        "Digite o código da obra (GGV03) ou do pedido (GGV03-009)."
    )

def teclado_ajuda():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("← Voltar",  callback_data="menu_inicio")],
        [InlineKeyboardButton("✖ Fechar", callback_data="obras_fechar")],
    ])

def _listar_obras():
    with sqlite3.connect(DB_PATH) as con:
        return con.execute(
            "SELECT codigo, descricao FROM obras WHERE ativa=1 ORDER BY codigo"
        ).fetchall()

def mostrar_lista_obras(obras):
    if not obras:
        return "Nenhuma obra cadastrada. Use ➕ Nova obra para começar."
    linhas = ["Qual obra?", ""]
    for codigo, desc in obras:
        desc = desc or ""
        titulo = desc.split(",")[0].replace(codigo, "").strip() if desc else "Sem descrição"
        linhas.append(f"{codigo} — {titulo}")
    return "\n".join(linhas)

def teclado_lista_obras(obras):
    botoes = []
    row = []
    for codigo, _ in obras:
        row.append(InlineKeyboardButton(codigo, callback_data=f"obra_ver:{codigo}"))
        if len(row) == 2:
            botoes.append(row)
            row = []
    if row:
        botoes.append(row)
    botoes.append([InlineKeyboardButton("➕ Nova obra",  callback_data="menu_nova_obra")])
    botoes.append([InlineKeyboardButton("← Voltar",      callback_data="menu_inicio")])
    botoes.append([InlineKeyboardButton("✖ Fechar",     callback_data="obras_fechar")])
    return InlineKeyboardMarkup(botoes)

def _pedidos_obra(ggv):
    with sqlite3.connect(DB_PATH) as con:
        return con.execute(
            "SELECT pfm_codigo, status, fornecedor, valor FROM lancamentos WHERE ggv=? ORDER BY pfm_codigo",
            (ggv,)
        ).fetchall()

def teclado_obra(codigo, pedidos=None):
    botoes = []
    if pedidos:
        botoes.append([InlineKeyboardButton("📋 Pedidos",   callback_data=f"obra_pedidos:{codigo}")])
    botoes.append([InlineKeyboardButton("📝 Listas de Compras", callback_data=f"obra_listas:{codigo}")])
    botoes.append([InlineKeyboardButton("✏️ Editar obra",   callback_data=f"obra_editar:{codigo}")])
    botoes.append([InlineKeyboardButton("◀️ Obras",         callback_data="menu_obras")])
    botoes.append([InlineKeyboardButton("✖ Fechar",         callback_data=f"obra_fechar:{codigo}")])
    return InlineKeyboardMarkup(botoes)

def mostrar_lista_pedidos(codigo, pedidos):
    _ST = {"a_pagar": "🟡", "pago": "🟢", "pendente_revisao": "🔴", "substituido": "⚫"}
    if not pedidos:
        return f"Nenhum pedido em {codigo}. Envie um orçamento para começar."
    linhas = [f"Qual pedido? · {codigo}\n"]
    for pfm_codigo, status, fornecedor, valor in pedidos:
        emoji    = _ST.get(status, "⚪")
        forn_cur = (fornecedor or "—")[:20]
        val_str  = f"R$ {_fmt_brl(valor)}" if valor else "—"
        linhas.append(f"{emoji} {pfm_codigo}  {forn_cur} · {val_str}")
    return "\n".join(linhas)

def teclado_lista_pedidos(codigo, pedidos):
    _ST = {"a_pagar": "🟡", "pago": "🟢", "pendente_revisao": "🔴", "substituido": "⚫"}
    botoes = []
    row = []
    for pfm_codigo, status, *_ in pedidos:
        emoji = _ST.get(status, "⚪")
        row.append(InlineKeyboardButton(f"{emoji} {pfm_codigo}", callback_data=f"pedido_abrir:{pfm_codigo}"))
        if len(row) == 2:
            botoes.append(row)
            row = []
    if row:
        botoes.append(row)
    botoes.append([InlineKeyboardButton("◀️ Voltar à obra", callback_data=f"obra_ver:{codigo}")])
    return InlineKeyboardMarkup(botoes)

def mostrar_lista_listas_compra(codigo, listas, filtro=None):
    """Picker "voltar numa lista pra editar" (Dennis, 2026-07-06) — cada "Gerar Lista de
    Compras" fecha a lista atual (encerrar_lista), então esta tela mostra o histórico da
    obra, mais recente primeiro, filtrável pelo Resumo."""
    if not listas:
        if filtro:
            return f"Nenhuma lista de {codigo} com \"{filtro}\" no resumo."
        return f"Nenhuma Lista de Compras gerada em {codigo} ainda."
    titulo = f"Qual lista? · {codigo}"
    if filtro:
        titulo += f" · filtro: \"{filtro}\""
    linhas = [titulo, ""]
    for lst in listas:
        data = lst["criado_em"][:10]
        resumo = lst["resumo"] or "sem resumo"
        n = lst["n_itens"]
        linhas.append(f"📅 {data} · {resumo} · {n} ite{'m' if n == 1 else 'ns'}")
    return "\n".join(linhas)

def teclado_lista_listas_compra(codigo, listas):
    botoes = []
    for lst in listas:
        data = lst["criado_em"][:10]
        resumo_curto = (lst["resumo"] or "sem resumo")[:24]
        botoes.append([InlineKeyboardButton(f"📅 {data} · {resumo_curto}", callback_data=f"lc_abrir:{lst['id']}")])
    botoes.append([InlineKeyboardButton("🔍 Buscar por nome", callback_data=f"lc_buscar:{codigo}")])
    botoes.append([InlineKeyboardButton("◀️ Voltar à obra", callback_data=f"obra_ver:{codigo}")])
    return InlineKeyboardMarkup(botoes)

def teclado_obra_campos(codigo):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Descrição",             callback_data=f"obra_campo:{codigo}:descricao")],
        [InlineKeyboardButton("Endereço de entrega",   callback_data=f"obra_campo:{codigo}:endereco_entrega")],
        [InlineKeyboardButton("Encarregado (nome)",    callback_data=f"obra_campo:{codigo}:encarregado_nome")],
        [InlineKeyboardButton("Encarregado (fone)",    callback_data=f"obra_campo:{codigo}:encarregado_fone")],
        [InlineKeyboardButton("Responsável (nome)",    callback_data=f"obra_campo:{codigo}:responsavel_nome")],
        [InlineKeyboardButton("Responsável (fone)",    callback_data=f"obra_campo:{codigo}:responsavel_fone")],
        [InlineKeyboardButton("◀️ Voltar",             callback_data=f"obra_ver:{codigo}")],
    ])

def teclado_orcamento(doc_id, tipo, ggv):
    if ggv == "nao_identificado":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📍 Definir obra",   callback_data=f"sel_ggv:{doc_id}:{tipo}:{ggv}")],
            [InlineKeyboardButton("✏️ Corrigir dados", callback_data=f"sel_edit:{doc_id}:{tipo}:{ggv}")],
            [InlineKeyboardButton("← Voltar",          callback_data=f"cancelar:{doc_id}")],
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Gerar Pedido de Compra", callback_data=f"pfm:{doc_id}:{ggv}")],
        [InlineKeyboardButton("✏️ Corrigir dados",         callback_data=f"sel_edit:{doc_id}:{tipo}:{ggv}")],
        [InlineKeyboardButton("← Voltar",                  callback_data=f"cancelar:{doc_id}")],
    ])

def teclado_candidatos_pix(doc_id_comp: int, candidatos: list):
    botoes = []
    for c in candidatos:
        botoes.append([InlineKeyboardButton(
            f"Pedido #{c['pfm_codigo']}",
            callback_data=f"pix_confirmar:{doc_id_comp}:{c['pfm_codigo']}"
        )])
    botoes.append([InlineKeyboardButton("✖ Nenhum destes — descartar arquivo",
                                        callback_data=f"pix_cancelar:{doc_id_comp}")])
    return InlineKeyboardMarkup(botoes)

def teclado_tipo_inicial(doc_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Orçamento / Fatura",    callback_data=f"sel_tipo_inicial:{doc_id}:orcamento")],
        [InlineKeyboardButton("💰 Comprovante PIX",       callback_data=f"sel_tipo_inicial:{doc_id}:comprovante_pix")],
        [InlineKeyboardButton("🧾 Nota Fiscal",           callback_data=f"sel_tipo_inicial:{doc_id}:nota_fiscal")],
        [InlineKeyboardButton("📦 Foto/arquivo de entrega", callback_data=f"sel_tipo_inicial:{doc_id}:foto_entrega")],
        [InlineKeyboardButton("📝 Lista de materiais",     callback_data=f"sel_tipo_inicial:{doc_id}:lista_materiais")],
        [InlineKeyboardButton("🏦 Extrato Mercado Pago", callback_data=f"sel_tipo_inicial:{doc_id}:extrato_mp")],
        [InlineKeyboardButton("Não é da obra",            callback_data=f"sel_tipo_inicial:{doc_id}:nao_relacionado")],
        [InlineKeyboardButton("✖ Cancelar",               callback_data=f"cancelar:{doc_id}")],
    ])

def teclado_condicao(doc_id, tipo, ggv):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 PIX à vista",                   callback_data=f"pgto:{doc_id}:{ggv}:pix_avista")],
        [InlineKeyboardButton("💰 PIX 50% entrada + 50% entrega", callback_data=f"pgto:{doc_id}:{ggv}:pix_50_50")],
        [InlineKeyboardButton("✏️ Outro (digitar)",                callback_data=f"pgto:{doc_id}:{ggv}:outro")],
        [InlineKeyboardButton("◀️ Voltar",                        callback_data=f"voltar_edit:{doc_id}:{tipo}:{ggv}")],
    ])

def teclado_escolha_endereco(destino, param, ggv, voltar_callback):
    """Teclado único de escolha de endereço — Pedido de Compra e Lista de Compras
    convergem aqui, com as mesmas opções (_opcoes_endereco) e a mesma resolução
    (_resolver_endereco em _cb_endsel). `destino` diz onde a escolha será gravada ('doc'
    ou 'lista'); `param` carrega o identificador necessário (doc_id|ggv, ou '-' quando não
    há); só o botão de voltar muda por quem chama (Dennis, 2026-07-05: "o objetivo não é
    diminuir linhas, é diminuir duplicação de comportamento")."""
    botoes = [[InlineKeyboardButton(label, callback_data=f"endsel:{destino}:{param}:{chave}")]
              for label, chave in _opcoes_endereco(ggv)]
    botoes.append([InlineKeyboardButton("← Voltar", callback_data=voltar_callback)])
    return InlineKeyboardMarkup(botoes)

def teclado_endereco(doc_id, tipo, ggv):
    return teclado_escolha_endereco("doc", f"{doc_id}|{ggv}", ggv, f"voltar_edit:{doc_id}:{tipo}:{ggv}")

def _fmt_data_curta(dt_str):
    """'2026-07-03 10:30:00' → '03/07'"""
    try:
        return f"{dt_str[8:10]}/{dt_str[5:7]}"
    except Exception:
        return dt_str[:10] if dt_str else "—"

_DATA_BR_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/\d{2,4}")

def _fmt_data_flexivel(dt_str):
    """Aceita 'D/M/AAAA...' (dia/mês sem zero à esquerda, ex: comprovante extraído pelo Claude)
    ou ISO 'AAAA-MM-DD...'. Sempre retorna 'DD/MM' com zero à esquerda, ou '—' se não reconhecer."""
    if not dt_str:
        return "—"
    m = _DATA_BR_RE.match(dt_str)
    if m:
        d, mth = m.groups()
        try:
            return f"{int(d):02d}/{int(mth):02d}"
        except ValueError:
            pass
    return _fmt_data_curta(dt_str)

def buscar_pedido(pfm_codigo: str) -> Optional[Pedido]:
    """Consulta o banco e retorna um Pedido com dados brutos e cálculos financeiros, ou None."""
    m = re.match(r"^(GGV\d{2,3})-(\d{3})(?:-R\d+)?$", pfm_codigo.upper())
    if not m:
        return None
    ggv, pfm_num = m.group(1), int(m.group(2))
    with sqlite3.connect(DB_PATH) as con:
        doc = con.execute(
            "SELECT id, ggv, dados_claude, condicao_pgto, data_entrega, desconto_rs, caminho, criado_em "
            "FROM documentos WHERE ggv=? AND pfm_numero=?",
            (ggv, pfm_num)
        ).fetchone()
        if not doc:
            return None
        doc_id, ggv_db, dados, condicao_pgto, data_entrega, desconto_rs, caminho, doc_criado = doc
        lanc = con.execute(
            "SELECT fornecedor, valor, data_prevista_entrega, vencimento_pagamento, status, criado_em, "
            "data_pagamento, doc_id_nfe, doc_id_comprovante, identificador_comprovante, "
            "obs_entrega, entregue_em, categoria "
            "FROM lancamentos WHERE pfm_codigo=?",
            (pfm_codigo,)
        ).fetchone()
        qtd_fotos = con.execute(
            "SELECT COUNT(*) FROM entrega_fotos WHERE pfm_codigo=?", (pfm_codigo,)
        ).fetchone()[0]
        qtd_parcelas = con.execute(
            "SELECT COUNT(*) FROM parcelas_pagamento WHERE pfm_codigo=?", (pfm_codigo,)
        ).fetchone()[0]
        total_pago_v = con.execute(
            "SELECT COALESCE(SUM(valor),0) FROM parcelas_pagamento WHERE pfm_codigo=?", (pfm_codigo,)
        ).fetchone()[0]

    forn_lanc = data_prev_ent = venc = status_raw = lanc_criado = data_pgto = None
    doc_id_nfe = doc_id_comp = ident_comp = obs_ent = entregue_em = categoria_lanc = None
    if lanc:
        forn_lanc, _, data_prev_ent, venc, status_raw, lanc_criado, data_pgto, doc_id_nfe, doc_id_comp, ident_comp, obs_ent, entregue_em, categoria_lanc = lanc

    try:
        status = StatusPedido(status_raw) if status_raw else StatusPedido.SEM_LANCAMENTO
    except ValueError:
        status = StatusPedido.SEM_LANCAMENTO

    subtotal_v, desconto_v, total_v = _calcular_totais(dados, desconto_rs)

    return Pedido(
        codigo             = pfm_codigo,
        doc_id             = doc_id,
        ggv                = ggv_db,
        status             = status,
        fornecedor         = forn_lanc or _campo(dados, "Fornecedor") or "—",
        cnpj               = _campo(dados, "CNPJ/CPF") or "—",
        valor_orcamento    = subtotal_v,
        desconto           = desconto_v,
        valor_negociado    = total_v,
        condicao_pagamento = condicao_pgto or "—",
        vencimento         = venc or "—",
        entrega_prevista   = data_prev_ent or data_entrega or "—",
        doc_criado_em      = doc_criado,
        lanc_criado_em     = lanc_criado,
        data_pagamento     = data_pgto,
        doc_id_nfe                = doc_id_nfe,
        doc_id_comprovante        = doc_id_comp,
        identificador_comprovante = ident_comp,
        qtd_fotos_entrega         = qtd_fotos,
        obs_entrega               = obs_ent,
        entregue_em               = entregue_em,
        categoria                 = categoria_lanc,
        qtd_parcelas              = qtd_parcelas,
        total_pago                = total_pago_v,
        caminho_orcamento         = caminho,
        observacoes               = (lambda o: None if _campo_vazio(o) else o)(_obs(dados).strip()),
    )

def preparar_visualizacao_pedido(pedido: Pedido) -> Pedido:
    """Verifica existência de arquivos em disco e constrói o histórico. Retorna o Pedido enriquecido."""
    if pedido.caminho_orcamento and not Path(pedido.caminho_orcamento).exists():
        pedido.caminho_orcamento = None

    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT caminho_pfm FROM documentos WHERE id=?", (pedido.doc_id,)).fetchone()
    caminho_pfm = row[0] if row else None
    pedido.caminho_pfm = caminho_pfm if caminho_pfm and Path(caminho_pfm).exists() else None

    if pedido.doc_id_nfe:
        with sqlite3.connect(DB_PATH) as con:
            row = con.execute("SELECT dados_claude FROM documentos WHERE id=?", (pedido.doc_id_nfe,)).fetchone()
        if row:
            numero = _campo(row[0], "Número da NF")
            pedido.nfe_numero = numero if numero != "A PREENCHER" else None
            data_raw = _campo(row[0], "Data de emissão")
            pedido.nfe_data = data_raw[:5] if data_raw != "A PREENCHER" else None

    historico = []
    if pedido.lanc_criado_em:
        historico.append((_fmt_data_curta(pedido.lanc_criado_em), "Pedido criado"))
    if pedido.data_pagamento:
        data_fmt = _fmt_data_flexivel(pedido.data_pagamento)
        pago_label = "Pago"
        if pedido.identificador_comprovante:
            cod = pedido.identificador_comprovante[:12]
            pago_label = f"Pago · {cod}"
        historico.append((data_fmt, pago_label))
    if pedido.doc_id_nfe:
        nfe_label = f"NF-e {pedido.nfe_numero}" if pedido.nfe_numero else "NF-e"
        historico.append((pedido.nfe_data or "", nfe_label))
    if pedido.obs_entrega:
        ent_data = _fmt_data_curta(pedido.entregue_em) if pedido.entregue_em else ""
        ent_label = "Entregue" if pedido.obs_entrega == "Entrega completa" else f"Entregue — {pedido.obs_entrega}"
        historico.append((ent_data, ent_label))
    pedido.historico = historico

    return pedido

# Categorias cujo fechamento fiscal é a própria fatura (CREA, ONR, prefeitura, Copel, Sanepar
# não emitem NF-e separada) — não exibir "NF-e pendente" nem exigir vínculo de NF-e
CATEGORIAS_SEM_NFE_OBRIGATORIA = {"taxa", "imposto", "servico_publico"}

def _status_pago_label(pedido: "Pedido") -> str:
    if pedido.nfe_numero:
        return f"Pago · NF-e {pedido.nfe_numero}"
    if pedido.categoria in CATEGORIAS_SEM_NFE_OBRIGATORIA:
        return "Pago"
    if not pedido.doc_id_nfe:
        return "Pago · NF-e pendente"
    return "Pago · NF-e"

def _status_a_pagar_label(pedido: "Pedido") -> str:
    if pedido.total_pago and pedido.total_pago > 0.009:
        return f"Aguardando pagamento · R$ {_fmt_brl(pedido.total_pago)} de R$ {_fmt_brl(pedido.valor_negociado)} pago"
    return "Aguardando pagamento"

def mostrar_pedido(pedido: Pedido) -> str:
    """Formata o Pedido como mensagem Telegram. Sem IO — apenas formatação."""
    _STATUS_EMOJI = {
        StatusPedido.A_PAGAR:          "🟡",
        StatusPedido.PAGO:             "🟢",
        StatusPedido.PENDENTE_REVISAO: "🔴",
        StatusPedido.SUBSTITUIDO:      "⚫",
        StatusPedido.SEM_LANCAMENTO:   "⚪",
    }
    _STATUS_SHORT = {
        StatusPedido.A_PAGAR:          _status_a_pagar_label(pedido),
        StatusPedido.PAGO:             _status_pago_label(pedido),
        StatusPedido.PENDENTE_REVISAO: "Requer atenção",
        StatusPedido.SUBSTITUIDO:      "Substituído",
        StatusPedido.SEM_LANCAMENTO:   "Sem registro financeiro",
    }
    SEP = "\n──────────────────────────────\n"

    emoji  = _STATUS_EMOJI.get(pedido.status, "")
    status = _STATUS_SHORT.get(pedido.status, str(pedido.status))
    cabecalho = f"{emoji} #{pedido.codigo} — {status}\n\n{pedido.fornecedor}"

    linhas_fin = []
    if pedido.valor_negociado > 0:
        valor_str = f"R$ {_fmt_brl(pedido.valor_negociado)}"
        if pedido.desconto > 0:
            valor_str += f"  (desc. R$ {_fmt_brl(pedido.desconto)})"
        linhas_fin.append(valor_str)
    cond = pedido.condicao_pagamento if pedido.condicao_pagamento not in ("—", None) else None
    ent  = pedido.entrega_prevista   if pedido.entrega_prevista   not in ("—", None) else None
    if cond and ent:
        linhas_fin.append(f"{cond} · entrega {ent}")
    elif cond:
        linhas_fin.append(cond)
    elif ent:
        linhas_fin.append(f"Entrega: {ent}")
    if pedido.vencimento and pedido.vencimento not in ("—", None):
        linhas_fin.append(f"Vencimento: {pedido.vencimento}")
    financeiro = "\n".join(linhas_fin) if linhas_fin else "Dados financeiros não disponíveis"

    arq = []
    if pedido.caminho_orcamento:
        arq.append("📎 Orçamento original")
    if pedido.caminho_pfm:
        arq.append("📄 Pedido de Compra")
    if pedido.doc_id_comprovante:
        arq.append("💰 Comprov. pagamento")
    if pedido.doc_id_nfe:
        nfe_label = f"🧾 NF-e {pedido.nfe_numero}" if pedido.nfe_numero else "🧾 NF-e"
        arq.append(nfe_label)
    if pedido.qtd_fotos_entrega:
        arq.append(f"📦 {_rotulo_qtd_arquivos(pedido.qtd_fotos_entrega)} da entrega")
    arquivos = "\n".join(arq) if arq else "Nenhum arquivo disponível"

    hist = []
    for data, evento in pedido.historico:
        hist.append(f"{data}  {evento}".strip())
    historico = "\n".join(hist) if hist else "—"

    blocos = [cabecalho, financeiro, arquivos, historico]
    if pedido.observacoes:
        blocos.append(f"📝 Obs: {pedido.observacoes}")
    return SEP.join(blocos)

def teclado_pedido(doc_id, pfm_codigo, doc_id_nfe=None, doc_id_comprovante=None,
                   qtd_fotos_entrega=0, obs_entrega=None, status=None, categoria=None,
                   qtd_parcelas=0):
    ggv = pfm_codigo.rsplit("-", 1)[0]
    botoes = [
        [InlineKeyboardButton("Revisar",      callback_data=f"pfm_revisar:{doc_id}:{pfm_codigo}")],
        [InlineKeyboardButton("📄 PDF",       callback_data=f"pfm_ver:{doc_id}:{pfm_codigo}")],
        [InlineKeyboardButton("📎 Orçamento", callback_data=f"pfm_orc:{doc_id}:{pfm_codigo}")],
    ]
    if doc_id_comprovante:
        botoes.append([InlineKeyboardButton("💰 Comprovante", callback_data=f"pfm_comp:{doc_id_comprovante}:{pfm_codigo}")])
    if doc_id_nfe:
        botoes.append([InlineKeyboardButton("🧾 NF-e", callback_data=f"pfm_nfe:{doc_id_nfe}:{pfm_codigo}")])
    if qtd_parcelas:
        botoes.append([InlineKeyboardButton(
            f"💰 Ver {_rotulo_qtd_arquivos(qtd_parcelas).replace('arquivo', 'parcela')}",
            callback_data=f"parcelas_ver:{pfm_codigo}"
        )])
    if obs_entrega:
        if qtd_fotos_entrega:
            botoes.append([InlineKeyboardButton(
                f"📦 Ver {_rotulo_qtd_arquivos(qtd_fotos_entrega)} da entrega",
                callback_data=f"entrega_ver_fotos:{pfm_codigo}"
            )])
        botoes.append([InlineKeyboardButton("✏️ Editar entrega", callback_data=f"entrega_editar:{pfm_codigo}")])
    else:
        botoes.append([InlineKeyboardButton("📦 Entregue", callback_data=f"pfm_entregue:{doc_id}:{pfm_codigo}")])
    botoes += [
        [InlineKeyboardButton("🗑 Excluir pedido", callback_data=f"pedido_excluir_confirmar:{pfm_codigo}")],
        [InlineKeyboardButton("◀️ Pedidos",   callback_data=f"obra_pedidos:{ggv}")],
        [InlineKeyboardButton("✖ Fechar",     callback_data=f"pfm_fechar:{doc_id}")],
    ]
    return InlineKeyboardMarkup(botoes)

_STATUS_PARCELA_LABEL = {
    "pago":                  "🟡 Pago — sem recibo",
    "aguardando_assinatura": "🟠 Aguardando assinatura",
    "assinado":              "🟢 Assinado",
}

def _texto_parcelas(pedido) -> str:
    parcelas = _listar_parcelas(pedido.codigo)
    linhas = [f"#{pedido.codigo} — {pedido.fornecedor}", ""]
    linhas.append(f"Total pago: R$ {_fmt_brl(pedido.total_pago)} de R$ {_fmt_brl(pedido.valor_negociado)}")
    if pedido.valor_negociado:
        faltam = pedido.valor_negociado - pedido.total_pago
        if faltam > 0.01:
            linhas.append(f"Faltam: R$ {_fmt_brl(faltam)}")
    linhas.append("")
    for i, (pid, valor, data, doc_id_rec, doc_id_rec_ass, status) in enumerate(parcelas, start=1):
        label = _STATUS_PARCELA_LABEL.get(status, status)
        linhas.append(f"{i}. R$ {_fmt_brl(valor)} — {data or '—'} — {label}")
    return "\n".join(linhas)

def teclado_parcelas(pfm_codigo):
    parcelas = _listar_parcelas(pfm_codigo)
    botoes = []
    for i, (pid, valor, data, doc_id_rec, doc_id_rec_ass, status) in enumerate(parcelas, start=1):
        valor_fmt = f"R$ {_fmt_brl(valor)}"
        if status == "pago":
            botoes.append([InlineKeyboardButton(
                f"📄 Gerar recibo — parcela {i} ({valor_fmt})", callback_data=f"recibo_parcela_iniciar:{pid}"
            )])
        elif status == "aguardando_assinatura":
            botoes.append([InlineKeyboardButton(
                f"👀 Ver recibo — parcela {i}", callback_data=f"pfm_recibo:{doc_id_rec}:{pfm_codigo}"
            )])
            botoes.append([InlineKeyboardButton(
                f"📎 Anexar assinado — parcela {i}", callback_data=f"recibo_assinado_iniciar:{pid}"
            )])
        elif status == "assinado":
            doc_ver = doc_id_rec_ass or doc_id_rec
            botoes.append([InlineKeyboardButton(
                f"✅ Ver recibo assinado — parcela {i}", callback_data=f"pfm_recibo:{doc_ver}:{pfm_codigo}"
            )])
    botoes.append([InlineKeyboardButton("← Voltar", callback_data=f"pedido_abrir:{pfm_codigo}")])
    return InlineKeyboardMarkup(botoes)

def buscar_pedidos_sem_entrega():
    with sqlite3.connect(DB_PATH) as con:
        return con.execute(
            "SELECT pfm_codigo, fornecedor, valor, status FROM lancamentos "
            "WHERE obs_entrega IS NULL "
            "ORDER BY pfm_codigo DESC"
        ).fetchall()

def _teclado_pedidos_entrega(pedidos):
    botoes = []
    for pfm_codigo, forn, valor, status in pedidos:
        emoji = "🟡" if status == "a_pagar" else "🟢"
        forn_curto = (forn or "")[:22]
        botoes.append([InlineKeyboardButton(
            f"{emoji} #{pfm_codigo} — {forn_curto}",
            callback_data=f"entrega_sel:{pfm_codigo}"
        )])
    botoes.append([InlineKeyboardButton("✖ Cancelar", callback_data="entrega_cancelar")])
    return InlineKeyboardMarkup(botoes)

def teclado_obs_entrega():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Entrega completa",      callback_data="entrega_obs:completa")],
        [InlineKeyboardButton("📦 Entrega parcial",       callback_data="entrega_obs:parcial")],
        [InlineKeyboardButton("⚠️ Material com avaria",  callback_data="entrega_obs:avaria")],
        [InlineKeyboardButton("🔄 Produto diferente",    callback_data="entrega_obs:diferente")],
        [InlineKeyboardButton("✏️ Outra observação",     callback_data="entrega_obs:outro")],
    ])

_MOTIVOS_RECIBO = {
    "autonomo": "Autônomo sem CNPJ",
    "informal": "Prestador informal",
    "orgao":    "Órgão/entidade sem NF-e",
}

def teclado_motivo_recibo(parcela_id, pfm_codigo):
    botoes = [
        [InlineKeyboardButton(label, callback_data=f"recibo_parcela_motivo:{parcela_id}:{chave}")]
        for chave, label in _MOTIVOS_RECIBO.items()
    ]
    botoes.append([InlineKeyboardButton("✏️ Outro motivo", callback_data=f"recibo_parcela_motivo:{parcela_id}:outro")])
    botoes.append([InlineKeyboardButton("✖ Cancelar", callback_data=f"parcelas_ver:{pfm_codigo}")])
    return InlineKeyboardMarkup(botoes)

def _salvar_entrega_db(pfm_codigo, obs):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "UPDATE lancamentos SET obs_entrega=?, "
            "entregue_em=datetime('now','localtime') WHERE pfm_codigo=?",
            (obs, pfm_codigo)
        )

def _tela_apos_entrega(pfm_codigo):
    pedido = buscar_pedido(pfm_codigo)
    if not pedido:
        return None, None
    preparar_visualizacao_pedido(pedido)
    return (
        mostrar_pedido(pedido),
        teclado_pedido(pedido.doc_id, pfm_codigo, pedido.doc_id_nfe,
                       pedido.doc_id_comprovante, pedido.qtd_fotos_entrega, pedido.obs_entrega,
                       pedido.status, pedido.categoria, pedido.qtd_parcelas)
    )

def _adicionar_foto_entrega(pfm_codigo, doc_id_foto, legenda):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO entrega_fotos (pfm_codigo, doc_id, legenda) VALUES (?,?,?)",
            (pfm_codigo, doc_id_foto, legenda)
        )
        qtd = con.execute(
            "SELECT COUNT(*) FROM entrega_fotos WHERE pfm_codigo=?", (pfm_codigo,)
        ).fetchone()[0]
        row = con.execute("SELECT caminho FROM documentos WHERE id=?", (doc_id_foto,)).fetchone()
    caminho_original = row[0] if row else None
    _arquivar_documento(pfm_codigo, f"foto{qtd:02d}", caminho_original, None, _pasta_entrega)

def _listar_fotos_entrega(pfm_codigo):
    with sqlite3.connect(DB_PATH) as con:
        return con.execute(
            "SELECT ef.id, ef.doc_id, ef.legenda, d.caminho FROM entrega_fotos ef "
            "JOIN documentos d ON d.id = ef.doc_id WHERE ef.pfm_codigo=? ORDER BY ef.id",
            (pfm_codigo,)
        ).fetchall()

def _icone_arquivo_entrega(caminho):
    if caminho and Path(caminho).suffix.lower() == ".pdf":
        return "📄"
    return "📷"

def _apagar_foto_entrega(foto_id):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM entrega_fotos WHERE id=?", (foto_id,))

def _atualizar_obs_entrega(pfm_codigo, obs):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "UPDATE lancamentos SET obs_entrega=? WHERE pfm_codigo=?",
            (obs, pfm_codigo)
        )

def _apagar_entrega_db(pfm_codigo):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "UPDATE lancamentos SET obs_entrega=NULL, entregue_em=NULL "
            "WHERE pfm_codigo=?", (pfm_codigo,)
        )
        con.execute("DELETE FROM entrega_fotos WHERE pfm_codigo=?", (pfm_codigo,))

def _buscar_estado_entrega(pfm_codigo):
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT fornecedor, obs_entrega FROM lancamentos WHERE pfm_codigo=?",
            (pfm_codigo,)
        ).fetchone()
        qtd_fotos = con.execute(
            "SELECT COUNT(*) FROM entrega_fotos WHERE pfm_codigo=?", (pfm_codigo,)
        ).fetchone()[0]
    forn, obs = row if row else (None, None)
    return forn, obs, qtd_fotos

def _rotulo_qtd_arquivos(qtd):
    if qtd == 0:
        return "nenhuma"
    if qtd == 1:
        return "1 arquivo"
    return f"{qtd} arquivos"

def _texto_gerir_entrega(pfm_codigo, forn, obs_entrega, qtd_fotos):
    return (
        f"#{pfm_codigo} — {forn or pfm_codigo}\n\n"
        f"Entrega registrada\n"
        f"Observação: {obs_entrega or '—'}\n"
        f"Arquivos: {_rotulo_qtd_arquivos(qtd_fotos)}"
    )

def _teclado_gerir_entrega(pfm_codigo, qtd_fotos):
    botoes = [
        [InlineKeyboardButton("✏️ Mudar observação", callback_data=f"entrega_mudar_obs:{pfm_codigo}")],
    ]
    if qtd_fotos:
        botoes.append([InlineKeyboardButton(f"👀 Ver {_rotulo_qtd_arquivos(qtd_fotos)}", callback_data=f"entrega_ver_fotos:{pfm_codigo}")])
    botoes.append([InlineKeyboardButton("📎 Adicionar foto ou arquivo", callback_data=f"entrega_trocar_foto:{pfm_codigo}")])
    if qtd_fotos:
        botoes.append([InlineKeyboardButton("🗑 Remover arquivo", callback_data=f"entrega_remover_foto:{pfm_codigo}")])
    botoes += [
        [InlineKeyboardButton("❌ Apagar entrega", callback_data=f"entrega_apagar:{pfm_codigo}")],
        [InlineKeyboardButton("← Voltar",          callback_data=f"entrega_voltar:{pfm_codigo}")],
    ]
    return InlineKeyboardMarkup(botoes)

def _teclado_mudar_obs(pfm_codigo):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Entrega completa",      callback_data="entrega_editobs:completa")],
        [InlineKeyboardButton("📦 Entrega parcial",       callback_data="entrega_editobs:parcial")],
        [InlineKeyboardButton("⚠️ Material com avaria",  callback_data="entrega_editobs:avaria")],
        [InlineKeyboardButton("🔄 Produto diferente",    callback_data="entrega_editobs:diferente")],
        [InlineKeyboardButton("✏️ Outra observação",     callback_data="entrega_editobs:outro")],
        [InlineKeyboardButton("← Voltar",                callback_data=f"entrega_editar:{pfm_codigo}")],
    ])

def _texto_obs_entrega(pfm_codigo, forn):
    return f"#{pfm_codigo} — {forn or pfm_codigo}\n\nComo foi a entrega?"

def _mostrar_pedidos_entrega(pedidos):
    if not pedidos:
        return "Nenhum pedido sem entrega registrada."
    linhas = ["Qual pedido chegou?", ""]
    for pfm_codigo, forn, valor, status in pedidos:
        emoji = "🟡" if status == "a_pagar" else "🟢"
        v = f"R$ {_fmt_brl(float(valor))}" if valor else ""
        linhas.append(f"{emoji} #{pfm_codigo} · {forn or '—'}" + (f" · {v}" if v else ""))
    return "\n".join(linhas)

def _teclado_obs_com_cancelar(com_foto=False):
    linhas = list(teclado_obs_entrega().inline_keyboard)
    if not com_foto:
        linhas.append([InlineKeyboardButton("📎 Foto / Documento", callback_data="entrega_foto_primeiro")])
    linhas.append([InlineKeyboardButton("✖ Cancelar", callback_data="entrega_cancelar")])
    return InlineKeyboardMarkup(linhas)

def _tela_categoria(cat, ramo):
    if cat:
        linha_ramo = f"\n{ramo}" if ramo and ramo != "A PREENCHER" else ""
        return f"Como classificar este pedido?\n\n{cat.label()}{linha_ramo}"
    return "Como classificar este pedido?"

def _teclado_selecao_categorias(doc_id, ggv, acao="cat_sel"):
    """Grade única de categorias, usada em dois momentos com ações diferentes:
    `cat_sel` (geração — escolher categoria e gerar o pedido) e `cat_upd` (pedido já
    existente — só reclassificar o lançamento, via Corrigir dados)."""
    cats = list(CategoriaLancamento)
    botoes = []
    for i in range(0, len(cats), 2):
        linha = [
            InlineKeyboardButton(c.label(), callback_data=f"{acao}:{doc_id}:{ggv}:{c.value}")
            for c in cats[i:i+2]
        ]
        botoes.append(linha)
    return InlineKeyboardMarkup(botoes)

def _teclado_categoria(doc_id, ggv, cat):
    if cat:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirmar",   callback_data=f"cat_confirmar:{doc_id}:{ggv}:{cat.value}")],
            [InlineKeyboardButton("Escolher outra", callback_data=f"cat_corrigir:{doc_id}:{ggv}")],
        ])
    return _teclado_selecao_categorias(doc_id, ggv)

async def _executar_gerar_pfm(query, ctx, doc_id, ggv, categoria):
    await query.edit_message_text("Gerando Pedido de Compra...")
    caminho, codigo, fornecedor, valor_v, lanc_status, ja_existia = gerar_pfm(doc_id, categoria)
    html      = _gerar_html_pc(doc_id)
    pdf_bytes = await _html_para_pdf(html)
    caminho.with_suffix(".pdf").write_bytes(pdf_bytes)
    await ctx.bot.send_document(
        chat_id=DONO_ID,
        document=pdf_bytes,
        filename=f"{codigo}.pdf",
        caption=f"Pedido #{codigo}"
    )
    if ja_existia:
        lanc_msg = f"Pedido #{codigo} já tinha registro financeiro."
    elif lanc_status == "pendente_revisao":
        lanc_msg = (
            f"🔴 Pedido #{codigo} requer atenção.\n"
            f"Fornecedor ou valor ausente — verifique antes de pagar."
        )
    else:
        cat_linha = f"\n{categoria.label()}" if categoria else ""
        lanc_msg = (
            f"🟡 {codigo} — aguardando pagamento\n\n"
            f"{fornecedor} — R$ {_fmt_brl(valor_v)}{cat_linha}"
        )
    await ctx.bot.send_message(chat_id=DONO_ID, text=lanc_msg)


async def _executar_revisao_pfm(query, ctx, doc_id, pfm_codigo_base):
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT rev_numero FROM documentos WHERE id=?", (doc_id,)).fetchone()
        rev_num = (row[0] or 0) + 1
        con.execute("UPDATE documentos SET rev_numero=? WHERE id=?", (rev_num, doc_id))
    rev_codigo = f"{pfm_codigo_base}-R{rev_num:02d}"
    await query.edit_message_text(f"Gerando revisão {rev_codigo}...")
    caminho_rev, *_ = gerar_pfm(doc_id, pfm_codigo_override=rev_codigo)
    nome_principal    = caminho_rev.name.replace(rev_codigo, pfm_codigo_base, 1)
    caminho_principal = caminho_rev.parent / nome_principal
    atualizar(doc_id, caminho_pfm=str(caminho_principal))
    html      = _gerar_html_pc(doc_id)
    pdf_bytes = await _html_para_pdf(html)
    caminho_rev.with_suffix(".pdf").write_bytes(pdf_bytes)
    caminho_principal.with_suffix(".pdf").write_bytes(pdf_bytes)
    await ctx.bot.send_document(
        chat_id=DONO_ID,
        document=pdf_bytes,
        filename=f"{rev_codigo}.pdf",
        caption=f"📄 {rev_codigo}"
    )
    ctx.user_data.pop("modo_revisao", None)
    await ctx.bot.send_message(
        chat_id=DONO_ID,
        text=f"✅ {rev_codigo} gerado. Lançamento financeiro mantido.",
        reply_markup=teclado_pedido(doc_id, pfm_codigo_base)
    )

async def _gerar_recibo(ctx, parcela_id: int, motivo: str):
    """Gera o recibo em PDF de uma parcela paga, arquiva e marca aguardando assinatura."""
    parcela = _buscar_parcela(parcela_id)
    if not parcela:
        await ctx.bot.send_message(chat_id=DONO_ID, text="Parcela não encontrada.")
        return
    _, pfm_codigo, valor_parcela, data_parcela, *_ = parcela
    pedido = buscar_pedido(pfm_codigo)
    if not pedido:
        await ctx.bot.send_message(chat_id=DONO_ID, text="Pedido não encontrado.")
        return
    html      = _gerar_html_recibo(parcela_id)
    pdf_bytes = await _html_para_pdf(html, formato="A5", paisagem=True)

    ggv        = pfm_codigo.split("-")[0]
    nome_base  = _nome_base_pfm(pfm_codigo, pedido.fornecedor, f"recibo-parcela{parcela_id}")
    destino    = _pasta_entrega(ggv) / f"{nome_base}.pdf"
    destino.write_bytes(pdf_bytes)

    hash_recibo = hashlib.sha256(pdf_bytes).hexdigest()
    doc_id_recibo = registrar(destino.name, destino, hash_recibo, "recibo", ggv, f"Motivo: {motivo}")

    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "UPDATE parcelas_pagamento SET doc_id_recibo=?, status='aguardando_assinatura' WHERE id=?",
            (doc_id_recibo, parcela_id)
        )
        con.execute(
            "UPDATE fornecedores SET emite_nf=0 WHERE cnpj=? OR cpf=?",
            (pedido.cnpj, pedido.cnpj)
        )

    await ctx.bot.send_document(
        chat_id=DONO_ID,
        document=pdf_bytes,
        filename=f"{nome_base}.pdf",
        caption=(f"📄 Recibo — Pedido #{pfm_codigo} — R$ {_fmt_brl(valor_parcela)}\n\n"
                 "Envie para o fornecedor assinar. Quando voltar assinado, use "
                 "\"📎 Anexar recibo assinado\" na tela de parcelas.")
    )
    await ctx.bot.send_message(
        chat_id=DONO_ID,
        text=f"🟡 Recibo gerado — aguardando assinatura (#{pfm_codigo}, R$ {_fmt_brl(valor_parcela)}).",
        reply_markup=teclado_parcelas(pfm_codigo)
    )

async def _sincronizar_receita_fornecedores(ctx: ContextTypes.DEFAULT_TYPE):
    """Job periódico: resincroniza TODOS os fornecedores com CNPJ contra a Receita — não só os
    pendentes. Três políticas diferentes por tipo de campo:
      - razão social, cidade, UF, CNAE: sempre reflete a Receita mais recente (dado oficial de
        cadastro, baixo risco de estar errado — pode sobrescrever)
      - ramo: prioriza o texto natural já salvo (extraído de documento real); CNAE da Receita só
        entra como fallback quando ainda não há nada
      - e-mail, telefone: só preenche se ainda estiver vazio — a Receita tem risco real de estar
        desatualizada nesses dois, nunca sobrescreve o que já existe
    Avisa só quando algo muda de verdade."""
    with sqlite3.connect(DB_PATH) as con:
        fornecedores = con.execute(
            "SELECT id, cnpj, razao_social, cidade, uf, ramo, cnae, email, whatsapp "
            "FROM fornecedores WHERE cnpj IS NOT NULL AND cnpj != ''"
        ).fetchall()
    if not fornecedores:
        return

    atualizados = 0
    for forn_id, cnpj, razao_at, cidade_at, uf_at, ramo_at, cnae_at, email_at, whats_at in fornecedores:
        cnpj_digits = re.sub(r"\D", "", cnpj or "")
        if len(cnpj_digits) != 14:
            continue
        receita = _consultar_receita(cnpj_digits)
        if not receita:
            continue

        novos = (
            receita.get("razao_social") or razao_at,     # sempre atualiza
            receita.get("cidade") or cidade_at,            # sempre atualiza
            receita.get("uf") or uf_at,                     # sempre atualiza
            ramo_at or receita.get("ramo"),                 # só preenche se vazio
            receita.get("cnae") or cnae_at,                 # sempre atualiza
            email_at or receita.get("email"),               # só preenche se vazio
            whats_at or receita.get("telefone"),            # só preenche se vazio
        )
        if novos == (razao_at, cidade_at, uf_at, ramo_at, cnae_at, email_at, whats_at):
            continue

        with sqlite3.connect(DB_PATH) as con:
            con.execute(
                "UPDATE fornecedores SET razao_social=?, cidade=?, uf=?, ramo=?, cnae=?, "
                "email=?, whatsapp=?, receita_pendente=0 WHERE id=?",
                (*novos, forn_id)
            )
        atualizados += 1

    if atualizados:
        await ctx.bot.send_message(
            chat_id=DONO_ID,
            text=f"📋 Receita sincronizada — {atualizados} fornecedor(es) com dado novo ou atualizado."
        )


# ── Handlers ───────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DONO_ID:
        return
    if TEST_MODE:
        await update.message.reply_text(
            "🧪 MODO TESTE ATIVO\n"
            "Banco: data/laura_test.db\n"
            "Uploads: data/test_uploads\n"
            "Pedidos: data/test_pfms"
        )
    else:
        await update.message.reply_text("Estou online.")

async def ajuda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DONO_ID:
        return
    await update.message.reply_text(
        mostrar_ajuda(),
        reply_markup=teclado_ajuda(),
        parse_mode="HTML"
    )

async def comando_desconhecido(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DONO_ID:
        return
    await update.message.reply_text(
        mostrar_boas_vindas(),
        reply_markup=teclado_boas_vindas()
    )

async def obras_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DONO_ID:
        return
    obras = _listar_obras()
    await update.message.reply_text(
        mostrar_lista_obras(obras),
        reply_markup=teclado_lista_obras(obras)
    )

async def entrega_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DONO_ID:
        return
    pedidos = buscar_pedidos_sem_entrega()
    if not pedidos:
        await update.message.reply_text("Nenhum pedido sem entrega registrada.")
        return
    ctx.user_data["entrega_doc_id_foto"] = None
    if len(pedidos) == 1:
        pfm_codigo, forn, _, _ = pedidos[0]
        ctx.user_data["entrega_pfm_codigo"] = pfm_codigo
        await update.message.reply_text(
            _texto_obs_entrega(pfm_codigo, forn),
            reply_markup=_teclado_obs_com_cancelar()
        )
    else:
        await update.message.reply_text(
            _mostrar_pedidos_entrega(pedidos),
            reply_markup=_teclado_pedidos_entrega(pedidos)
        )

async def nova_obra(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DONO_ID:
        return
    ctx.user_data["aguardando"] = "nova_obra_codigo"
    await update.message.reply_text("Código da nova obra (ex: GGV04):")

# ── Lista de Compras (Fiada 1 — momento "antes da compra") ─────────────────
# docs/POLITICA_COMPRAS.md, docs/CASOS_DE_USO_COMPRAS.md, docs/MODELO_DOMINIO_COMPRAS.md
#
# Camada 1 (interpretação) — /lista aceita texto, foto ou PDF; a IA interpreta a lista
# inteira de uma vez, mesma lógica de segurança do orçamento (interpreta → apresenta →
# confirma → só então grava). Camadas seguintes (SINAPI, referência de preço, tela de
# conferência editável, gravação) entram em cima disso.

PROMPT_INTERPRETAR_LISTA = """
Você recebeu uma lista de materiais ou peças que o usuário está montando para comprar —
pode ser texto corrido, anotação à mão, lista impressa, foto de uma tabela ou PDF. Não tem
preço nem fornecedor — não classifique nem tente identificar isso como orçamento.

PROCEDIMENTO — siga esta ordem antes de responder:
1. Verifique se o conteúdo tem estrutura de tabela (colunas separadas de descrição, unidade,
   quantidade, código). Documentos de obra costumam ter essa estrutura mesmo quando a foto ou
   o texto colado parece bagunçado.
2. Se houver tabela, identifique cada linha (item) individualmente antes de interpretar
   qualquer conteúdo.
3. Para cada linha, identifique a coluna de descrição, a coluna de unidade e a coluna de
   quantidade SEPARADAMENTE — nunca misture uma com a outra.
4. Só depois de separar as colunas, interprete semanticamente o texto de cada campo (ex:
   normalizar "sc" como unidade, identificar o fabricante dentro da descrição).
5. Depois de identificar todos os itens, olhe a lista COMO UM TODO antes de finalizar a
   interpretação de cada um. Os itens juntos costumam indicar a etapa da obra (ex: cimento +
   argamassa + rejunte + porcelanato + revestimento cerâmico = revestimentos e acabamentos;
   tubo + conexão + registro + joelho + luva = instalação hidráulica; eletroduto + cabo +
   caixa + disjuntor = instalação elétrica). Um engenheiro lendo essa lista não interpreta
   cada item isolado — ele entende primeiro o contexto da compra e só depois cada material
   dentro desse contexto. Use esse contexto coletivo pra reduzir ambiguidade (ex: numa lista
   de revestimentos, "argamassa" é mais provavelmente argamassa colante do que reboco; um
   "rejunte" nessa mesma lista é rejunte cimentício de junta).

REGRAS — nunca violar, mesmo sob a tentação de "completar" um campo:
- Quantidade e unidade vêm da coluna correspondente da tabela. Se não for possível ler com
  confiança, use `null` — NUNCA invente ou assuma "1" como padrão.
- Fabricante é a marca/fabricante do produto (ex: Cauê, Belka, Lef, Quartzolit, Tigre,
  Votorantim) — sempre um campo separado da descrição e da unidade, nunca dentro de um ou
  de outro.
- Código de referência do fabricante (ex: "72707/72745", "RX32000A") é um identificador —
  copie exatamente os caracteres/dígitos como aparecem. NUNCA reordene, corrija ou "arrume"
  um código, mesmo que pareça estranho. Se a leitura não for 100% clara, use `null` e registre
  em observações que a leitura é incerta (ex: "código de difícil leitura, conferir").
- Prioridade quando houver qualquer dúvida: (1) o valor escrito na coluna da tabela, (2) o
  texto exatamente como foi lido, (3) sua interpretação. Nunca "melhore" ou complete um valor
  objetivo com base no que pareceria mais provável.
- Nunca invente ou escreva preço, mesmo que consiga estimar um valor de mercado — preço não
  existe nesse tipo de documento.
- Depois de ler a unidade de uma linha, verifique se ela faz sentido técnico pro produto
  daquela linha (ex: cimento/argamassa/rejunte/cal são vendidos por peso — SC, KG — não por
  metro linear; porcelanato/revestimento/forro são vendidos por área — M2 — não por metro
  linear). Se a unidade lida não fizer sentido técnico pro produto, releia a coluna da tabela
  especificamente para essa linha antes de decidir — é mais provável ter confundido com a
  linha vizinha (erro de alinhamento de coluna) do que a obra realmente comprar rejunte por
  metro. Só use `null` se a releitura confirmar que a coluna genuinamente não dá pra ler com
  confiança, não porque o valor pareceu estranho à primeira vista.

ANTES DE CONCLUIR QUE UMA INFORMAÇÃO NÃO EXISTE, tente compreender tecnicamente o produto e
separe duas coisas diferentes:
- características PERMANENTES do produto (embalagem/tamanho de uma unidade de venda,
  fabricante, dimensões) — normalmente estão dentro do próprio nome/descrição do produto
  (ex: "Rejunte Cinza Ártico 5kg" → a embalagem de uma unidade é 5 kg, isso está na descrição
  mesmo sem tabela legível);
- características DA COMPRA (quantidade de unidades pedidas, unidade comercial de compra,
  preço) — essas só vêm da tabela/documento, nunca invente.

Preencha "embalagem" sempre que a descrição indicar claramente o tamanho de UMA unidade de
venda (ex: "20 KG", "5 KG", "18 L"), mesmo que "quantidade"/"unidade" fiquem `null` por falta
de leitura confiável na tabela — "5kg" no nome do produto quase sempre é o tamanho da
embalagem, não a quantidade comprada. Nunca confunda as duas coisas: identificar a embalagem
não significa que você pode inferir a quantidade pedida a partir dela.

Preencha também "termo_busca_sinapi": uma descrição curta, genérica e técnica do produto (o
que ele É e para que SERVE — categoria, função, aplicação, material), sem marca e sem nome
comercial/código do fabricante, usada só pra buscar a referência SINAPI depois. Nomes
comerciais não descrevem a função técnica do produto (ex: "Argamassa EXT 10 EM 1" é só o nome
comercial da Hipermassa — numa lista de revestimentos, contendo porcelanato/revestimento
cerâmico, o termo técnico correto é algo como "argamassa colante para porcelanato área
externa", não "argamassa ext 10 em 1"). Use o contexto da lista inteira (passo 5) pra inferir
isso com mais segurança. Se a própria descrição já for genérica o suficiente (ex: "Areia média
lavada"), repita algo equivalente sem marca.

Preencha também "descricao_generica" (true/false): marque true quando a descrição, do jeito
que o usuário escreveu, não tem informação técnica suficiente pra pedir uma cotação séria —
tipicamente uma ou duas palavras, sem marca, sem dimensão, sem tipo/variante, sem aplicação,
sem embalagem (ex: "Areia", "Brita", "Tijolos", "Cimento", "Cal" são genéricas; "Areia média
lavada", "Cimento CP II 50kg Cauê", "Tijolo cerâmico 6 furos 9x19x19" não são). Use julgamento
técnico, não uma regra mecânica de contagem de palavras — o teste é "um comprador conseguiria
pedir orçamento com isso, ou precisaria perguntar mais alguma coisa?". A Laura vai tentar
enriquecer essas descrições depois com histórico próprio ou SINAPI, mas isso só deve acontecer
quando a descrição original genuinamente carece de especificação.

Responda APENAS com um array JSON, sem markdown, sem texto antes ou depois, neste formato:
[
  {"numero": 1, "descricao": "Cimento CP II 50 kg", "fabricante": "Cauê", "codigo": null,
   "unidade": "SC", "quantidade": 250.0, "embalagem": "50 KG",
   "termo_busca_sinapi": "cimento portland composto", "descricao_generica": false,
   "observacoes": null}
]

Campos: "numero" (inteiro — número do item na lista original, ou null se não houver
numeração), "descricao" (string, obrigatório), "fabricante" (string ou null), "codigo"
(string ou null), "unidade" (string ou null), "quantidade" (número ou null), "embalagem"
(string ou null — tamanho de UMA unidade de venda, quando identificável na descrição),
"termo_busca_sinapi" (string ou null — descrição técnica genérica pra busca SINAPI),
"descricao_generica" (true/false — a descrição do jeito que veio é pobre demais pra
cotação?), "observacoes" (string ou null).
"""

async def _interpretar_lista_texto(texto):
    resposta = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": f"Lista enviada pelo usuário:\n\n{texto}"},
                {"type": "text", "text": PROMPT_INTERPRETAR_LISTA},
            ]
        }]
    )
    itens = _itens_lista_materiais(resposta.content[0].text)
    itens = await _adicionar_correspondencia_sinapi(itens)
    itens = _adicionar_referencia_laura(itens)
    return _adicionar_sugestao_descricao(itens)

async def _interpretar_lista_arquivo(conteudo_bytes, mime_inf):
    tipo_conteudo = "document" if mime_inf == "application/pdf" else "image"
    dados_b64 = base64.standard_b64encode(conteudo_bytes).decode()
    resposta = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {"type": tipo_conteudo, "source": {"type": "base64", "media_type": mime_inf, "data": dados_b64}},
                {"type": "text", "text": PROMPT_INTERPRETAR_LISTA},
            ]
        }]
    )
    itens = _itens_lista_materiais(resposta.content[0].text)
    itens = await _adicionar_correspondencia_sinapi(itens)
    itens = _adicionar_referencia_laura(itens)
    return _adicionar_sugestao_descricao(itens)

# ── Camada 2 — Candidatos SINAPI (busca FTS5 + Claude decide) ──────────────
# Convergência deliberada: a correspondência acontece dentro das duas funções de
# interpretação acima, não numa etapa separada que cada chamador precisaria lembrar de
# invocar — mesmo princípio "entradas diferentes, processo único" da Camada 1.

_SINAPI_PALAVRA_RE = re.compile(r"[A-Za-zÀ-ÿ0-9]+")

def _mesma_unidade(a, b):
    """Compara duas unidades ignorando maiúsculas/minúsculas e espaço nas pontas — 'm2' e
    'M2' são a mesma unidade (metro quadrado), não unidades diferentes. Evitar esse tipo de
    falso "unidade diferente" é o que motivou esta função (Dennis, 2026-07-04: "M2 e m2 são
    unidades iguais metro quadrado")."""
    return (a or "").strip().upper() == (b or "").strip().upper()

def _candidatos_sinapi(descricao, limite=6):
    """Busca candidatos SINAPI por palavra-chave (FTS5) para a descrição de um item.
    Recall alto, não precisão — a decisão final é do Claude na segunda etapa. Nunca
    levanta exceção: lista vazia em qualquer caso de falha (defensivo, mesmo espírito do
    resto do pipeline de interpretação)."""
    palavras = [p for p in _SINAPI_PALAVRA_RE.findall(descricao.lower()) if len(p) >= 3][:8]
    if not palavras:
        return []
    query_fts = " OR ".join(palavras)
    try:
        with sqlite3.connect(DB_PATH) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("""
                SELECT s.codigo, s.descricao, s.unidade, s.preco_pr, s.mes_referencia
                FROM insumos_sinapi_fts f
                JOIN insumos_sinapi s ON s.codigo = f.rowid
                WHERE insumos_sinapi_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query_fts, limite)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []

PROMPT_ESCOLHER_SINAPI = """
Para cada item da lista abaixo, você recebeu candidatos de insumos SINAPI (base de preços
oficial da construção civil) encontrados por busca de palavra-chave — a busca é só um filtro
inicial, pode trazer candidato errado ou nenhum candidato certo.

Antes de decidir qualquer item, olhe a LISTA INTEIRA e identifique que etapa de obra ela
representa como conjunto (ex: cimento + argamassa + rejunte + porcelanato + revestimento
cerâmico = revestimentos e acabamentos; tubo + conexão + registro + joelho + luva = instalação
hidráulica; eletroduto + cabo + caixa + disjuntor = instalação elétrica). Um engenheiro lendo
essa lista não decide item por item isolado — ele entende o contexto da compra primeiro. Use
esse contexto pra reduzir ambiguidade em cada item (ex: numa lista de revestimentos, uma
"argamassa" é mais provavelmente argamassa colante pra assentamento do que reboco).

Cada item pode trazer "termo_tecnico" (a função/categoria do produto já inferida na etapa
anterior, sem marca nem nome comercial) — quando presente, é o sinal mais confiável do que o
produto realmente É e PARA QUE SERVE; o nome comercial ("descricao") pode ser só o nome de
venda do fabricante (ex: "Argamassa EXT 10 EM 1" da Hipermassa é argamassa colante — o nome
comercial não descreve isso). Nomes comerciais e códigos de produto NUNCA aparecem no SINAPI
(base genérica, sem marca) — não busque semelhança textual com eles, busque semelhança
funcional com o que o produto faz.

Antes de decidir, entenda o produto de verdade — não compare só a descrição como texto.
Considere internamente: o que é este produto, qual sua categoria, é material ou ferramenta,
qual a aplicação (piso, parede, teto, estrutura...), qual o material predominante, quais as
dimensões, quais características técnicas aparecem na descrição. Você não precisa escrever
essas respostas — use-as só pra decidir melhor.

Escolha, para cada item, o candidato que representa exatamente o MESMO produto (mesma
categoria, aplicação e especificação técnica relevante). Preste atenção especial a categorias
adjacentes mas tecnicamente diferentes (ex: porcelanato não é a mesma coisa que revestimento
cerâmico comum, mesmo aparecendo juntos numa busca por palavra-chave) — trate isso como
discordância de categoria, não como "descrição parecida o suficiente".

Classifique seu grau de confiança em cada correspondência:
- "alta": categoria, aplicação e especificação técnica claramente compatíveis
- "media": mesma categoria, mas alguma característica não confirmada com certeza
- "baixa": categoria plausível mas com dúvida real — errar com confiança é pior que admitir
  dúvida; prefira "baixa" a forçar "alta"/"media" quando não tiver certeza
- "nenhuma": nenhum candidato representa o mesmo produto (nesse caso, sinapi_codigo é `null`)

A Lista de Compras mantém sempre a unidade comercial do item (como se compra e negocia —
ex: SC, LT, CX) — isso nunca muda e nunca é convertido para a unidade do SINAPI.

Se a unidade comercial do item já for IGUAL à unidade do candidato escolhido, não existe
conversão a fazer: deixe preco_equivalente_unidade_comercial como `null` (o preço do SINAPI
já está direto na unidade comercial, sem precisar de equivalência).

Se a unidade comercial for DIFERENTE da unidade do candidato (ex: item vendido em SC/saco,
SINAPI referencia por KG), use o campo "embalagem" do item, se vier preenchido — já é o
tamanho de UMA unidade de venda, extraído na etapa anterior (ex: embalagem "50 KG" pra um item
vendido em SC significa que 1 SC pesa 50 kg). Se "embalagem" vier `null`, tente determinar o
mesmo dado a partir da própria descrição do item, só quando tiver certeza. Calcule o INVERSO:
o preço de referência do SINAPI convertido para a unidade comercial do item (preço por SC, não
quantidade em KG). Exemplo: SINAPI = R$ 0,80/KG, embalagem = 50 kg/SC →
preço_equivalente_unidade_comercial = 40.00 (R$ por SC).

O fator de conversão vem SEMPRE do tamanho de UMA embalagem/unidade de venda (quanto pesa ou
mede uma única SC, LT, CX...), nunca da quantidade pedida no item — quantidade pedida é
irrelevante pra essa conta. Só calcule quando tiver certeza do tamanho da embalagem — senão
`null`.

Responda APENAS com um array JSON, sem markdown, sem texto antes ou depois, neste formato:
[
  {"numero": 1, "sinapi_codigo": 12345, "confianca": "alta",
   "preco_equivalente_unidade_comercial": 40.00},
  {"numero": 2, "sinapi_codigo": null, "confianca": "nenhuma",
   "preco_equivalente_unidade_comercial": null}
]
"""

async def _adicionar_correspondencia_sinapi(itens):
    """Segunda etapa da Camada 2: para cada item já interpretado, busca candidatos SINAPI
    e faz uma única chamada ao Claude decidindo a correspondência de toda a lista de uma
    vez (não uma chamada por item). Anota os itens no lugar com os 5 campos de snapshot
    SINAPI (sinapi_codigo/descricao_referencia/unidade_referencia/preco_referencia/
    mes_referencia) — mesmos nomes das colunas de lista_compra_itens, prontos pra Camada 6
    gravar sem tradução."""
    candidatos_por_numero = {}
    itens_para_claude = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        # Busca pelo termo técnico (categoria/função/aplicação, sem marca nem nome comercial)
        # quando a Camada 1 conseguiu inferir um — nome comercial (ex: "Argamassa EXT 10 EM 1")
        # raramente contém vocabulário que bate com a base SINAPI. Cai pra descrição crua
        # quando não há termo técnico inferido.
        termo_busca = item.get("termo_busca_sinapi") or item["descricao"]
        candidatos = _candidatos_sinapi(termo_busca)
        candidatos_por_numero[item.get("numero")] = candidatos
        if candidatos:
            itens_para_claude.append({
                "numero": item.get("numero"),
                "descricao": item["descricao"],
                "termo_tecnico": item.get("termo_busca_sinapi"),
                "embalagem": item.get("embalagem"),
                "unidade_comercial": item.get("unidade"),
                "candidatos_sinapi": [
                    {"codigo": c["codigo"], "descricao": c["descricao"], "unidade": c["unidade"],
                     "preco": c["preco_pr"]}
                    for c in candidatos
                ],
            })

    escolhas = {}
    if itens_para_claude:
        try:
            resposta = claude.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": json.dumps({"itens": itens_para_claude}, ensure_ascii=False)},
                        {"type": "text", "text": PROMPT_ESCOLHER_SINAPI},
                    ]
                }]
            )
            texto_resposta = resposta.content[0].text.strip()
            # Extrai só o array JSON mesmo se vier cercado por markdown ou seguido de
            # texto de justificativa — Claude às vezes explica a decisão após o array,
            # apesar da instrução de responder só com JSON.
            m = re.search(r"\[.*\]", texto_resposta, re.DOTALL)
            if m:
                texto_resposta = m.group(0)
            for escolha in json.loads(texto_resposta):
                escolhas[escolha.get("numero")] = escolha
        except (json.JSONDecodeError, ValueError, TypeError, anthropic.APIError):
            pass  # sem escolhas — todos os itens ficam sem correspondência SINAPI

    for item in itens:
        if not isinstance(item, dict):
            continue
        escolha = escolhas.get(item.get("numero")) or {}
        codigo_escolhido = escolha.get("sinapi_codigo")
        candidato = None
        if codigo_escolhido is not None:
            candidato = next(
                (c for c in candidatos_por_numero.get(item.get("numero"), []) if c["codigo"] == codigo_escolhido),
                None
            )
        item["sinapi_codigo"] = candidato["codigo"] if candidato else None
        item["sinapi_descricao_referencia"] = candidato["descricao"] if candidato else None
        item["sinapi_unidade_referencia"] = candidato["unidade"] if candidato else None
        item["sinapi_preco_referencia"] = candidato["preco_pr"] if candidato else None
        item["sinapi_mes_referencia"] = candidato["mes_referencia"] if candidato else None
        # Confiança e preço equivalente: raciocínio da própria etapa de interpretação
        # (Camada 2), não um atributo persistido — Dennis, 2026-07-04: "não quero criar uma
        # estrutura permanente antes de comprovar seu valor". A unidade comercial do item
        # nunca é convertida; é o preço do SINAPI que é convertido pra ela (Dennis, 2026-07-04:
        # "A Laura nunca converte o item comercial para a unidade do SINAPI. A Laura converte
        # a referência do SINAPI para a unidade comercial do item.").
        item["sinapi_confianca"] = escolha.get("confianca") if candidato else ("nenhuma" if escolha else None)
        item["sinapi_preco_equivalente"] = escolha.get("preco_equivalente_unidade_comercial")
    return itens

def _referencia_laura_item(descricao, unidade):
    """Camada 3: procura no histórico real de compras da própria Laura (itens_pedido) se algo
    parecido já foi comprado, e retorna o último preço pago como referência adicional à
    SINAPI (Princípio 5 da Política de Compras: "último preço pago" é referência de primeira
    classe). Reaproveita procurar_item() (financeiro/consultas.py) tal como já existia — sem
    chamada de IA, busca determinística.

    Tenta a descrição inteira primeiro (mais precisa, mas rara de bater por causa de fraseado
    diferente entre compras — ex: "Cimento CP II 50 kg" vs "Cimento CP-II 50kg" já registrado);
    cai pra busca por palavra significativa isolada se não achar nada. O grau de confiança
    (Princípio 8: toda referência declara origem e confiança) muda conforme a estratégia que
    funcionou — nunca apresenta um achado aproximado como se fosse exato.

    Filtro obrigatório de unidade igual (Dennis, 2026-07-04, achado real: "Revestimento
    Cerâmico" em M2 casou com um item histórico de bloco cerâmico em BLOCOS — unidades
    diferentes, produtos diferentes): candidato só é aceito se a unidade do pedido histórico
    for a mesma da unidade comercial do item atual. Ao contrário da Camada 2 (SINAPI), aqui
    NÃO existe conversão de unidade — "isso não deveria mudar". Sem a unidade do item pra
    comparar, não há como validar o filtro, então não retorna referência nenhuma (melhor
    admitir ausência do que arriscar comparar produtos diferentes)."""
    if not unidade:
        return None

    def _so_mesma_unidade(candidatos):
        return [c for c in candidatos if _mesma_unidade(c["unidade"], unidade)]

    resultado = _so_mesma_unidade(procurar_item(DB_PATH, descricao))
    grau = GrauConfianca.CONFIRMADA
    if not resultado:
        palavras = [p for p in _SINAPI_PALAVRA_RE.findall(descricao.lower()) if len(p) >= 3]
        for palavra in palavras:
            resultado = _so_mesma_unidade(procurar_item(DB_PATH, palavra))
            if resultado:
                grau = GrauConfianca.APROXIMADA
                break
    if not resultado:
        return None
    mais_recente = resultado[0]  # procurar_item já ordena por data_pagamento DESC
    return {
        "laura_preco_referencia": mais_recente["valor_unitario"],
        "laura_unidade_referencia": mais_recente["unidade"],
        "laura_data_referencia": mais_recente["data_pagamento"],
        "laura_fornecedor_referencia": mais_recente["fornecedor"],
        "laura_origem_referencia": OrigemReferencia.ULTIMO_PRECO_PAGO.value,
        "laura_grau_confianca_referencia": grau.value,
        # Descrição do item histórico encontrado — não é snapshot de preço, é matéria-prima
        # pra Camada de enriquecimento de descrição (2026-07-05, ver _adicionar_sugestao_descricao).
        # Transiente: só importa até o usuário aceitar ou ignorar a sugestão nesta sessão.
        "laura_descricao_referencia": mais_recente["descricao"],
    }

def _adicionar_referencia_laura(itens):
    """Anota cada item com a referência de último preço pago pela própria Laura, quando
    existir — roda depois da Camada 2 (SINAPI), juntando as duas referências na mesma tela,
    cada uma com sua origem e confiança declaradas (nunca escondendo qual é qual)."""
    for item in itens:
        if not isinstance(item, dict):
            continue
        referencia = _referencia_laura_item(item["descricao"], item.get("unidade")) or {}
        item["laura_preco_referencia"] = referencia.get("laura_preco_referencia")
        item["laura_unidade_referencia"] = referencia.get("laura_unidade_referencia")
        item["laura_data_referencia"] = referencia.get("laura_data_referencia")
        item["laura_fornecedor_referencia"] = referencia.get("laura_fornecedor_referencia")
        item["laura_origem_referencia"] = referencia.get("laura_origem_referencia")
        item["laura_grau_confianca_referencia"] = referencia.get("laura_grau_confianca_referencia")
        item["laura_descricao_referencia"] = referencia.get("laura_descricao_referencia")
    return itens

_PALAVRA_DIGITO_RE = re.compile(r"\d")

def _descricao_parece_generica(descricao):
    """Heurística leve (sem IA) pra decidir se uma descrição está pobre pra cotação — usada
    como rede de segurança quando o item não passa de novo pela Camada 1 (ex: depois de
    corrigir um campo manualmente, sem reinterpretar). Ponto de partida sugerido pelo
    Dennis, 2026-07-05: uma ou duas palavras, sem marca/dimensão/tipo/aplicação/embalagem —
    aproximado aqui por "poucas palavras e nenhum dígito" (dígito costuma indicar dimensão,
    embalagem ou código, sinal de que já não é genérico demais)."""
    palavras = descricao.strip().split()
    if len(palavras) > 2:
        return False
    return not _PALAVRA_DIGITO_RE.search(descricao)

def _adicionar_sugestao_descricao(itens):
    """Camada de enriquecimento de descrição (Dennis, 2026-07-05): "a Laura não deve apenas
    interpretar a lista do jeito que eu escrevi... deve me ajudar a melhorar a qualidade
    técnica da Lista de Compras." Roda depois das Camadas 2 e 3 — não faz busca nova,
    reaproveita os candidatos que elas já encontraram (histórico próprio e SINAPI).

    Prioridade como orientação, não regra cega: histórico real da empresa primeiro
    (conhecimento próprio, mais confiável pro vocabulário real da obra); SINAPI só como
    apoio quando o histórico não resolve, e só com confiança alta/média (nunca sugere a
    partir de um candidato que a própria Camada 2 já marcou como incerto). Sugestão nunca
    aparece se for igual à descrição atual — isso também é o que impede a sugestão de
    voltar em loop depois que o usuário já aceitou uma vez.

    Nunca decide sozinha: só anota `descricao_sugerida`/`descricao_sugerida_origem` pra
    tela apresentar; aplicar é sempre ação explícita do usuário ("Usar sugestão")."""
    for item in itens:
        if not isinstance(item, dict):
            continue
        atual = item["descricao"].strip().lower()
        generica = item.get("descricao_generica")
        if generica is None:
            generica = _descricao_parece_generica(item["descricao"])

        sugestao, origem = None, None
        if generica:
            cand_hist = item.get("laura_descricao_referencia")
            cand_sinapi = item.get("sinapi_descricao_referencia")
            sinapi_confiavel = item.get("sinapi_confianca") in ("alta", "media")
            if cand_hist and cand_hist.strip().lower() != atual:
                sugestao, origem = cand_hist, "histórico"
            elif cand_sinapi and sinapi_confiavel and cand_sinapi.strip().lower() != atual:
                sugestao, origem = cand_sinapi, "SINAPI"

        item["descricao_sugerida"] = sugestao
        item["descricao_sugerida_origem"] = origem
    return itens

def _fmt_qtde_segura(qtde):
    try:
        return _fmt_qtde(float(qtde))
    except (TypeError, ValueError):
        return str(qtde)

_CONFIANCA_LABEL_TECNICA = {"alta": "Alta confiança", "media": "Média confiança",
                             "baixa": "Baixa confiança", "nenhuma": "Sem correspondência"}
_GRAU_LABEL_LAURA = {"confirmada": "Confirmada", "aproximada": "Aproximada"}

def _linhas_analise_item(item):
    """Bloco de análise técnica de um item — reaproveitado tanto na análise da lista
    inteira (Nível 3 clássico, todos os itens) quanto na análise de um item só (a partir
    da Tela do Item). Nunca esconde origem/confiança de uma referência (Princípio 8,
    Política de Compras)."""
    if not isinstance(item, dict):
        return [str(item)]
    partes = [item["descricao"]]
    if item.get("fabricante"):
        partes.append(f"— {item['fabricante']}")
    if item.get("codigo"):
        partes.append(f"(cód. {item['codigo']})")
    linha = " ".join(partes)

    qtde, und, embalagem = item.get("quantidade"), item.get("unidade"), item.get("embalagem")
    if qtde is not None and und:
        linha += f" — {_fmt_qtde_segura(qtde)} {und}"
    elif qtde is not None:
        linha += f" — {_fmt_qtde_segura(qtde)} (unidade não identificada)"
    elif und:
        linha += f" — quantidade não identificada ({und})"
    elif embalagem:
        # Não achar a quantidade pedida não é o mesmo que não saber nada do produto —
        # a embalagem (tamanho de uma unidade de venda) já é uma informação útil por si
        # só, mesmo sem tabela legível o bastante pra dizer quantas foram compradas.
        linha += f" — embalagem {embalagem}, quantidade comercial não identificada"
    else:
        linha += " — quantidade e unidade não identificadas"
    linhas = [linha]

    if item.get("sinapi_codigo"):
        preco = item.get("sinapi_preco_referencia")
        und_sinapi = item.get("sinapi_unidade_referencia")
        confianca = _CONFIANCA_LABEL_TECNICA.get(item.get("sinapi_confianca"), "confiança não informada")
        linhas.append(
            f"   SINAPI ({confianca}): {item['sinapi_descricao_referencia']} "
            f"(cód. {item['sinapi_codigo']}, ref. {item.get('sinapi_mes_referencia') or '?'})"
        )
        preco_equiv = item.get("sinapi_preco_equivalente")
        if preco_equiv is not None and und:
            # Referência sempre expressa na unidade comercial do item — nunca o
            # contrário. O preço do SINAPI na unidade original vem só como contexto.
            linhas.append(f"   Referência SINAPI: R$ {_fmt_brl(preco_equiv)} / {und}")
            if preco:
                linhas.append(f"   (equivalente a R$ {_fmt_brl(preco)}/{und_sinapi})")
        elif preco:
            if und and und_sinapi and not _mesma_unidade(und, und_sinapi):
                linhas.append(
                    f"   Referência SINAPI: R$ {_fmt_brl(preco)}/{und_sinapi} "
                    f"(unidade diferente da comercial — conversão não calculada)"
                )
            else:
                linhas.append(f"   Referência SINAPI: R$ {_fmt_brl(preco)}/{und_sinapi}")
    else:
        linhas.append("   SINAPI: sem correspondência confiável")

    preco_laura = item.get("laura_preco_referencia")
    if preco_laura is not None:
        grau = _GRAU_LABEL_LAURA.get(item.get("laura_grau_confianca_referencia"), "")
        grau_fmt = f" ({grau})" if grau else ""
        und_laura = item.get("laura_unidade_referencia") or "?"
        data_laura = item.get("laura_data_referencia")
        data_fmt = f" em {_fmt_data_flexivel(data_laura)}" if data_laura else ""
        fornecedor = item.get("laura_fornecedor_referencia") or "fornecedor não identificado"
        linhas.append(
            f"   Última compra{grau_fmt}: R$ {_fmt_brl(preco_laura)}/{und_laura}"
            f"{data_fmt} — {fornecedor}"
        )
    else:
        linhas.append("   Última compra: sem referência própria encontrada")

    if item.get("observacoes"):
        linhas.append(f"   Obs: {item['observacoes']}")

    if item.get("descricao_sugerida"):
        linhas.append(
            f"   💡 Sugestão de descrição ({item['descricao_sugerida_origem']}): "
            f"{item['descricao_sugerida']}"
        )
        # Histórico tem prioridade sobre SINAPI (Dennis, 2026-07-05) — quando o histórico
        # venceu, o candidato do SINAPI ainda pode valer a pena mostrar como alternativa.
        if item["descricao_sugerida_origem"] == "histórico" and item.get("sinapi_descricao_referencia"):
            alt = item["sinapi_descricao_referencia"]
            if alt.strip().lower() != item["descricao_sugerida"].strip().lower():
                linhas.append(f"   Outra possibilidade (SINAPI): {alt}")
    return linhas

def _texto_analise_tecnica(itens, ggv):
    """Nível 3 (Análise Técnica) — tudo que a Laura sabe sobre cada item da lista inteira:
    confiança, código SINAPI, preço original, conversão, histórico. Só acessada por quem
    quer entender como a Laura chegou na referência (Dennis, 2026-07-04: "a inteligência
    trabalha nos bastidores; a tela principal não é um relatório técnico")."""
    label_ggv = f"Obra {ggv}" if ggv else "Obra ainda não definida"
    linhas = [f"🔍 <b>Análise técnica — {label_ggv}</b>"]
    if ggv:
        obra = buscar_obra(ggv)
        if obra and obra.get("endereco_entrega"):
            linhas.append(f"Endereço: {obra['endereco_entrega']}")
    linhas.append("")
    if not itens:
        linhas.append("Não consegui reconhecer nenhum item nesta lista.")
        return "\n".join(linhas)
    for i, item in enumerate(itens, 1):
        bloco = _linhas_analise_item(item)
        linhas.append(f"{i}. {bloco[0]}")
        linhas.extend(bloco[1:])
    return "\n".join(linhas)

def _texto_item_tecnico(item, indice):
    """Análise técnica de um item só, acessada a partir da Tela do Item (Dennis,
    2026-07-05: "a análise técnica deve sair desta tela" — vira nível opcional por item,
    não mais misturada com a view/menu principal)."""
    linhas = [f"🔍 <b>Análise técnica — Item {indice}</b>", ""]
    linhas.extend(_linhas_analise_item(item))
    return "\n".join(linhas)

def _preco_sinapi_item(item):
    """Preço de referência do SINAPI, já na unidade comercial quando possível — extraído à
    parte de _melhor_referencia_preco (2026-07-06) porque a Consultoria de Recompra precisa
    comparar o preço pago no histórico contra a referência SINAPI *atual*, mesmo quando
    também existe referência própria (que nesse caso venceria em _melhor_referencia_preco)."""
    if not item.get("sinapi_codigo"):
        return None
    if item.get("sinapi_preco_equivalente") is not None:
        return item["sinapi_preco_equivalente"]
    preco = item.get("sinapi_preco_referencia")
    if preco is not None and _mesma_unidade(item.get("unidade"), item.get("sinapi_unidade_referencia")):
        return preco
    return None

def _melhor_referencia_preco(item):
    """Prioridade de referência de preço (Dennis, 2026-07-04): 1) última compra própria
    (Camada 3, já filtrada por unidade igual), 2) referência própria consolidada da Laura
    (não existe ainda), 3) SINAPI convertido pra unidade comercial, 4) nenhuma. Sempre em
    R$/unidade comercial do item — nunca precisa converter de novo aqui, as Camadas 2 e 3 já
    entregam o preço na unidade certa quando existe."""
    if not isinstance(item, dict):
        return None
    if item.get("laura_preco_referencia") is not None:
        return item["laura_preco_referencia"]
    return _preco_sinapi_item(item)

def _avaliar_item(item):
    """Classifica o item pra tela de conferência (Dennis, 2026-07-04):
    🔴 atenção — existe algo que impede uma boa cotação (quantidade/unidade desconhecida,
        item não interpretado);
    🟡 revisar — merece conferência mas não impede pedir orçamento (confiança média/baixa,
        correspondência aproximada, observação da IA, ou nenhuma referência de preço ainda —
        "se a Laura nunca viu aquele item, isso não impede pedir orçamento, só significa que
        ela ainda não possui conhecimento suficiente");
    🟢 ok — tudo consistente."""
    if not isinstance(item, dict):
        return "atencao", ["Item não interpretado"]

    alertas_atencao = []
    if item.get("quantidade") is None:
        alertas_atencao.append("Quantidade não identificada")
    if not item.get("unidade"):
        alertas_atencao.append("Unidade comercial não identificada")
    if alertas_atencao:
        return "atencao", alertas_atencao

    alertas_revisar = []
    confianca = item.get("sinapi_confianca")
    if confianca == "media":
        alertas_revisar.append("Correspondência SINAPI de confiança média")
    elif confianca == "baixa":
        alertas_revisar.append("Correspondência SINAPI de confiança baixa")
    if item.get("laura_grau_confianca_referencia") == "aproximada":
        alertas_revisar.append("Referência própria aproximada")
    if item.get("observacoes"):
        alertas_revisar.append("Observação da IA — conferir")
    if _melhor_referencia_preco(item) is None:
        alertas_revisar.append("Sem referência de preço conhecida")
    if item.get("descricao_sugerida"):
        alertas_revisar.append("Descrição genérica — sugestão disponível")
    if alertas_revisar:
        return "revisar", alertas_revisar
    return "ok", []

_EMOJI_STATUS = {"ok": "🟢", "revisar": "🟡", "atencao": "🔴"}

def _calcular_referencia_total(itens):
    """Referência total estimada de uma lista — mesmo cálculo usado na Tela de Conferência
    (texto) e no PDF (2026-07-05), pra nunca existirem dois números diferentes pro mesmo
    conceito ("Convergência antes de paralelismo", docs/CONSTITUICAO.md)."""
    total = 0.0
    parcial = False
    for item in itens:
        if not isinstance(item, dict):
            parcial = True
            continue
        preco_ref = _melhor_referencia_preco(item)
        qtde, und = item.get("quantidade"), item.get("unidade")
        if preco_ref is not None and und and qtde is not None:
            total += preco_ref * qtde
        else:
            parcial = True
    return total, parcial

def _texto_lista_conferencia(itens, ggv, endereco_override=None, observacoes=None, resumo=None):
    """Nível 1 (Tela de Conferência) — a tela principal depois de interpretar. Objetivo não é
    explicar como a Laura chegou na resposta, é permitir conferir rápido (Dennis, 2026-07-04):
    "o que vou comprar, quanto, uma ideia de preço, o que precisa da minha atenção". Detalhe
    técnico fica pro Nível 3 (Análise Técnica), edição completa de um item pro Nível 2.

    Cabeçalho ganhou 3 campos editáveis (Dennis, 2026-07-05): Obra, Endereço (herdado da
    obra, mas com override só para esta lista — nunca sobrescreve obras.endereco_entrega) e
    Observações gerais (opcional, instrução geral pro fornecedor)."""
    linhas = [f"📝 <b>Lista de Compras — Obra {ggv}</b>" if ggv else "📝 <b>Lista de Compras</b>"]
    if ggv:
        obra = buscar_obra(ggv)
        endereco = endereco_override or (obra.get("endereco_entrega") if obra else None)
        linhas.append(f"📍 Endereço: {endereco}" if endereco else "⚠️ Endereço de entrega não definido")
    else:
        linhas.append("⚠️ Obra ainda não definida")
    linhas.append(f"🗒 Observações: {observacoes}" if observacoes else "🗒 Observações: —")
    linhas.append(f"🏷 Resumo: {resumo}" if resumo else "🏷 Resumo: —")
    linhas.append("")

    if not itens:
        linhas.append("Não consegui reconhecer nenhum item nesta lista.")
        return "\n".join(linhas)

    alertas_agrupados = {}
    n_itens_com_alerta = 0

    for i, item in enumerate(itens, 1):
        status, alertas = _avaliar_item(item)
        if status != "ok":
            n_itens_com_alerta += 1
        for alerta in alertas:
            alertas_agrupados.setdefault(alerta, []).append(i)

        emoji = _EMOJI_STATUS[status]
        if not isinstance(item, dict):
            linhas.append(f"{emoji} {i}. {item}")
            linhas.append("")
            continue

        linhas.append(f"{emoji} {i}. {item['descricao']}")
        qtde, und = item.get("quantidade"), item.get("unidade")
        if qtde is not None and und:
            detalhe = f"{_fmt_qtde_segura(qtde)} {und}"
        elif und:
            detalhe = f"{und} (quantidade não identificada)"
        elif item.get("embalagem"):
            detalhe = f"Embalagem {item['embalagem']}"
        elif qtde is not None:
            detalhe = f"{_fmt_qtde_segura(qtde)} (unidade não identificada)"
        else:
            detalhe = "quantidade/unidade não identificadas"
        if item.get("fabricante"):
            detalhe += f" • {item['fabricante']}"
        linhas.append(f"     {detalhe}")

        preco_ref = _melhor_referencia_preco(item)
        if preco_ref is not None and und:
            linhas.append(f"     Referência: ~R$ {_fmt_brl(preco_ref)}/{und}")
        else:
            linhas.append("     Referência: ainda não conhecida")
        linhas.append("")

    total_referencia, total_parcial = _calcular_referencia_total(itens)

    if alertas_agrupados:
        linhas.append("⚠️ <b>Revisar:</b>")
        for texto, numeros in alertas_agrupados.items():
            rotulo = "item" if len(numeros) == 1 else "itens"
            linhas.append(f"• {texto} — {rotulo} {', '.join(str(n) for n in numeros)}")
        linhas.append("")

    linhas.append("<b>Resumo</b>")
    linhas.append(f"Itens: {len(itens)}")
    total_str = f"R$ {_fmt_brl(total_referencia)}"
    if total_parcial:
        total_str += " (parcial — alguns itens sem quantidade ou referência)"
    linhas.append(f"Referência estimada: {total_str}")
    linhas.append(f"Alertas: {n_itens_com_alerta}")
    return "\n".join(linhas)

def _teclado_lista_conferencia(ggv):
    token = ggv or "nao_identificado"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏗 Obra",                  callback_data="lc_defobra"),
         InlineKeyboardButton("📍 Endereço",               callback_data="lc_campolista:endereco"),
         InlineKeyboardButton("🗒 Observações",            callback_data="lc_campolista:observacoes")],
        [InlineKeyboardButton("🏷 Resumo",                 callback_data="lc_campolista:resumo")],
        [InlineKeyboardButton("✏️ Editar item",           callback_data=f"lc_editar:{token}"),
         InlineKeyboardButton("🔍 Análise técnica",        callback_data=f"lc_tecnico:{token}")],
        [InlineKeyboardButton("✅ Gerar Lista de Compras", callback_data=f"lc_gerar:{token}")],
        [InlineKeyboardButton("✖ Fechar",                  callback_data="lc_fechar")],
    ])

def _renderizar_lista_conferencia(itens, ggv, ctx):
    """Helper de render pra centralizar a leitura do estado ephemeral de cabeçalho
    (endereço/observações), evitando repetir ctx.user_data.get(...) nos ~8 pontos que
    reemitem a Tela de Conferência."""
    texto = _texto_lista_conferencia(
        itens, ggv, ctx.user_data.get("lista_endereco"), ctx.user_data.get("lista_observacoes"),
        ctx.user_data.get("lista_resumo")
    )
    return texto, _teclado_lista_conferencia(ggv)

def _teclado_definir_obra_lista(obras):
    botoes, row = [], []
    for codigo, _ in obras:
        row.append(InlineKeyboardButton(codigo, callback_data=f"lc_setobra:{codigo}"))
        if len(row) == 2:
            botoes.append(row)
            row = []
    if row:
        botoes.append(row)
    botoes.append([InlineKeyboardButton("← Voltar", callback_data="lc_voltar")])
    return InlineKeyboardMarkup(botoes)

def _teclado_item_picker(itens):
    botoes = []
    for i, item in enumerate(itens, 1):
        desc = item["descricao"] if isinstance(item, dict) else str(item)
        botoes.append([InlineKeyboardButton(f"{i}. {desc[:40]}", callback_data=f"lc_item:{i}")])
    botoes.append([InlineKeyboardButton("← Voltar", callback_data="lc_voltar")])
    return InlineKeyboardMarkup(botoes)

def _referencia_e_correspondencia(item):
    """(preço, rótulo de confiança) da melhor referência do item pra Tela do Item — mesma
    prioridade de _melhor_referencia_preco (própria > SINAPI > nenhuma), mas junto com o
    rótulo de quem venceu, pra nunca esconder a origem (Princípio 8, Política de Compras)."""
    if item.get("laura_preco_referencia") is not None:
        grau = _GRAU_LABEL_LAURA.get(item.get("laura_grau_confianca_referencia"), "Referência própria")
        return item["laura_preco_referencia"], grau
    preco = _melhor_referencia_preco(item)
    if preco is not None:
        label = _CONFIANCA_LABEL_TECNICA.get(item.get("sinapi_confianca"), "Confiança não informada")
        return preco, label
    return None, None

_CAMPOS_ITEM_LISTA = {
    "descricao":   ("Produto", "Digite a nova descrição."),
    "fabricante":  ("Fabricante", "Digite o novo fabricante."),
    "codigo":      ("Código comercial", "Digite o novo código."),
    "quantidade":  ("Quantidade", "Digite a nova quantidade."),
    "unidade":     ("Unidade comercial", "Digite a nova unidade comercial."),
    "observacoes": ("Observações", "Digite a nova observação."),
}

def _linhas_recompra(item):
    """Painel "Você já comprou isso" — Consultoria de Recompra (Dennis, 2026-07-06): mostra
    o que foi comprado da última vez com destaque (fornecedor + descrição real, não só um
    preço), e compara com a referência SINAPI atual como informação neutra — sem limiar de
    tempo/variação pra decidir "não vale mais a pena" ainda ("sem limites por enquanto"); a
    decisão continua sempre do usuário."""
    desc_hist = item.get("laura_descricao_referencia") or item["descricao"]
    fornecedor = item.get("laura_fornecedor_referencia") or "fornecedor não identificado"
    und_hist = item.get("laura_unidade_referencia") or item.get("unidade") or "?"
    preco_hist = item["laura_preco_referencia"]
    grau = _GRAU_LABEL_LAURA.get(item.get("laura_grau_confianca_referencia"), "")
    grau_fmt = f" ({grau})" if grau else ""
    tempo = _tempo_decorrido(item.get("laura_data_referencia"))
    tempo_fmt = f" · há {tempo}" if tempo else ""

    linhas = [
        "🔁 Você já comprou isso",
        f"{desc_hist} — {fornecedor}",
        f"R$ {_fmt_brl(preco_hist)}/{und_hist}{grau_fmt}{tempo_fmt}",
    ]
    preco_sinapi = _preco_sinapi_item(item)
    if preco_sinapi is not None and preco_hist:
        variacao = (preco_sinapi - preco_hist) / preco_hist * 100
        sinal = "+" if variacao >= 0 else ""
        linhas.append("")
        linhas.append(
            f"📈 Referência SINAPI atual: R$ {_fmt_brl(preco_sinapi)}/{und_hist} "
            f"({sinal}{variacao:.0f}% desde a última compra)"
        )
    linhas.append("")
    return linhas

def _texto_tela_item(indice, item, pendente):
    """Tela do Item (Nível 2) — view e menu de correção juntos numa tela só (Dennis,
    2026-07-05: "uma tela = uma decisão"; reduzir a ficha técnica a um menu de alteração).
    Enquanto existe rascunho pendente, referência/correspondência somem da tela — nunca
    mostradas como se ainda fossem válidas — até o usuário concluir a edição."""
    if not isinstance(item, dict):
        return f"📦 <b>Item {indice}</b>\n\n{item}"
    qtde, und, fabricante = item.get("quantidade"), item.get("unidade"), item.get("fabricante")
    linhas = [f"📦 <b>Item {indice}</b>", "", item["descricao"], ""]
    partes = []
    if qtde is not None and und:
        partes.append(f"{_fmt_qtde_segura(qtde)} {und}")
    elif und:
        partes.append(f"{und} (quantidade não identificada)")
    elif qtde is not None:
        partes.append(f"{_fmt_qtde_segura(qtde)} (unidade não identificada)")
    else:
        partes.append("quantidade/unidade não identificadas")
    if fabricante:
        partes.append(fabricante)
    linhas.append(" • ".join(partes))
    linhas.append("")
    tem_recompra = not pendente and item.get("laura_preco_referencia") is not None
    if tem_recompra:
        linhas.extend(_linhas_recompra(item))
    elif not pendente and item.get("descricao_sugerida"):
        linhas.append(
            f"💡 Descrição genérica. Sugestão: {item['descricao_sugerida']} "
            f"({item['descricao_sugerida_origem']})"
        )
        linhas.append("")
    if pendente:
        linhas.append("⚠️ Alterações pendentes")
        linhas.append("A referência será recalculada ao concluir a edição.")
    elif not tem_recompra:
        preco, label = _referencia_e_correspondencia(item)
        linhas.append("Referência Laura")
        linhas.append(f"~R$ {_fmt_brl(preco)}/{und}" if preco is not None and und else "ainda não conhecida")
        if label:
            linhas.append("")
            linhas.append("Correspondência")
            linhas.append(f"✔ {label}")
    linhas.append("")
    linhas.append("─" * 20)
    linhas.append("O que deseja alterar?")
    return "\n".join(linhas)

def _teclado_item_tela(indice, item, pendente):
    """Menu da Tela do Item — cada campo é uma ação direta (estilo configurações do
    Telegram), sem tela intermediária de 'corrigir campos'. Item em fallback (string, não
    interpretado) só oferece Reinterpretar — não há campos estruturados pra corrigir.

    Item já interpretado NÃO mostra "Reinterpretar item" (Dennis, 2026-07-05: "se o usuário
    fica em dúvida entre dois botões, um deles não deveria estar na tela principal" —
    'Concluir edição' já recalcula SINAPI/referência/confiança sozinho; reinterpretar do
    zero via texto livre vira recurso de exceção, sem lugar na tela principal por ora)."""
    if not isinstance(item, dict):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Reinterpretar item", callback_data=f"lc_reinterpretar:{indice}")],
            [InlineKeyboardButton("⬅ Voltar", callback_data="lc_voltar")],
        ])
    botoes = [
        [InlineKeyboardButton("📝 Produto",           callback_data=f"lc_campo:{indice}:descricao"),
         InlineKeyboardButton("🏷 Fabricante",         callback_data=f"lc_campo:{indice}:fabricante")],
        [InlineKeyboardButton("🔢 Código comercial",  callback_data=f"lc_campo:{indice}:codigo"),
         InlineKeyboardButton("📦 Quantidade",         callback_data=f"lc_campo:{indice}:quantidade")],
        [InlineKeyboardButton("📏 Unidade comercial",  callback_data=f"lc_campo:{indice}:unidade"),
         InlineKeyboardButton("🗒 Observações",        callback_data=f"lc_campo:{indice}:observacoes")],
        [InlineKeyboardButton("🔍 Ver análise técnica", callback_data=f"lc_tecnicoitem:{indice}")],
    ]
    if not pendente:
        if item.get("laura_preco_referencia") is not None:
            botoes.append([InlineKeyboardButton("🔁 Repetir esta compra", callback_data=f"lc_repetircompra:{indice}")])
        elif item.get("descricao_sugerida"):
            botoes.append([InlineKeyboardButton("✅ Usar sugestão", callback_data=f"lc_usarsugestao:{indice}")])
    if pendente:
        botoes.append([InlineKeyboardButton("💾 Concluir edição", callback_data=f"lc_concluir:{indice}")])
    else:
        botoes.append([InlineKeyboardButton("⬅ Voltar", callback_data="lc_voltar")])
    return InlineKeyboardMarkup(botoes)

def _teclado_analise_tecnica():
    return InlineKeyboardMarkup([[InlineKeyboardButton("← Voltar", callback_data="lc_voltar")]])

def _teclado_item_tecnico(indice):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Voltar", callback_data=f"lc_item:{indice}")]])

async def _cb_lc_editar(query, ctx, partes):
    itens = ctx.user_data.get("lista_itens") or []
    if not itens:
        await query.edit_message_text("Lista não encontrada nesta sessão. Envie /lista novamente.")
        return
    await query.edit_message_text("Escolha o item que deseja corrigir:", reply_markup=_teclado_item_picker(itens))

def _preparar_tela_item(ctx, indice, itens):
    """Resolve o item a exibir (rascunho ou committed) e se há alteração pendente de
    verdade — rascunho comparado ao item real, não só "existe rascunho" (Dennis,
    2026-07-05: abrir um campo e voltar sem digitar nada não pode aparecer como pendência).
    Também descarta rascunho de um item diferente do que está sendo exibido agora."""
    if ctx.user_data.get("lista_item_indice") != indice:
        ctx.user_data.pop("lista_item_rascunho", None)
        ctx.user_data.pop("lista_item_indice", None)
    rascunho = ctx.user_data.get("lista_item_rascunho")
    committed = itens[indice - 1] if 1 <= indice <= len(itens) else None
    if rascunho is None:
        return committed, False
    return rascunho, isinstance(committed, dict) and rascunho != committed

def _teclado_voltar_item(indice):
    return InlineKeyboardMarkup([[InlineKeyboardButton("← Voltar", callback_data=f"lc_item:{indice}")]])

async def _cb_lc_item(query, ctx, partes):
    indice = int(partes[1])
    itens = ctx.user_data.get("lista_itens") or []
    if not (1 <= indice <= len(itens)):
        await query.edit_message_text("Item não encontrado.")
        return
    ctx.user_data["aguardando"] = None
    item_exibir, pendente = _preparar_tela_item(ctx, indice, itens)
    await query.edit_message_text(
        _texto_tela_item(indice, item_exibir, pendente), parse_mode="HTML",
        reply_markup=_teclado_item_tela(indice, item_exibir, pendente)
    )

async def _cb_lc_campo(query, ctx, partes):
    indice, campo = int(partes[1]), partes[2]
    if ctx.user_data.get("lista_item_indice") != indice:
        itens = ctx.user_data.get("lista_itens") or []
        if not (1 <= indice <= len(itens)) or not isinstance(itens[indice - 1], dict):
            await query.edit_message_text("Item não encontrado.")
            return
        ctx.user_data["lista_item_rascunho"] = dict(itens[indice - 1])
        ctx.user_data["lista_item_indice"] = indice
    ctx.user_data["aguardando"] = f"lista_campo_{campo}"
    label, instrucao = _CAMPOS_ITEM_LISTA[campo]
    valor_atual = ctx.user_data["lista_item_rascunho"].get(campo)
    if campo == "quantidade":
        valor_fmt = _fmt_qtde_segura(valor_atual) if valor_atual is not None else "—"
    else:
        valor_fmt = valor_atual or "—"
    await query.edit_message_text(
        f"{label}\n\nValor atual:\n{valor_fmt}\n\n{instrucao}",
        reply_markup=_teclado_voltar_item(indice)
    )

async def _aplicar_descricao_no_rascunho(query, ctx, indice, itens, nova_descricao, msg_vazio):
    """Aplica uma descrição candidata (sugestão de enriquecimento ou repetição de compra) no
    rascunho do item — mesmo mecanismo de corrigir o campo Produto manualmente. 'Concluir
    edição' recalcula SINAPI/referência com a descrição nova, sem chamada de IA extra aqui.
    Compartilhado entre "Usar sugestão" e "Repetir esta compra" (2026-07-06) — mesma ação,
    só a origem da descrição muda."""
    if not (1 <= indice <= len(itens)) or not isinstance(itens[indice - 1], dict):
        await query.edit_message_text("Item não encontrado.")
        return
    item = itens[indice - 1]
    if not nova_descricao:
        await query.edit_message_text(msg_vazio, reply_markup=_teclado_voltar_item(indice))
        return
    rascunho = dict(item)
    rascunho["descricao"] = nova_descricao
    ctx.user_data["lista_item_rascunho"] = rascunho
    ctx.user_data["lista_item_indice"] = indice
    await query.edit_message_text(
        _texto_tela_item(indice, rascunho, True), parse_mode="HTML",
        reply_markup=_teclado_item_tela(indice, rascunho, True)
    )

async def _cb_lc_usarsugestao(query, ctx, partes):
    """Aceita a descrição sugerida (histórico próprio ou SINAPI) — Dennis, 2026-07-05: "a
    Laura deve me ajudar a melhorar a qualidade técnica da Lista de Compras"."""
    indice = int(partes[1])
    itens = ctx.user_data.get("lista_itens") or []
    sugestao = itens[indice - 1].get("descricao_sugerida") if 1 <= indice <= len(itens) and isinstance(itens[indice - 1], dict) else None
    await _aplicar_descricao_no_rascunho(query, ctx, indice, itens, sugestao, "Sugestão não encontrada.")

async def _cb_lc_repetircompra(query, ctx, partes):
    """"Repetir esta compra" — Consultoria de Recompra (Dennis, 2026-07-06): aplica a
    descrição do item histórico encontrado (Camada 3) no rascunho. Preço/fornecedor não são
    copiados — são só informação; "Concluir edição" recalcula a referência certa pra
    descrição nova."""
    indice = int(partes[1])
    itens = ctx.user_data.get("lista_itens") or []
    descricao_historica = itens[indice - 1].get("laura_descricao_referencia") if 1 <= indice <= len(itens) and isinstance(itens[indice - 1], dict) else None
    await _aplicar_descricao_no_rascunho(query, ctx, indice, itens, descricao_historica, "Compra anterior não encontrada.")

async def _cb_lc_concluir(query, ctx, partes):
    indice = int(partes[1])
    rascunho = ctx.user_data.get("lista_item_rascunho")
    itens = ctx.user_data.get("lista_itens") or []
    if rascunho is None or not (1 <= indice <= len(itens)):
        await query.edit_message_text("Contexto perdido. Envie /lista novamente.")
        return
    await query.edit_message_text("Recalculando...")
    # termo_busca_sinapi/descricao_generica são julgamentos da IA presos à descrição antiga
    # (Camada 1) — se a descrição mudou, ficam obsoletos. Descartados aqui: termo_busca_sinapi
    # cai no fallback já existente (busca pela descrição atual); descricao_generica cai na
    # heurística leve de _adicionar_sugestao_descricao (sem IA, já que não há reinterpretação).
    rascunho.pop("termo_busca_sinapi", None)
    rascunho.pop("descricao_generica", None)
    novos = await _adicionar_correspondencia_sinapi([rascunho])
    novos = _adicionar_referencia_laura(novos)
    novo_item = _adicionar_sugestao_descricao(novos)[0]
    itens[indice - 1] = novo_item
    ctx.user_data["lista_itens"] = itens
    ctx.user_data.pop("lista_item_rascunho", None)
    ctx.user_data.pop("lista_item_indice", None)
    ggv = ctx.user_data.get("lista_ggv")
    texto, markup = _renderizar_lista_conferencia(itens, ggv, ctx)
    await query.edit_message_text(texto, parse_mode="HTML", reply_markup=markup)

async def _cb_lc_tecnicoitem(query, ctx, partes):
    indice = int(partes[1])
    itens = ctx.user_data.get("lista_itens") or []
    if not (1 <= indice <= len(itens)):
        await query.edit_message_text("Item não encontrado.")
        return
    await query.edit_message_text(
        _texto_item_tecnico(itens[indice - 1], indice), parse_mode="HTML",
        reply_markup=_teclado_item_tecnico(indice)
    )

async def _cb_lc_reinterpretar(query, ctx, partes):
    indice = int(partes[1])
    ctx.user_data.pop("lista_item_rascunho", None)
    ctx.user_data["aguardando"] = "lista_reinterpretar_item"
    ctx.user_data["lista_item_indice"] = indice
    await query.edit_message_text(
        "Envie a nova descrição pra reinterpretar este item:",
        reply_markup=_teclado_voltar_item(indice)
    )

async def _cb_lc_tecnico(query, ctx, partes):
    ggv_token = partes[1]
    ggv = None if ggv_token == "nao_identificado" else ggv_token
    itens = ctx.user_data.get("lista_itens") or []
    await query.edit_message_text(
        _texto_analise_tecnica(itens, ggv), parse_mode="HTML",
        reply_markup=_teclado_analise_tecnica()
    )

async def _cb_lc_voltar(query, ctx, partes):
    itens = ctx.user_data.get("lista_itens") or []
    ggv = ctx.user_data.get("lista_ggv")
    texto, markup = _renderizar_lista_conferencia(itens, ggv, ctx)
    await query.edit_message_text(texto, parse_mode="HTML", reply_markup=markup)

async def _cb_lc_defobra(query, ctx, partes):
    obras = _listar_obras()
    await query.edit_message_text(
        mostrar_lista_obras(obras), reply_markup=_teclado_definir_obra_lista(obras)
    )

async def _cb_lc_setobra(query, ctx, partes):
    codigo = partes[1]
    ctx.user_data["lista_ggv"] = codigo
    itens = ctx.user_data.get("lista_itens") or []
    texto, markup = _renderizar_lista_conferencia(itens, codigo, ctx)
    await query.edit_message_text(texto, parse_mode="HTML", reply_markup=markup)

_CAMPOS_LISTA_GERAL = {
    "endereco":     ("Endereço de entrega", "Digite o novo endereço de entrega.", "lista_endereco"),
    "observacoes":  ("Observações gerais", "Digite as observações gerais da compra.", "lista_observacoes"),
    "resumo":       ("Resumo da lista", "Digite um resumo curto (aparece no nome dos PDFs gerados, ex: \"Materiais elétricos\").", "lista_resumo"),
}

async def _cb_lc_campolista(query, ctx, partes):
    """Observações continua texto livre direto; Endereço reaproveita o mesmo mecanismo de
    presets do Pedido de Compra (Obra/Casa/Escritório/Chácara/Outro) — Dennis, 2026-07-05:
    "endereço de entrega é o mesmo conceito... a Lista deve reaproveitar essa mesma
    experiência, não criar um fluxo paralelo mais simples"."""
    campo = partes[1]
    if campo == "endereco":
        ggv = ctx.user_data.get("lista_ggv")
        await query.edit_message_text(
            "Endereço de entrega — escolha uma opção:",
            reply_markup=teclado_escolha_endereco("lista", "-", ggv, "lc_voltar")
        )
        return
    label, instrucao, chave_estado = _CAMPOS_LISTA_GERAL[campo]
    ctx.user_data["aguardando"] = f"lista_geral_{campo}"
    valor_atual = ctx.user_data.get(chave_estado)
    await query.edit_message_text(
        f"{label}\n\nValor atual:\n{valor_atual or '—'}\n\n{instrucao}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Voltar", callback_data="lc_voltar")]])
    )


async def _cb_lc_gerar(query, ctx, partes):
    ggv_token = partes[1]
    ggv = None if ggv_token == "nao_identificado" else ggv_token
    itens = ctx.user_data.get("lista_itens") or []
    if not ggv:
        await query.edit_message_text(
            "Não dá pra gravar sem obra definida. Toque em \"📍 Definir obra\" abaixo.",
            reply_markup=_teclado_lista_conferencia(ggv)
        )
        return
    itens_validos = [item for item in itens if isinstance(item, dict)]
    if not itens_validos:
        await query.edit_message_text("Lista vazia — nada pra gravar.")
        return
    # Reabrindo uma lista antiga pelo picker (lc_abrir), regrava a mesma lista_id em vez de
    # criar uma nova — só uma sessão nova (sem lista_id_edicao) cria um registro histórico.
    lista_id = ctx.user_data.get("lista_id_edicao")
    if not lista_id:
        lista_id, _criada = criar_ou_buscar_lista_aberta(DB_PATH, ggv)
    # Só grava endereço/observações se foram tocados nesta sessão — reabrir uma lista já
    # existente sem reeditar esses campos não pode apagar um valor já salvo antes.
    campos_lista = {}
    if ctx.user_data.get("lista_endereco"):
        campos_lista["endereco_entrega"] = ctx.user_data["lista_endereco"]
    if ctx.user_data.get("lista_observacoes"):
        campos_lista["observacoes"] = ctx.user_data["lista_observacoes"]
    if ctx.user_data.get("lista_resumo"):
        campos_lista["resumo"] = ctx.user_data["lista_resumo"]
    if campos_lista:
        atualizar_lista(DB_PATH, lista_id, **campos_lista)
    # Cada confirmação reflete a lista inteira vista agora, não um incremento — reabrir e
    # confirmar de novo a mesma lista aberta (ex: pra testar uma correção) duplicava os
    # itens, porque adicionar_item() só insere. Mesmo padrão de _salvar_itens_pedido()
    # (Pedido de Compra): a versão mais recente substitui a anterior. Soft-delete (não
    # apaga de verdade) pra manter o padrão de remover_item() já usado no resto do módulo.
    for item_existente in listar_itens(DB_PATH, lista_id):
        remover_item(DB_PATH, item_existente["id"])
    for item in itens_validos:
        adicionar_item(
            DB_PATH, lista_id,
            descricao=item["descricao"],
            unidade=item.get("unidade") or "",
            quantidade=item.get("quantidade"),
            fabricante=item.get("fabricante"),
            codigo=item.get("codigo"),
            sinapi_codigo=item.get("sinapi_codigo"),
            sinapi_descricao_referencia=item.get("sinapi_descricao_referencia"),
            sinapi_unidade_referencia=item.get("sinapi_unidade_referencia"),
            sinapi_preco_referencia=item.get("sinapi_preco_referencia"),
            sinapi_mes_referencia=item.get("sinapi_mes_referencia"),
            sinapi_confianca=item.get("sinapi_confianca"),
            sinapi_preco_equivalente=item.get("sinapi_preco_equivalente"),
            observacoes=item.get("observacoes"),
            laura_preco_referencia=item.get("laura_preco_referencia"),
            laura_data_referencia=item.get("laura_data_referencia"),
            laura_fornecedor_referencia=item.get("laura_fornecedor_referencia"),
            laura_origem_referencia=item.get("laura_origem_referencia"),
            laura_grau_confianca_referencia=item.get("laura_grau_confianca_referencia"),
        )
    # Fecha a lista (Dennis, 2026-07-06) — cada geração vira um registro histórico próprio,
    # localizável depois pelo picker "📝 Listas de Compras" (data ou Resumo).
    encerrar_lista(DB_PATH, lista_id)
    n = len(itens_validos)
    await query.edit_message_text(f"✅ Lista de Compras da Obra {ggv} salva — {n} ite{'m' if n == 1 else 'ns'}. Gerando PDF...")

    data_str = datetime.now().strftime('%Y-%m-%d')
    resumo_slug = _slug_arquivo(ctx.user_data.get("lista_resumo")) or "lista-compras"
    pasta = _pasta_orcamentos(ggv)
    for com_precos, sufixo, caption in (
        (True,  "ref",  f"Lista de Compras — Obra {ggv} (com referência de preço, uso interno)"),
        (False, "orç",  f"Lista de Compras — Obra {ggv} (para solicitar orçamento ao fornecedor)"),
    ):
        html      = _gerar_html_lista(lista_id, com_precos=com_precos)
        pdf_bytes = await _html_para_pdf(html)
        nome_arquivo = f"{ggv}-list-{data_str}-{resumo_slug}-{sufixo}.pdf"
        (pasta / nome_arquivo).write_bytes(pdf_bytes)
        await ctx.bot.send_document(
            chat_id=query.message.chat_id,
            document=pdf_bytes,
            filename=nome_arquivo,
            caption=caption
        )

    ctx.user_data["aguardando"] = None
    ctx.user_data.pop("lista_itens", None)
    ctx.user_data.pop("lista_ggv", None)
    ctx.user_data.pop("lista_endereco", None)
    ctx.user_data.pop("lista_observacoes", None)
    ctx.user_data.pop("lista_resumo", None)
    ctx.user_data.pop("lista_id_edicao", None)

async def _cb_lc_fechar(query, ctx, partes):
    ctx.user_data["aguardando"] = None
    ctx.user_data.pop("lista_ggv_preselecionada", None)
    ctx.user_data.pop("lista_itens", None)
    ctx.user_data.pop("lista_ggv", None)
    ctx.user_data.pop("lista_endereco", None)
    ctx.user_data.pop("lista_observacoes", None)
    ctx.user_data.pop("lista_resumo", None)
    ctx.user_data.pop("lista_id_edicao", None)
    ctx.user_data.pop("lista_item_indice", None)
    ctx.user_data.pop("lista_item_rascunho", None)
    await query.edit_message_text("Fechado.")

def _itens_lista_materiais(dados):
    """Parseia o array JSON retornado pela IA (PROMPT_INTERPRETAR_LISTA) em itens
    estruturados: numero, descricao, fabricante, codigo, unidade, quantidade, observacoes.

    Claude às vezes envolve o JSON em cercas de markdown mesmo quando instruído a não
    fazer — removidas defensivamente antes do parse. Se o JSON vier malformado, cada linha
    não vazia do texto bruto vira um item em string (fallback) — nunca perde item
    silenciosamente, mesmo espírito do fallback que já existia no parser antigo."""
    texto = dados.strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```[a-zA-Z]*\n?", "", texto)
        texto = re.sub(r"\n?```$", "", texto).strip()
    try:
        itens_json = json.loads(texto)
        if not isinstance(itens_json, list):
            raise ValueError("Resposta não é uma lista JSON")
        resultado = []
        for item in itens_json:
            if not isinstance(item, dict) or not item.get("descricao"):
                continue
            resultado.append({
                "numero": item.get("numero"),
                "descricao": str(item["descricao"]).strip(),
                "fabricante": item.get("fabricante") or None,
                "codigo": item.get("codigo") or None,
                "unidade": item.get("unidade") or None,
                "quantidade": item.get("quantidade"),
                "embalagem": item.get("embalagem") or None,
                "termo_busca_sinapi": item.get("termo_busca_sinapi") or None,
                "descricao_generica": bool(item.get("descricao_generica")),
                "observacoes": item.get("observacoes") or None,
            })
        return resultado
    except (json.JSONDecodeError, ValueError, TypeError):
        return [linha.strip() for linha in dados.splitlines() if linha.strip()]

async def lista_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DONO_ID:
        return
    ctx.user_data["aguardando"] = "lista_conteudo"
    ctx.user_data["lista_ggv_preselecionada"] = None
    if ctx.args:
        codigo = ctx.args[0].upper()
        if GGV_CODIGO_RE.match(codigo) and buscar_obra(codigo):
            ctx.user_data["lista_ggv_preselecionada"] = codigo
    await update.message.reply_text("Envie a lista — texto, foto ou PDF.")

async def receber_arquivo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DONO_ID:
        return

    if update.message.photo:
        tg_file = await update.message.photo[-1].get_file()
        nome = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        mime = None
    elif update.message.document:
        tg_file = await update.message.document.get_file()
        nome = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{update.message.document.file_name}"
        mime = update.message.document.mime_type or "application/pdf"
    else:
        await update.message.reply_text("Recebi. Ainda não sei o que fazer com isso.")
        return

    conteudo = await tg_file.download_as_bytearray()
    hash_arquivo = hashlib.sha256(conteudo).hexdigest()
    if TEST_MODE:
        hash_arquivo += f"_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    if ja_existe(hash_arquivo):
        await update.message.reply_text("Este arquivo já foi recebido.")
        return

    if mime is None:
        mime = "image/png" if conteudo[:4] == b'\x89PNG' else "image/jpeg"

    ACEITOS = {"image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"}
    if mime not in ACEITOS:
        await update.message.reply_text(
            f"Formato não suportado: {mime}\n\n"
            "Aceito: foto (JPEG, PNG, GIF, WEBP) ou PDF."
        )
        return

    if ctx.user_data.get("aguardando") == "lista_conteudo":
        ggv = ctx.user_data.get("lista_ggv_preselecionada")
        ctx.user_data["aguardando"] = None
        ctx.user_data.pop("lista_ggv_preselecionada", None)
        await update.message.reply_text("Interpretando...")
        itens = await _interpretar_lista_arquivo(bytes(conteudo), mime)
        ctx.user_data["lista_itens"] = itens
        ctx.user_data["lista_ggv"] = ggv
        ctx.user_data["lista_endereco"] = None
        ctx.user_data["lista_observacoes"] = None
        ctx.user_data["lista_resumo"] = None
        ctx.user_data.pop("lista_id_edicao", None)
        texto, markup = _renderizar_lista_conferencia(itens, ggv, ctx)
        await update.message.reply_text(texto, parse_mode="HTML", reply_markup=markup)
        return

    caminho = UPLOADS / nome
    caminho.write_bytes(conteudo)
    if TEST_MODE:
        await update.message.reply_text("🧪 MODO TESTE ATIVO — dados não afetam produção.")

    doc_id = registrar(nome, caminho, hash_arquivo, "pendente", "nao_identificado", "")

    if ctx.user_data.get("aguardando") == "foto_entrega_obs":
        ctx.user_data["aguardando"] = "entrega_legenda_inicial"
        atualizar(doc_id, tipo="foto_entrega")
        ctx.user_data["entrega_doc_id_foto"] = doc_id
        await update.message.reply_text("Legenda do arquivo (ex: nota fiscal, caixa avariada):")
        return

    if ctx.user_data.get("aguardando") == "foto_entrega_troca":
        ctx.user_data["aguardando"] = "entrega_legenda_add"
        atualizar(doc_id, tipo="foto_entrega")
        ctx.user_data["entrega_doc_id_foto"] = doc_id
        await update.message.reply_text("Legenda do arquivo (ex: nota fiscal, caixa avariada):")
        return

    if ctx.user_data.get("aguardando") == "recibo_assinado_upload":
        ctx.user_data["aguardando"] = None
        parcela_id = ctx.user_data.pop("recibo_parcela_id", None)
        parcela = _buscar_parcela(parcela_id) if parcela_id else None
        if not parcela:
            await update.message.reply_text("Parcela não encontrada.")
            return
        _, pfm_codigo, valor_parcela, data_parcela, doc_id_recibo_antigo, _, _ = parcela
        atualizar(doc_id, tipo="recibo_assinado")
        with sqlite3.connect(DB_PATH) as con:
            con.execute(
                "UPDATE parcelas_pagamento SET doc_id_recibo_assinado=?, status='assinado' WHERE id=?",
                (doc_id, parcela_id)
            )
        # Sobrescreve o recibo rascunho em 05 Entrega com a versão assinada, mesmo nome de arquivo
        if doc_id_recibo_antigo:
            with sqlite3.connect(DB_PATH) as con:
                row = con.execute("SELECT caminho FROM documentos WHERE id=?", (doc_id_recibo_antigo,)).fetchone()
            if row and row[0]:
                try:
                    shutil.copy2(caminho, row[0])
                except OSError:
                    pass
        pedido = buscar_pedido(pfm_codigo)
        await update.message.reply_text(
            f"✅ Recibo assinado registrado — parcela de R$ {_fmt_brl(valor_parcela)} (#{pfm_codigo}).",
            reply_markup=teclado_parcelas(pfm_codigo) if pedido else None
        )
        return

    await update.message.reply_text(
        "O que é este documento?",
        reply_markup=teclado_tipo_inicial(doc_id)
    )

async def receber_texto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DONO_ID:
        return
    aguardando = ctx.user_data.get("aguardando")
    texto      = update.message.text.strip()

    if not aguardando:
        if _SAUDACOES_RE.match(texto):
            await update.message.reply_text(
                mostrar_boas_vindas(),
                reply_markup=teclado_boas_vindas()
            )
            return
        if _OBRAS_RE.match(texto):
            obras = _listar_obras()
            await update.message.reply_text(
                mostrar_lista_obras(obras),
                reply_markup=teclado_lista_obras(obras)
            )
            return
        m_obra = GGV_CODIGO_RE.match(texto)
        if m_obra:
            codigo = m_obra.group(1).upper()
            obra = buscar_obra(codigo)
            if obra:
                await update.message.reply_text(
                    mostrar_cockpit_obra(obra),
                    reply_markup=teclado_obra(codigo, _pedidos_obra(codigo))
                )
            else:
                await update.message.reply_text(f"Obra {codigo} não encontrada.")
            return
        m = PFM_CODIGO_RE.search(texto)
        if m:
            pfm_codigo = m.group(1).upper()
            pedido = buscar_pedido(pfm_codigo)
            if pedido:
                preparar_visualizacao_pedido(pedido)
                await update.message.reply_text(
                    mostrar_pedido(pedido),
                    reply_markup=teclado_pedido(pedido.doc_id, pfm_codigo, pedido.doc_id_nfe, pedido.doc_id_comprovante, pedido.qtd_fotos_entrega, pedido.obs_entrega, pedido.status, pedido.categoria, pedido.qtd_parcelas)
                )
            else:
                await update.message.reply_text(f"Pedido {pfm_codigo} não encontrado.")
        else:
            await update.message.reply_text(
                mostrar_boas_vindas(),
                reply_markup=teclado_boas_vindas()
            )
        return

    doc_id = ctx.user_data.get("doc_id")
    ggv    = ctx.user_data.get("ggv")

    if aguardando == "condicao_pgto":
        atualizar(doc_id, condicao_pgto=texto)
        ctx.user_data["aguardando"] = None
        texto_resumo, markup = _resumo_gerar(doc_id)
        await update.message.reply_text(texto_resumo, reply_markup=markup, parse_mode="HTML")

    elif aguardando == "data_entrega":
        atualizar(doc_id, data_entrega=texto)
        ctx.user_data["aguardando"] = None
        texto_resumo, markup = _resumo_gerar(doc_id)
        await update.message.reply_text(texto_resumo, reply_markup=markup, parse_mode="HTML")

    elif aguardando == "edit_desconto":
        try:
            v = _parse_brl(re.sub(r"[^\d,.]", "", texto))
        except Exception:
            v = 0.0
        atualizar(doc_id, desconto_rs=f"{v:.2f}")
        ctx.user_data["aguardando"] = None
        texto_resumo, markup = _resumo_gerar(doc_id)
        await update.message.reply_text(texto_resumo, reply_markup=markup, parse_mode="HTML")

    elif aguardando == "obs_entrega_texto":
        obs = texto.strip()
        pfm_codigo = ctx.user_data.pop("entrega_pfm_codigo", None)
        doc_id_foto = ctx.user_data.pop("entrega_doc_id_foto", None)
        legenda_foto = ctx.user_data.pop("entrega_legenda_foto", None)
        ctx.user_data["aguardando"] = None
        if pfm_codigo:
            _salvar_entrega_db(pfm_codigo, obs)
            if doc_id_foto:
                _adicionar_foto_entrega(pfm_codigo, doc_id_foto, legenda_foto)
            texto_ped, markup = _tela_apos_entrega(pfm_codigo)
            await update.message.reply_text(texto_ped or "Entrega registrada.", reply_markup=markup)
        else:
            await update.message.reply_text("Pedido não encontrado.")

    elif aguardando == "edit_obs_entrega_texto":
        obs = texto.strip()
        pfm_codigo = ctx.user_data.pop("entrega_pfm_codigo", None)
        ctx.user_data["aguardando"] = None
        if pfm_codigo:
            _atualizar_obs_entrega(pfm_codigo, obs)
            forn, obs_ent, qtd_fotos = _buscar_estado_entrega(pfm_codigo)
            await update.message.reply_text(
                _texto_gerir_entrega(pfm_codigo, forn, obs_ent, qtd_fotos),
                reply_markup=_teclado_gerir_entrega(pfm_codigo, qtd_fotos)
            )
        else:
            await update.message.reply_text("Pedido não encontrado.")

    elif aguardando == "entrega_legenda_inicial":
        legenda = texto.strip()
        ctx.user_data["entrega_legenda_foto"] = legenda
        ctx.user_data["aguardando"] = None
        pfm_codigo = ctx.user_data.get("entrega_pfm_codigo")
        forn, _, _ = _buscar_estado_entrega(pfm_codigo) if pfm_codigo else (None, None, None)
        await update.message.reply_text(
            _texto_obs_entrega(pfm_codigo, forn),
            reply_markup=_teclado_obs_com_cancelar(com_foto=True)
        )

    elif aguardando == "entrega_legenda_add":
        legenda = texto.strip()
        pfm_codigo = ctx.user_data.pop("entrega_pfm_codigo", None)
        doc_id_foto = ctx.user_data.pop("entrega_doc_id_foto", None)
        ctx.user_data["aguardando"] = None
        if pfm_codigo and doc_id_foto:
            _adicionar_foto_entrega(pfm_codigo, doc_id_foto, legenda)
            forn, obs_ent, qtd_fotos = _buscar_estado_entrega(pfm_codigo)
            await update.message.reply_text(
                _texto_gerir_entrega(pfm_codigo, forn, obs_ent, qtd_fotos),
                reply_markup=_teclado_gerir_entrega(pfm_codigo, qtd_fotos)
            )
        else:
            await update.message.reply_text("Pedido não encontrado.")

    elif aguardando == "recibo_motivo_texto":
        motivo = texto.strip()
        parcela_id = ctx.user_data.pop("recibo_parcela_id", None)
        ctx.user_data["aguardando"] = None
        if parcela_id:
            await update.message.reply_text("Gerando recibo...")
            await _gerar_recibo(ctx, parcela_id, motivo)
        else:
            await update.message.reply_text("Parcela não encontrada.")

    elif aguardando == "edit_contato":
        m_fone = re.search(r'\s+([\d][\d\s\(\)\-\.]{5,})\s*$', texto)
        if m_fone:
            nome_v = texto[:m_fone.start()].strip()
            fone_v = m_fone.group(1).strip()
        else:
            nome_v = texto.strip()
            fone_v = ""
        with sqlite3.connect(DB_PATH) as con:
            row = con.execute("SELECT dados_claude FROM documentos WHERE id=?", (doc_id,)).fetchone()
        if row:
            novos_dados = _substituir_campo(row[0], "Vendedor", nome_v)
            if fone_v:
                novos_dados = _substituir_campo(novos_dados, "Telefone do vendedor", fone_v)
            atualizar(doc_id, dados_claude=novos_dados)
        ctx.user_data["aguardando"] = None
        texto_resumo, markup = _resumo_gerar(doc_id)
        await update.message.reply_text(texto_resumo, reply_markup=markup, parse_mode="HTML")

    elif aguardando in ("edit_fornecedor", "edit_cnpj", "edit_valor", "edit_pix", "edit_itens", "edit_obs"):
        campo_map = {
            "edit_fornecedor": "Fornecedor",
            "edit_cnpj":       "CNPJ/CPF",
            "edit_valor":      "Valor total",
            "edit_pix":        "Chave PIX",
            "edit_obs":        "Observações",
        }
        tipo = ctx.user_data.get("tipo", "orcamento")
        with sqlite3.connect(DB_PATH) as con:
            row = con.execute(
                "SELECT dados_claude, ggv FROM documentos WHERE id=?", (doc_id,)
            ).fetchone()
        if row:
            dados_atuais, ggv_db = row
            if aguardando == "edit_itens":
                # Editar no celular costuma vir com o texto da própria pergunta colado junto
                # (copiar/colar a mensagem inteira em vez de só a edição) — achado real: isso
                # gravou "Novos itens:\nUse o formato..." dentro do campo Itens do documento,
                # junto com o item de exemplo, corrompendo o valor total calculado. Recusar em
                # vez de gravar texto que reconhecidamente não é uma lista de itens.
                texto_lower = texto.lower()
                if any(marca in texto_lower for marca in (
                    "novos itens:", "use o formato para cálculo automático", "itens atuais:"
                )):
                    await update.message.reply_text(
                        "Recebi o texto da minha própria mensagem junto com a edição — costuma "
                        "acontecer copiando e colando pelo celular. Envie só a lista de itens "
                        "nova (sem repetir \"Itens atuais\" nem as instruções)."
                    )
                    return
                novos_dados = _recalcular_itens(_substituir_itens(dados_atuais, texto))
                nome_campo = "Itens"
            else:
                nome_campo = campo_map[aguardando]
                novos_dados = _substituir_campo(dados_atuais, nome_campo, texto)
            atualizar(doc_id, dados_claude=novos_dados)
            ctx.user_data["aguardando"] = None
            texto_resumo, markup = _resumo_gerar(doc_id)
            await update.message.reply_text(texto_resumo, reply_markup=markup, parse_mode="HTML")
        else:
            ctx.user_data["aguardando"] = None
            await update.message.reply_text("Documento não encontrado.")

    elif aguardando == "endereco_entrega":
        atualizar(doc_id, endereco_entrega=texto)
        ctx.user_data["aguardando"] = None
        texto_resumo, markup = _resumo_gerar(doc_id)
        await update.message.reply_text(texto_resumo, reply_markup=markup, parse_mode="HTML")

    elif aguardando == "vencimento_pgto":
        atualizar(doc_id, vencimento_pgto=texto)
        ctx.user_data["aguardando"] = None
        texto_resumo, markup = _resumo_gerar(doc_id)
        await update.message.reply_text(texto_resumo, reply_markup=markup, parse_mode="HTML")

    elif aguardando == "edit_encarregado":
        atualizar(doc_id, encarregado=texto)
        ctx.user_data["aguardando"] = None
        texto_resumo, markup = _resumo_gerar(doc_id)
        await update.message.reply_text(texto_resumo, reply_markup=markup, parse_mode="HTML")

    elif aguardando == "nova_obra_codigo":
        codigo = texto.upper()
        if not GGV_CODIGO_RE.match(codigo):
            await update.message.reply_text("Formato inválido. Use GGV seguido de dois dígitos — ex: GGV04. Tente novamente:")
            return
        criada = criar_obra(codigo)
        ctx.user_data["aguardando"] = None
        if not criada:
            await update.message.reply_text(f"Obra {codigo} já existe.")
        else:
            await update.message.reply_text(f"Obra {codigo} criada. Complete os dados abaixo.")
        obra = buscar_obra(codigo)
        await update.message.reply_text(mostrar_cockpit_obra(obra), reply_markup=teclado_obra(codigo, _pedidos_obra(codigo)))

    elif aguardando and aguardando.startswith("obra_edit_"):
        campo = aguardando[len("obra_edit_"):]
        obra_codigo = ctx.user_data.get("obra_codigo")
        if obra_codigo and campo:
            atualizar_obra(obra_codigo, **{campo: texto})
            ctx.user_data["aguardando"] = None
            obra = buscar_obra(obra_codigo)
            await update.message.reply_text(
                mostrar_cockpit_obra(obra),
                reply_markup=teclado_obra(obra_codigo, _pedidos_obra(obra_codigo))
            )
        else:
            ctx.user_data["aguardando"] = None
            await update.message.reply_text("Contexto perdido. Envie o código da obra novamente.")

    elif aguardando == "lista_conteudo":
        ggv = ctx.user_data.get("lista_ggv_preselecionada")
        ctx.user_data["aguardando"] = None
        ctx.user_data.pop("lista_ggv_preselecionada", None)
        await update.message.reply_text("Interpretando...")
        itens = await _interpretar_lista_texto(texto)
        ctx.user_data["lista_itens"] = itens
        ctx.user_data["lista_ggv"] = ggv
        ctx.user_data["lista_endereco"] = None
        ctx.user_data["lista_observacoes"] = None
        ctx.user_data["lista_resumo"] = None
        ctx.user_data.pop("lista_id_edicao", None)
        texto_tela, markup = _renderizar_lista_conferencia(itens, ggv, ctx)
        await update.message.reply_text(texto_tela, parse_mode="HTML", reply_markup=markup)

    elif aguardando == "lista_reinterpretar_item":
        indice = ctx.user_data.get("lista_item_indice")
        itens = ctx.user_data.get("lista_itens") or []
        ctx.user_data["aguardando"] = None
        ctx.user_data.pop("lista_item_indice", None)
        if not indice or not (1 <= indice <= len(itens)):
            await update.message.reply_text("Contexto perdido. Envie /lista novamente.")
            return
        await update.message.reply_text("Interpretando...")
        novos = await _interpretar_lista_texto(texto)
        novo_item = next((it for it in novos if isinstance(it, dict)), novos[0] if novos else None)
        if novo_item is None:
            await update.message.reply_text(
                "Não consegui interpretar. Tente novamente.",
                reply_markup=_teclado_voltar_item(indice)
            )
            return
        itens[indice - 1] = novo_item
        ctx.user_data["lista_itens"] = itens
        ggv = ctx.user_data.get("lista_ggv")
        texto_tela, markup = _renderizar_lista_conferencia(itens, ggv, ctx)
        await update.message.reply_text(texto_tela, parse_mode="HTML", reply_markup=markup)

    elif aguardando and aguardando.startswith("lista_campo_"):
        campo = aguardando[len("lista_campo_"):]
        indice = ctx.user_data.get("lista_item_indice")
        rascunho = ctx.user_data.get("lista_item_rascunho")
        itens = ctx.user_data.get("lista_itens") or []
        ctx.user_data["aguardando"] = None
        if not indice or rascunho is None or campo not in _CAMPOS_ITEM_LISTA:
            await update.message.reply_text("Contexto perdido. Envie /lista novamente.")
            return
        valor_bruto = texto.strip()
        if campo == "descricao" and valor_bruto in ("", "-"):
            ctx.user_data["aguardando"] = f"lista_campo_{campo}"
            await update.message.reply_text(
                "Descrição não pode ficar em branco. Envie o novo valor:",
                reply_markup=_teclado_voltar_item(indice)
            )
            return
        if campo == "quantidade":
            if valor_bruto == "-":
                valor = None
            else:
                try:
                    valor = float(valor_bruto.replace(",", "."))
                except ValueError:
                    ctx.user_data["aguardando"] = f"lista_campo_{campo}"
                    await update.message.reply_text(
                        "Não entendi a quantidade. Envie só o número (ex: 250 ou 12,5) ou \"-\" pra deixar sem valor.",
                        reply_markup=_teclado_voltar_item(indice)
                    )
                    return
        else:
            valor = None if valor_bruto == "-" else valor_bruto
        rascunho[campo] = valor
        ctx.user_data["lista_item_rascunho"] = rascunho
        item_exibir, pendente = _preparar_tela_item(ctx, indice, itens)
        await update.message.reply_text(
            _texto_tela_item(indice, item_exibir, pendente), parse_mode="HTML",
            reply_markup=_teclado_item_tela(indice, item_exibir, pendente)
        )

    elif aguardando and aguardando.startswith("lista_geral_"):
        campo = aguardando[len("lista_geral_"):]
        ctx.user_data["aguardando"] = None
        if campo not in _CAMPOS_LISTA_GERAL:
            await update.message.reply_text("Contexto perdido. Envie /lista novamente.")
            return
        _, _, chave_estado = _CAMPOS_LISTA_GERAL[campo]
        valor_bruto = texto.strip()
        ctx.user_data[chave_estado] = None if valor_bruto == "-" else valor_bruto
        itens = ctx.user_data.get("lista_itens") or []
        ggv = ctx.user_data.get("lista_ggv")
        texto_tela, markup = _renderizar_lista_conferencia(itens, ggv, ctx)
        await update.message.reply_text(texto_tela, parse_mode="HTML", reply_markup=markup)

    elif aguardando and aguardando.startswith("lista_buscar_nome_"):
        codigo = aguardando[len("lista_buscar_nome_"):]
        ctx.user_data["aguardando"] = None
        filtro = texto.strip()
        listas = listar_listas_obra(DB_PATH, codigo, limite=10, busca_resumo=filtro)
        await update.message.reply_text(
            mostrar_lista_listas_compra(codigo, listas, filtro=filtro),
            reply_markup=teclado_lista_listas_compra(codigo, listas)
        )

async def _cb_ok(query, ctx, partes):
    _, doc_id, tipo, ggv = partes
    atualizar(int(doc_id), status="confirmado")
    if tipo == "orcamento":
        ctx.user_data.update({"doc_id": int(doc_id), "ggv": ggv, "aguardando": None})
        texto, markup = _resumo_gerar(int(doc_id))
        await query.edit_message_text(texto, reply_markup=markup, parse_mode="HTML")
    elif tipo == "comprovante_pix":
        dados_claude = _dados_doc(int(doc_id))
        dados        = parse_comprovante(dados_claude)
        candidatos   = buscar_candidatos_pix(dados["valor_v"], dados["favorecido"], dados["cnpj"])
        await query.edit_message_text(mostrar_comprovante_candidatos(dados, candidatos))
    else:
        emoji, label = TIPOS.get(tipo, ("📄", tipo))
        await query.edit_message_text(f"Confirmado: {label}")


async def _cb_cancelar(query, ctx, partes):
    doc_id_cancelar = int(partes[1])
    if _descartar_documento(doc_id_cancelar):
        await query.edit_message_text("Cancelado. Pode reenviar o arquivo se precisar.")
    else:
        # Mensagem antiga de um documento que já virou pedido — abre o cockpit direto,
        # sem etapa intermediária
        with sqlite3.connect(DB_PATH) as con:
            row = con.execute(
                "SELECT ggv, pfm_numero FROM documentos WHERE id=?", (doc_id_cancelar,)
            ).fetchone()
        pfm_codigo_atual = f"{row[0]}-{row[1]:03d}" if row and row[1] else None
        pedido = buscar_pedido(pfm_codigo_atual) if pfm_codigo_atual else None
        if pedido:
            preparar_visualizacao_pedido(pedido)
            await query.edit_message_text(
                mostrar_pedido(pedido),
                reply_markup=teclado_pedido(pedido.doc_id, pfm_codigo_atual, pedido.doc_id_nfe, pedido.doc_id_comprovante, pedido.qtd_fotos_entrega, pedido.obs_entrega, pedido.status, pedido.categoria, pedido.qtd_parcelas)
            )
        else:
            await query.answer("Esse documento já virou um pedido — não dá mais pra cancelar por aqui.", show_alert=True)


async def _cb_sel_tipo(query, ctx, partes):
    _, doc_id, tipo, ggv = partes
    botoes = [[InlineKeyboardButton(f"{e} {l}", callback_data=f"set_tipo:{doc_id}:{t}:{ggv}")]
              for t, (e, l) in TIPOS.items()]
    await query.edit_message_reply_markup(InlineKeyboardMarkup(botoes))


async def _cb_set_tipo(query, ctx, partes):
    _, doc_id, novo_tipo, ggv = partes
    atualizar(int(doc_id), tipo=novo_tipo)
    with sqlite3.connect(DB_PATH) as con:
        status = con.execute("SELECT status FROM documentos WHERE id=?", (int(doc_id),)).fetchone()[0]
    if status == "confirmado":
        texto, markup = _resumo_gerar(int(doc_id))
        await query.edit_message_text(texto, reply_markup=markup, parse_mode="HTML")
    else:
        texto, markup = _resumo_gerar(int(doc_id))
        await query.edit_message_text(texto, reply_markup=markup, parse_mode="HTML")


async def _cb_sel_tipo_inicial(query, ctx, partes):
    _, doc_id, tipo = partes
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT caminho FROM documentos WHERE id=?", (int(doc_id),)).fetchone()
    if not row:
        await query.edit_message_text("Documento não encontrado.")
        return
    caminho_doc = row[0]

    if tipo == "foto_entrega":
        atualizar(int(doc_id), tipo=tipo)
        pedidos = buscar_pedidos_sem_entrega()
        if not pedidos:
            await query.edit_message_text("Nenhum pedido sem entrega registrada.")
            return
        ctx.user_data["entrega_doc_id_foto"] = int(doc_id)
        await query.edit_message_text(
            _mostrar_pedidos_entrega(pedidos),
            reply_markup=_teclado_pedidos_entrega(pedidos)
        )
        return

    if tipo == "lista_materiais":
        # Mesmo caminho de interpretação do /lista — nunca passa pelo PROMPT de
        # classificação. "Enviar imagem + escolher tipo" e "/lista" têm que produzir o
        # mesmo resultado; dois prompts fazendo a mesma coisa é como o bug da Lição #12
        # (marca confundida com unidade) apareceu num caminho e não no outro.
        atualizar(int(doc_id), tipo=tipo)
        mime_inf_lista = "application/pdf" if caminho_doc.lower().endswith(".pdf") else "image/jpeg"
        conteudo_lista = Path(caminho_doc).read_bytes()
        await query.edit_message_text("Interpretando...")
        itens = await _interpretar_lista_arquivo(conteudo_lista, mime_inf_lista)
        ctx.user_data["lista_itens"] = itens
        ctx.user_data["lista_ggv"] = None
        ctx.user_data["lista_endereco"] = None
        ctx.user_data["lista_observacoes"] = None
        ctx.user_data["lista_resumo"] = None
        ctx.user_data.pop("lista_id_edicao", None)
        texto_tela, markup = _renderizar_lista_conferencia(itens, None, ctx)
        await query.edit_message_text(texto_tela, parse_mode="HTML", reply_markup=markup)
        return

    mime_inf = "application/pdf" if caminho_doc.lower().endswith(".pdf") else "image/jpeg"
    tipo_conteudo = "document" if mime_inf == "application/pdf" else "image"
    conteudo = Path(caminho_doc).read_bytes()
    dados_b64 = base64.standard_b64encode(conteudo).decode()
    await query.edit_message_text("Analisando...")
    resposta = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {"type": tipo_conteudo, "source": {"type": "base64", "media_type": mime_inf, "data": dados_b64}},
                {"type": "text", "text": PROMPT}
            ]
        }]
    )
    _, ggv, corpo = parse_resposta(resposta.content[0].text)
    atualizar(int(doc_id), tipo=tipo, ggv=ggv, dados_claude=corpo)
    if tipo == "orcamento":
        _autopreencher_endereco(int(doc_id), ggv)
    emoji, label_tipo = TIPOS.get(tipo, ("📄", tipo))
    label_ggv = ggv if ggv != "nao_identificado" else "Obra não identificada"
    if tipo == "comprovante_pix":
        dados = parse_comprovante(corpo)
        ident = dados["id_transacao"] if dados["id_transacao"] != "A PREENCHER" else None
        ja_pago = None
        if ident and not TEST_MODE:
            with sqlite3.connect(DB_PATH) as con:
                ja_pago = con.execute(
                    "SELECT pfm_codigo FROM lancamentos "
                    "WHERE identificador_comprovante=? AND status='pago' LIMIT 1",
                    (ident,)
                ).fetchone()
        if ja_pago:
            await query.edit_message_text(
                f"Comprovante já registrado.\n\n"
                f"Pedido #{ja_pago[0]} — 🟢 Pago\n\n"
                "Cada comprovante pode ser usado apenas uma vez."
            )
        else:
            candidatos = buscar_candidatos_pix(dados["valor_v"], dados["favorecido"], dados["cnpj"])
            texto_resultado = mostrar_comprovante_candidatos(dados, candidatos)
            if not candidatos:
                _descartar_documento(int(doc_id))
                texto_resultado += "\n\nArquivo descartado — pode reenviar depois de corrigir o pedido."
                await query.edit_message_text(texto_resultado)
            else:
                await query.edit_message_text(
                    texto_resultado,
                    reply_markup=teclado_candidatos_pix(int(doc_id), candidatos)
                )
    elif tipo == "nota_fiscal":
        dados_nfe = parse_nfe(corpo)
        candidatos = buscar_candidatos_nfe(dados_nfe["cnpj"], dados_nfe["valor_v"], DB_PATH)
        if not candidatos:
            _descartar_documento(int(doc_id))
            await query.edit_message_text(
                mostrar_nfe(dados_nfe, candidatos) +
                "\n\nArquivo descartado — pode reenviar depois de corrigir o pedido."
            )
        else:
            await query.edit_message_text(
                mostrar_nfe(dados_nfe, candidatos),
                reply_markup=teclado_candidatos_nfe(int(doc_id), candidatos)
            )
    elif tipo == "orcamento":
        texto, markup = _resumo_gerar(int(doc_id))
        await query.edit_message_text(texto, reply_markup=markup, parse_mode="HTML")
    else:
        await query.edit_message_text(
            f"{label_tipo}\n\n{corpo}\n\nConfirmar?",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Confirmar", callback_data=f"ok:{doc_id}:{tipo}:{ggv}"),
                InlineKeyboardButton("← Voltar",    callback_data=f"cancelar:{doc_id}"),
            ]])
        )


async def _cb_pix_confirmar(query, ctx, partes):
    _, doc_id_comp, pfm_codigo = partes
    with sqlite3.connect(DB_PATH) as con:
        comp = con.execute(
            "SELECT dados_claude FROM documentos WHERE id=?", (int(doc_id_comp),)
        ).fetchone()
        lanc = con.execute(
            "SELECT fornecedor, valor, status FROM lancamentos WHERE pfm_codigo=?",
            (pfm_codigo,)
        ).fetchone()
    if not comp or not lanc:
        await query.edit_message_text("Dados não encontrados.")
        return
    dados_comp   = parse_comprovante(comp[0])
    forn, valor_lanc, status_lanc = lanc
    status_label = {"a_pagar": "🟡 Aguardando pagamento", "pago": "🟢 Pago"}.get(status_lanc, status_lanc)
    valor_lanc_fmt = f"R$ {_fmt_brl(valor_lanc)}" if valor_lanc else "—"
    texto = (
        f"Confirmar pagamento?\n\n"
        f"Comprovante:  R$ {dados_comp['valor_fmt']}  {dados_comp['data']}\n"
        f"Pedido:       #{pfm_codigo} — {forn}\n"
        f"Valor:        {valor_lanc_fmt}\n"
        f"Status:       {status_label}"
    )
    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar pagamento",
                             callback_data=f"pix_pagar:{doc_id_comp}:{pfm_codigo}")],
        [InlineKeyboardButton("↩️ Voltar",
                             callback_data="pix_cancelar")],
    ]))


async def _cb_pix_pagar(query, ctx, partes):
    _, doc_id_comp, pfm_codigo = partes
    with sqlite3.connect(DB_PATH) as con:
        comp = con.execute(
            "SELECT dados_claude, caminho FROM documentos WHERE id=?", (int(doc_id_comp),)
        ).fetchone()
        lanc = con.execute(
            "SELECT valor, categoria, doc_id FROM lancamentos WHERE pfm_codigo=?", (pfm_codigo,)
        ).fetchone()
    if not comp or not lanc:
        await query.edit_message_text("Dados não encontrados.")
        return
    dados_comp = parse_comprovante(comp[0])
    caminho_comp = comp[1]
    valor_total, categoria_lanc, doc_id_orcamento = lanc
    ident_comp = dados_comp["id_transacao"] if dados_comp["id_transacao"] != "A PREENCHER" else None
    ja_usado = None
    if ident_comp and not TEST_MODE:
        with sqlite3.connect(DB_PATH) as con:
            ja_usado = con.execute(
                "SELECT pfm_codigo FROM parcelas_pagamento WHERE identificador_comprovante=? LIMIT 1",
                (ident_comp,)
            ).fetchone()
    if ja_usado:
        await query.edit_message_text(
            f"Comprovante já registrado no Pedido #{ja_usado[0]}.\n"
            "Cada comprovante pode ser usado apenas uma vez."
        )
        return
    _MESES = {"janeiro":"01","fevereiro":"02","março":"03","abril":"04",
              "maio":"05","junho":"06","julho":"07","agosto":"08",
              "setembro":"09","outubro":"10","novembro":"11","dezembro":"12"}
    _data_raw = dados_comp["data"] if dados_comp["data"] != "A PREENCHER" \
                else datetime.now().strftime("%d/%m/%Y")
    data_pgto = _data_raw
    for nome, num in _MESES.items():
        if nome in _data_raw.lower():
            data_pgto = re.sub(nome, num, _data_raw, flags=re.IGNORECASE)
            break

    valor_parcela = dados_comp["valor_v"] or 0.0
    parcela_id = _registrar_parcela(pfm_codigo, valor_parcela, data_pgto, int(doc_id_comp), ident_comp)
    _arquivar_doc_financeiro(pfm_codigo, f"comprovante-parcela{parcela_id}", caminho_comp, data_pgto)

    quitado = _recalcular_status_pagamento(pfm_codigo, valor_total, data_pgto)
    total_pago = _total_pago(pfm_codigo)

    if quitado and categoria_lanc in CATEGORIAS_SEM_NFE_OBRIGATORIA:
        # Taxa/imposto/serviço público: a fatura já enviada é a "terceira via" — não há NF-e separada
        with sqlite3.connect(DB_PATH) as con:
            row_fatura = con.execute("SELECT caminho FROM documentos WHERE id=?", (doc_id_orcamento,)).fetchone()
        _arquivar_doc_financeiro(pfm_codigo, "fatura", row_fatura[0] if row_fatura else None, data_pgto)

    valor_parcela_fmt = f"R$ {_fmt_brl(valor_parcela)}"
    botoes = []
    if categoria_lanc not in CATEGORIAS_SEM_NFE_OBRIGATORIA:
        botoes.append([InlineKeyboardButton(
            "📄 Gerar recibo desta parcela", callback_data=f"recibo_parcela_iniciar:{parcela_id}"
        )])
    if quitado:
        texto = f"🟢 Pedido #{pfm_codigo} — quitado. Parcela: {valor_parcela_fmt}."
        if categoria_lanc not in CATEGORIAS_SEM_NFE_OBRIGATORIA:
            texto += "\n\nEnvie a NF-e para fechar este pedido (se aplicável)."
    else:
        faltam = valor_total - total_pago
        texto = (
            f"🟡 Pedido #{pfm_codigo} — parcela registrada: {valor_parcela_fmt}.\n"
            f"Total pago: R$ {_fmt_brl(total_pago)} de R$ {_fmt_brl(valor_total)} — "
            f"faltam R$ {_fmt_brl(faltam)}."
        )
    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(botoes) if botoes else None)


async def _cb_pix_cancelar(query, ctx, partes):
    # Com doc_id (botão "Nenhum destes" da lista de candidatos): descarta o documento —
    # sem isso o arquivo ficava preso pra sempre como `recebido`, com o hash bloqueando
    # reenvio (mesmo bug já corrigido no fluxo de NF-e em 2026-07-06, caso real: fatura
    # Copel identificada errado como comprovante). Sem doc_id (botão "↩️ Voltar" da tela
    # de confirmação de pagamento): só cancela a conversa, nunca apaga nada.
    if len(partes) > 1:
        _descartar_documento(int(partes[1]))
        await query.edit_message_text(
            "Arquivo descartado — pode reenviar se precisar."
        )
    else:
        await query.edit_message_text("Cancelado.")


async def _cb_sel_ggv(query, ctx, partes):
    _, doc_id, tipo, ggv = partes
    botoes = [[InlineKeyboardButton(g, callback_data=f"set_ggv:{doc_id}:{tipo}:{g}")] for g in GGVS]
    botoes.append([InlineKeyboardButton("❓ Não identificado",
                                        callback_data=f"set_ggv:{doc_id}:{tipo}:nao_identificado")])
    botoes.append([InlineKeyboardButton("◀️ Voltar",
                                        callback_data=f"voltar_edit:{doc_id}:{tipo}:{ggv}")])
    await query.edit_message_reply_markup(InlineKeyboardMarkup(botoes))


async def _cb_set_ggv(query, ctx, partes):
    _, doc_id, tipo, novo_ggv = partes
    atualizar(int(doc_id), ggv=novo_ggv)
    if tipo == "orcamento":
        _autopreencher_endereco(int(doc_id), novo_ggv)
    texto, markup = _resumo_gerar(int(doc_id))
    await query.edit_message_text(texto, reply_markup=markup, parse_mode="HTML")


async def _cb_pgto(query, ctx, partes):
    _, doc_id, ggv, escolha = partes
    if escolha == "outro":
        ctx.user_data.update({"doc_id": int(doc_id), "ggv": ggv, "aguardando": "condicao_pgto"})
        await query.edit_message_text("Condição de pagamento:")
        return
    label_pgto = CONDICOES.get(escolha, escolha)
    atualizar(int(doc_id), condicao_pgto=label_pgto)
    ctx.user_data.update({"doc_id": int(doc_id), "ggv": ggv, "aguardando": None})
    texto, markup = _resumo_gerar(int(doc_id))
    await query.edit_message_text(texto, reply_markup=markup, parse_mode="HTML")


async def _cb_endsel(query, ctx, partes):
    """Único handler de escolha de endereço — Pedido de Compra e Lista de Compras
    convergem aqui (Dennis, 2026-07-05). Só a gravação final diverge por `destino`: 'doc'
    grava direto em documentos (via doc_id embutido em `param`) e reabre o resumo do
    pedido; 'lista' grava em ctx.user_data (a Lista ainda não existe no banco até
    "Gerar") e reabre a Tela de Conferência. Mesma tolerância já aceita na Camada 2/3 da
    Lista de Compras: computação/opções compartilhadas, gravação final por domínio."""
    _, destino, param, escolha = partes
    if escolha == "outro":
        if destino == "doc":
            doc_id, ggv = param.split("|", 1)
            ctx.user_data.update({"doc_id": int(doc_id), "ggv": ggv, "aguardando": "endereco_entrega"})
            await query.edit_message_text("Endereço de entrega:")
        else:
            ctx.user_data["aguardando"] = "lista_geral_endereco"
            await query.edit_message_text(
                "Endereço de entrega\n\nDigite o novo endereço de entrega.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Voltar", callback_data="lc_voltar")]])
            )
        return
    endereco = _resolver_endereco(escolha)
    if destino == "doc":
        doc_id, _ggv = param.split("|", 1)
        atualizar(int(doc_id), endereco_entrega=endereco)
        texto, markup = _resumo_gerar(int(doc_id))
        await query.edit_message_text(texto, reply_markup=markup, parse_mode="HTML")
    else:
        ctx.user_data["lista_endereco"] = endereco
        itens = ctx.user_data.get("lista_itens") or []
        ggv = ctx.user_data.get("lista_ggv")
        texto, markup = _renderizar_lista_conferencia(itens, ggv, ctx)
        await query.edit_message_text(texto, parse_mode="HTML", reply_markup=markup)


async def _cb_sel_edit(query, ctx, partes):
    _, doc_id, tipo, ggv = partes
    # Categoria só é editável depois que o pedido existe (lancamentos.categoria é gravada na
    # geração); antes disso a tela de categoria aparece no próprio "Gerar Pedido de Compra"
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT pfm_numero FROM documentos WHERE id=?", (int(doc_id),)).fetchone()
    pedido_gerado = bool(row and row[0])
    botoes = [
        [InlineKeyboardButton("👤 Fornecedor",    callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:fornecedor")],
        [InlineKeyboardButton("🔢 CNPJ/CPF",      callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:cnpj")],
        [InlineKeyboardButton("💲 Valor total",   callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:valor")],
        [InlineKeyboardButton("🔑 Chave PIX",     callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:pix")],
        [InlineKeyboardButton("📦 Itens",         callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:itens")],
        [InlineKeyboardButton("🏷️ Desconto",     callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:desconto")],
        [InlineKeyboardButton("💰 Condição pgto", callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:pgto")],
        [InlineKeyboardButton("📅 Data entrega",  callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:data")],
        [InlineKeyboardButton("📍 Endereço",      callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:endereco")],
        [InlineKeyboardButton("📅 Vencimento pgto", callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:vencimento")],
        [InlineKeyboardButton("👷 Encarregado",     callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:encarregado")],
        [InlineKeyboardButton("📞 Contato vendedor", callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:contato")],
        [InlineKeyboardButton("📝 Observações",     callback_data=f"edit_campo:{doc_id}:{tipo}:{ggv}:obs")],
        [InlineKeyboardButton("🏗 GGV",             callback_data=f"sel_ggv:{doc_id}:{tipo}:{ggv}")],
        [InlineKeyboardButton("📋 Tipo doc.",      callback_data=f"sel_tipo:{doc_id}:{tipo}:{ggv}")],
        [InlineKeyboardButton("◀️ Voltar",         callback_data=f"voltar_edit:{doc_id}:{tipo}:{ggv}")],
    ]
    if pedido_gerado:
        botoes.insert(-1, [InlineKeyboardButton(
            "🏷 Categoria da compra", callback_data=f"cat_edit:{doc_id}:{ggv}"
        )])
    await query.edit_message_reply_markup(InlineKeyboardMarkup(botoes))


async def _cb_edit_campo(query, ctx, partes):
    _, doc_id, tipo, ggv, campo = partes
    ctx.user_data.update({"doc_id": int(doc_id), "ggv": ggv, "tipo": tipo})

    if campo == "pgto":
        ctx.user_data["aguardando"] = None
        await query.edit_message_text(
            "Condição de pagamento:",
            reply_markup=teclado_condicao(doc_id, tipo, ggv)
        )
    elif campo == "endereco":
        ctx.user_data["aguardando"] = None
        await query.edit_message_text(
            "Endereço de entrega:",
            reply_markup=teclado_endereco(doc_id, tipo, ggv)
        )
    elif campo == "vencimento":
        ctx.user_data["aguardando"] = "vencimento_pgto"
        with sqlite3.connect(DB_PATH) as con:
            row = con.execute("SELECT vencimento_pgto FROM documentos WHERE id=?", (int(doc_id),)).fetchone()
        atual = row[0] if row and row[0] else "Não informado"
        await query.edit_message_text(
            f"Atual: {atual}\n\nNovo vencimento (ex: Parcela única até 15/07/2026):"
        )
    elif campo == "encarregado":
        ctx.user_data["aguardando"] = "edit_encarregado"
        with sqlite3.connect(DB_PATH) as con:
            row = con.execute("SELECT encarregado FROM documentos WHERE id=?", (int(doc_id),)).fetchone()
        atual = (row[0] if row and row[0] else None) or buscar_obra(ggv).get("encarregado_nome", "Não definido")
        await query.edit_message_text(
            f"Atual: {atual}\n\nNovo encarregado:"
        )
    elif campo == "contato":
        ctx.user_data["aguardando"] = "edit_contato"
        with sqlite3.connect(DB_PATH) as con:
            row = con.execute("SELECT dados_claude FROM documentos WHERE id=?", (int(doc_id),)).fetchone()
        dados_atuais = row[0] if row else ""
        nome_v = _campo(dados_atuais, "Vendedor")
        fone_v = _campo(dados_atuais, "Telefone do vendedor")
        if nome_v == "A PREENCHER": nome_v = "Não informado"
        if fone_v == "A PREENCHER": fone_v = ""
        atual = f"{nome_v}  {fone_v}".strip() if fone_v else nome_v
        await query.edit_message_text(
            f"Atual: {atual}\n\nNome e telefone do vendedor (ex: Flávio 42 99912-7781):"
        )
    elif campo == "itens":
        ctx.user_data["aguardando"] = "edit_itens"
        with sqlite3.connect(DB_PATH) as con:
            row = con.execute("SELECT dados_claude FROM documentos WHERE id=?", (int(doc_id),)).fetchone()
        bloco = _bloco_itens(row[0] if row else "")
        await query.edit_message_text(
            f"Itens atuais:\n\n{bloco}\n\n"
            "Novos itens:\n"
            "Use o formato para cálculo automático:\n"
            "1. Descrição (qtde UN) — R$ valor_total\n"
            "Ex: 1. Cimento 50kg (10 sc) — R$ 350,00"
        )
    else:
        aguardando_campo = "data_entrega" if campo == "data" else f"edit_{campo}"
        ctx.user_data["aguardando"] = aguardando_campo
        labels = {
            "fornecedor": "nome do fornecedor",
            "cnpj":       "CNPJ ou CPF",
            "valor":      "valor total (ex: R$ 1.500,00)",
            "pix":        "chave PIX",
            "desconto":   "valor do desconto em R$ (ex: 80 ou 80,00) — ou 0 para remover",
            "data":       "data de entrega (ex: 01/08/2026, 7 dias úteis, A combinar)",
            "obs":        "observação",
        }
        campo_doc = {
            "fornecedor": "Fornecedor",
            "cnpj":       "CNPJ/CPF",
            "valor":      "Valor total",
            "pix":        "Chave PIX",
        }
        with sqlite3.connect(DB_PATH) as con:
            row = con.execute(
                "SELECT dados_claude, desconto_rs, data_entrega FROM documentos WHERE id=?", (int(doc_id),)
            ).fetchone()
        dados_atuais, desconto_atual, data_atual = row if row else ("", None, None)
        if campo == "desconto":
            atual = f"R$ {_fmt_brl(_parse_brl(re.sub(r'[^\d,.]', '', str(desconto_atual))))}" if desconto_atual else "Não informado"
        elif campo == "data":
            atual = data_atual or "Não informada"
        elif campo == "obs":
            atual = _obs(dados_atuais) or "Não informada"
        else:
            atual = _campo(dados_atuais, campo_doc.get(campo, campo))
        await query.edit_message_text(
            f"Atual: {atual}\n\nNovo valor:"
        )


async def _cb_voltar_edit(query, ctx, partes):
    _, doc_id, tipo, ggv = partes
    texto, markup = _resumo_gerar(int(doc_id))
    await query.edit_message_text(texto, reply_markup=markup, parse_mode="HTML")


async def _cb_ver_itens(query, ctx, partes):
    _, doc_id, tipo, ggv = partes
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT dados_claude FROM documentos WHERE id=?", (int(doc_id),)).fetchone()
    bloco = _bloco_itens(row[0] if row else "")
    await query.edit_message_text(
        bloco,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Voltar ao resumo", callback_data=f"voltar_edit:{doc_id}:{tipo}:{ggv}")]
        ])
    )


async def _cb_pfm(query, ctx, partes):
    _, doc_id, ggv = partes
    pfm_codigo_revisao = ctx.user_data.get("modo_revisao")
    if pfm_codigo_revisao:
        await _executar_revisao_pfm(query, ctx, int(doc_id), pfm_codigo_revisao)
    else:
        atualizar(int(doc_id), status="confirmado")
        ramo = _campo(_dados_doc(int(doc_id)), "Ramo de atividade")
        cat  = sugerir_categoria(ramo)
        await query.edit_message_text(
            _tela_categoria(cat, ramo),
            reply_markup=_teclado_categoria(int(doc_id), ggv, cat)
        )


async def _cb_cat_confirmar(query, ctx, partes):
    _, doc_id, ggv, cat_val = partes
    await _executar_gerar_pfm(query, ctx, int(doc_id), ggv, CategoriaLancamento(cat_val))


async def _cb_cat_corrigir(query, ctx, partes):
    _, doc_id, ggv = partes
    await query.edit_message_text(
        "Selecione a categoria:",
        reply_markup=_teclado_selecao_categorias(int(doc_id), ggv)
    )


async def _cb_cat_sel(query, ctx, partes):
    _, doc_id, ggv, cat_val = partes
    await _executar_gerar_pfm(query, ctx, int(doc_id), ggv, CategoriaLancamento(cat_val))


async def _cb_cat_edit(query, ctx, partes):
    _, doc_id, ggv = partes
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT pfm_codigo, categoria FROM lancamentos WHERE doc_id=?", (int(doc_id),)
        ).fetchone()
    if not row:
        await query.answer("Pedido ainda não gerado — a categoria é escolhida ao gerar.", show_alert=True)
        return
    atual = CategoriaLancamento(row[1]).label() if row[1] else "não definida"
    await query.edit_message_text(
        f"#{row[0]} — categoria atual: {atual}\n\nSelecione a nova categoria:",
        reply_markup=_teclado_selecao_categorias(int(doc_id), ggv, acao="cat_upd")
    )


async def _cb_cat_upd(query, ctx, partes):
    _, doc_id, ggv, cat_val = partes
    cat = CategoriaLancamento(cat_val)
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT pfm_codigo FROM lancamentos WHERE doc_id=?", (int(doc_id),)
        ).fetchone()
        if not row:
            await query.edit_message_text("Pedido não encontrado.")
            return
        # Só reclassifica — nunca toca status, valor, pagamento ou NF-e
        con.execute(
            "UPDATE lancamentos SET categoria=? WHERE doc_id=?", (cat.value, int(doc_id))
        )
    extra = ""
    if cat.value in CATEGORIAS_SEM_NFE_OBRIGATORIA:
        extra = "\nCategoria dispensa NF-e — a fatura vale como fechamento."
    await query.edit_message_text(
        f"#{row[0]} reclassificado: {cat.label()}.{extra}"
    )


async def _cb_pfm_revisar(query, ctx, partes):
    _, doc_id, pfm_codigo = partes
    ctx.user_data["doc_id"]       = int(doc_id)
    ctx.user_data["tipo"]         = "orcamento"
    ctx.user_data["modo_revisao"] = pfm_codigo
    texto_resumo, markup = _resumo_gerar(int(doc_id))
    try:
        await query.edit_message_text(texto_resumo, reply_markup=markup, parse_mode="HTML")
    except Exception:
        await query.answer("Tela de revisão já está aberta.")


async def _cb_pfm_ver(query, ctx, partes):
    _, doc_id, pfm_codigo = partes
    await query.answer()
    html      = _gerar_html_pc(int(doc_id))
    pdf_bytes = await _html_para_pdf(html)
    await ctx.bot.send_document(
        chat_id=DONO_ID,
        document=pdf_bytes,
        filename=f"{pfm_codigo}.pdf",
        caption=f"📄 {pfm_codigo}"
    )


async def _cb_pfm_orc(query, ctx, partes):
    _, doc_id, pfm_codigo = partes
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT caminho FROM documentos WHERE id=?", (int(doc_id),)).fetchone()
    caminho = row[0] if row else None
    if not caminho or not Path(caminho).exists():
        await query.answer("Orçamento original não encontrado.", show_alert=True)
        return
    path = Path(caminho)
    await query.answer()
    dados = path.read_bytes()
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg", ".png", ".webp"):
        await ctx.bot.send_photo(chat_id=query.message.chat_id, photo=dados)
    else:
        await ctx.bot.send_document(chat_id=query.message.chat_id, document=dados, filename=path.name)


async def _cb_pfm_nfe(query, ctx, partes):
    _, doc_id_arquivo, pfm_codigo = partes
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT caminho FROM documentos WHERE id=?", (int(doc_id_arquivo),)).fetchone()
    caminho = row[0] if row else None
    label = {"pfm_nfe": "NF-e", "pfm_comp": "comprovante", "pfm_recibo": "recibo"}.get(acao, acao)
    if not caminho or not Path(caminho).exists():
        await query.answer(f"Arquivo de {label} não encontrado.", show_alert=True)
        return
    path = Path(caminho)
    await query.answer()
    dados = path.read_bytes()
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg", ".png", ".webp"):
        await ctx.bot.send_photo(chat_id=query.message.chat_id, photo=dados)
    else:
        await ctx.bot.send_document(chat_id=query.message.chat_id, document=dados, filename=path.name)


async def _cb_pfm_entregue(query, ctx, partes):
    _, doc_id, pfm_codigo = partes
    ctx.user_data["entrega_pfm_codigo"] = pfm_codigo
    ctx.user_data["entrega_doc_id_foto"] = None
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT fornecedor FROM lancamentos WHERE pfm_codigo=?", (pfm_codigo,)).fetchone()
    forn = row[0] if row else pfm_codigo
    await query.edit_message_text(
        _texto_obs_entrega(pfm_codigo, forn),
        reply_markup=_teclado_obs_com_cancelar()
    )


async def _cb_entrega_sel(query, ctx, partes):
    _, pfm_codigo = partes
    ctx.user_data["entrega_pfm_codigo"] = pfm_codigo
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute("SELECT fornecedor FROM lancamentos WHERE pfm_codigo=?", (pfm_codigo,)).fetchone()
    forn = row[0] if row else pfm_codigo
    await query.edit_message_text(
        _texto_obs_entrega(pfm_codigo, forn),
        reply_markup=_teclado_obs_com_cancelar()
    )


async def _cb_entrega_obs(query, ctx, partes):
    _, chave = partes
    OBS_MAP = {
        "completa":  "Entrega completa",
        "parcial":   "Entrega parcial — aguardando restante",
        "avaria":    "Material com avaria",
        "diferente": "Produto diferente do pedido",
    }
    if chave == "outro":
        ctx.user_data["aguardando"] = "obs_entrega_texto"
        await query.edit_message_text("Descreva a observação:")
        return
    obs = OBS_MAP.get(chave, chave)
    pfm_codigo = ctx.user_data.pop("entrega_pfm_codigo", None)
    doc_id_foto = ctx.user_data.pop("entrega_doc_id_foto", None)
    legenda_foto = ctx.user_data.pop("entrega_legenda_foto", None)
    if not pfm_codigo:
        await query.answer("Pedido não encontrado. Tente novamente.", show_alert=True)
        return
    _salvar_entrega_db(pfm_codigo, obs)
    if doc_id_foto:
        _adicionar_foto_entrega(pfm_codigo, doc_id_foto, legenda_foto)
    texto, markup = _tela_apos_entrega(pfm_codigo)
    if texto:
        await query.edit_message_text(texto, reply_markup=markup)
    else:
        await query.edit_message_text("Entrega registrada.")


async def _cb_entrega_cancelar(query, ctx, partes):
    ctx.user_data.pop("entrega_pfm_codigo", None)
    ctx.user_data.pop("entrega_doc_id_foto", None)
    ctx.user_data.pop("entrega_legenda_foto", None)
    await query.edit_message_text(
        mostrar_boas_vindas(),
        reply_markup=teclado_boas_vindas()
    )


async def _cb_entrega_foto_primeiro(query, ctx, partes):
    ctx.user_data["aguardando"] = "foto_entrega_obs"
    await query.edit_message_text("Envie a foto ou documento da entrega:")


async def _cb_entrega_editar(query, ctx, partes):
    pfm_codigo = partes[1]
    forn, obs_ent, qtd_fotos = _buscar_estado_entrega(pfm_codigo)
    await query.edit_message_text(
        _texto_gerir_entrega(pfm_codigo, forn, obs_ent, qtd_fotos),
        reply_markup=_teclado_gerir_entrega(pfm_codigo, qtd_fotos)
    )


async def _cb_entrega_mudar_obs(query, ctx, partes):
    pfm_codigo = partes[1]
    ctx.user_data["entrega_pfm_codigo"] = pfm_codigo
    _, obs_atual, _ = _buscar_estado_entrega(pfm_codigo)
    await query.edit_message_text(
        f"#{pfm_codigo} — Mudar observação\n\nAtual: {obs_atual or '—'}",
        reply_markup=_teclado_mudar_obs(pfm_codigo)
    )


async def _cb_entrega_editobs(query, ctx, partes):
    chave = partes[1]
    pfm_codigo = ctx.user_data.get("entrega_pfm_codigo")
    if not pfm_codigo:
        await query.answer("Sessão expirada. Abra o pedido novamente.", show_alert=True)
        return
    OBS_MAP_EDIT = {
        "completa":  "Entrega completa",
        "parcial":   "Entrega parcial — aguardando restante",
        "avaria":    "Material com avaria",
        "diferente": "Produto diferente do pedido",
    }
    if chave == "outro":
        ctx.user_data["aguardando"] = "edit_obs_entrega_texto"
        await query.edit_message_text("Descreva a observação:")
        return
    obs = OBS_MAP_EDIT.get(chave, chave)
    _atualizar_obs_entrega(pfm_codigo, obs)
    forn, obs_ent, qtd_fotos = _buscar_estado_entrega(pfm_codigo)
    await query.edit_message_text(
        _texto_gerir_entrega(pfm_codigo, forn, obs_ent, qtd_fotos),
        reply_markup=_teclado_gerir_entrega(pfm_codigo, qtd_fotos)
    )


async def _cb_entrega_trocar_foto(query, ctx, partes):
    pfm_codigo = partes[1]
    ctx.user_data["aguardando"] = "foto_entrega_troca"
    ctx.user_data["entrega_pfm_codigo"] = pfm_codigo
    await query.edit_message_text("Envie a foto ou documento da entrega:")


async def _cb_entrega_ver_fotos(query, ctx, partes):
    pfm_codigo = partes[1]
    fotos = _listar_fotos_entrega(pfm_codigo)
    if not fotos:
        await query.answer("Nenhuma foto registrada.", show_alert=True)
        return
    botoes = []
    for foto_id, _doc_id_foto, legenda, caminho in fotos:
        rotulo = (legenda or "Sem legenda")[:40]
        icone = _icone_arquivo_entrega(caminho)
        botoes.append([InlineKeyboardButton(f"{icone} {rotulo}", callback_data=f"entrega_foto_ver:{foto_id}:{pfm_codigo}")])
    botoes.append([InlineKeyboardButton("← Voltar", callback_data=f"entrega_editar:{pfm_codigo}")])
    await query.edit_message_text(
        f"#{pfm_codigo} — Arquivos da entrega ({len(fotos)})",
        reply_markup=InlineKeyboardMarkup(botoes)
    )


async def _cb_entrega_foto_ver(query, ctx, partes):
    _, foto_id, pfm_codigo = partes
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT ef.legenda, d.caminho FROM entrega_fotos ef "
            "JOIN documentos d ON d.id = ef.doc_id WHERE ef.id=?",
            (int(foto_id),)
        ).fetchone()
    if not row or not row[1] or not Path(row[1]).exists():
        await query.answer("Foto não encontrada.", show_alert=True)
        return
    legenda, caminho = row
    await query.answer()
    path = Path(caminho)
    dados = path.read_bytes()
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg", ".png", ".webp"):
        await ctx.bot.send_photo(chat_id=query.message.chat_id, photo=dados, caption=legenda or None)
    else:
        await ctx.bot.send_document(chat_id=query.message.chat_id, document=dados, filename=path.name, caption=legenda or None)


async def _cb_entrega_remover_foto(query, ctx, partes):
    pfm_codigo = partes[1]
    fotos = _listar_fotos_entrega(pfm_codigo)
    if not fotos:
        await query.answer("Nenhuma foto registrada.", show_alert=True)
        return
    botoes = []
    for foto_id, _doc_id_foto, legenda, _caminho in fotos:
        rotulo = (legenda or "Sem legenda")[:40]
        botoes.append([InlineKeyboardButton(f"🗑 {rotulo}", callback_data=f"entrega_foto_apagar:{foto_id}:{pfm_codigo}")])
    botoes.append([InlineKeyboardButton("← Voltar", callback_data=f"entrega_editar:{pfm_codigo}")])
    await query.edit_message_text(
        f"#{pfm_codigo} — Remover qual arquivo?",
        reply_markup=InlineKeyboardMarkup(botoes)
    )


async def _cb_entrega_foto_apagar(query, ctx, partes):
    _, foto_id, pfm_codigo = partes
    _apagar_foto_entrega(int(foto_id))
    forn, obs_ent, qtd_fotos = _buscar_estado_entrega(pfm_codigo)
    await query.edit_message_text(
        _texto_gerir_entrega(pfm_codigo, forn, obs_ent, qtd_fotos),
        reply_markup=_teclado_gerir_entrega(pfm_codigo, qtd_fotos)
    )


async def _cb_entrega_apagar(query, ctx, partes):
    pfm_codigo = partes[1]
    _apagar_entrega_db(pfm_codigo)
    texto, markup = _tela_apos_entrega(pfm_codigo)
    if texto:
        await query.edit_message_text(texto, reply_markup=markup)
    else:
        await query.edit_message_text("Entrega apagada.")


async def _cb_entrega_voltar(query, ctx, partes):
    pfm_codigo = partes[1]
    texto, markup = _tela_apos_entrega(pfm_codigo)
    if texto:
        await query.edit_message_text(texto, reply_markup=markup)
    else:
        await query.edit_message_text("Pedido não encontrado.")


async def _cb_nfe_confirmar(query, ctx, partes):
    _, doc_id_nfe, pfm_codigo = partes
    ok = vincular_nfe(pfm_codigo, int(doc_id_nfe), DB_PATH)
    if ok:
        with sqlite3.connect(DB_PATH) as con:
            row_nfe = con.execute(
                "SELECT caminho, dados_claude FROM documentos WHERE id=?", (int(doc_id_nfe),)
            ).fetchone()
        if row_nfe:
            caminho_nfe, dados_nfe = row_nfe
            numero_nfe = _campo(dados_nfe, "Número da NF")
            data_nfe   = _campo(dados_nfe, "Data de emissão")
            sufixo_nfe = f"NFe {numero_nfe}" if numero_nfe != "A PREENCHER" else "NFe"
            _arquivar_doc_financeiro(pfm_codigo, sufixo_nfe, caminho_nfe, data_nfe)
        with sqlite3.connect(DB_PATH) as con:
            row_lanc = con.execute(
                "SELECT status, valor FROM lancamentos WHERE pfm_codigo=?", (pfm_codigo,)
            ).fetchone()
        status_lanc, valor_lanc = row_lanc if row_lanc else (None, None)
        if status_lanc == "pago":
            texto = f"🟢 #{pfm_codigo} — NF-e vinculada. Ciclo fechado."
        else:
            total_pago = _total_pago(pfm_codigo)
            faltam = (valor_lanc or 0) - total_pago
            texto = (
                f"🟡 #{pfm_codigo} — NF-e vinculada. Pagamento em andamento: "
                f"R$ {_fmt_brl(total_pago)} de R$ {_fmt_brl(valor_lanc or 0)} pago "
                f"(faltam R$ {_fmt_brl(faltam)}). Ciclo fecha quando o pagamento for concluído."
            )
        await query.edit_message_text(texto)
    else:
        await query.edit_message_text(
            f"Não foi possível vincular a NF-e ao Pedido #{pfm_codigo}.\n"
            "O pedido pode já ter uma NF-e vinculada."
        )


async def _cb_nfe_cancelar(query, ctx, partes):
    doc_id = int(partes[1])
    _descartar_documento(doc_id)
    await query.edit_message_text(
        "NF-e não vinculada. Arquivo descartado — pode reenviar depois de corrigir o pedido."
    )


async def _cb_parcelas_ver(query, ctx, partes):
    pfm_codigo = partes[1]
    pedido = buscar_pedido(pfm_codigo)
    if not pedido:
        await query.answer(f"Pedido {pfm_codigo} não encontrado.", show_alert=True)
        return
    await query.edit_message_text(
        _texto_parcelas(pedido),
        reply_markup=teclado_parcelas(pfm_codigo)
    )


async def _cb_recibo_parcela_iniciar(query, ctx, partes):
    parcela_id = int(partes[1])
    parcela = _buscar_parcela(parcela_id)
    if not parcela:
        await query.answer("Parcela não encontrada.", show_alert=True)
        return
    pfm_codigo = parcela[1]
    await query.edit_message_text(
        f"#{pfm_codigo} — Por que não tem NF-e?",
        reply_markup=teclado_motivo_recibo(parcela_id, pfm_codigo)
    )


async def _cb_recibo_parcela_motivo(query, ctx, partes):
    _, parcela_id_str, chave = partes
    parcela_id = int(parcela_id_str)
    if chave == "outro":
        ctx.user_data["aguardando"] = "recibo_motivo_texto"
        ctx.user_data["recibo_parcela_id"] = parcela_id
        await query.edit_message_text("Descreva o motivo:")
        return
    motivo = _MOTIVOS_RECIBO.get(chave, chave)
    await query.edit_message_text("Gerando recibo...")
    await _gerar_recibo(ctx, parcela_id, motivo)


async def _cb_recibo_assinado_iniciar(query, ctx, partes):
    parcela_id = int(partes[1])
    ctx.user_data["aguardando"] = "recibo_assinado_upload"
    ctx.user_data["recibo_parcela_id"] = parcela_id
    await query.edit_message_text("Envie a foto ou PDF do recibo assinado:")


async def _cb_obra_pedidos(query, ctx, partes):
    codigo  = partes[1]
    pedidos = _pedidos_obra(codigo)
    await query.edit_message_text(
        mostrar_lista_pedidos(codigo, pedidos),
        reply_markup=teclado_lista_pedidos(codigo, pedidos)
    )


async def _cb_obra_listas(query, ctx, partes):
    codigo = partes[1]
    listas = listar_listas_obra(DB_PATH, codigo, limite=10)
    await query.edit_message_text(
        mostrar_lista_listas_compra(codigo, listas),
        reply_markup=teclado_lista_listas_compra(codigo, listas)
    )


async def _cb_lc_buscar(query, ctx, partes):
    codigo = partes[1]
    ctx.user_data["aguardando"] = f"lista_buscar_nome_{codigo}"
    await query.edit_message_text(
        "Buscar lista pelo nome (Resumo)\n\nDigite parte do texto:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Voltar", callback_data=f"obra_listas:{codigo}")]])
    )


async def _cb_lc_abrir(query, ctx, partes):
    """Reabre uma lista já encerrada pra continuar editando — mesma Tela de Conferência,
    itens/endereço/observações/resumo carregados do banco (Dennis, 2026-07-06: poder voltar
    numa lista antiga por data ou nome). "Gerar" depois regrava esta mesma lista_id."""
    lista_id = int(partes[1])
    lista = buscar_lista(DB_PATH, lista_id)
    if not lista:
        await query.answer("Lista não encontrada.", show_alert=True)
        return
    itens = listar_itens(DB_PATH, lista_id)
    ctx.user_data["lista_itens"] = itens
    ctx.user_data["lista_ggv"] = lista["ggv"]
    ctx.user_data["lista_endereco"] = lista.get("endereco_entrega")
    ctx.user_data["lista_observacoes"] = lista.get("observacoes")
    ctx.user_data["lista_resumo"] = lista.get("resumo")
    ctx.user_data["lista_id_edicao"] = lista_id
    texto, markup = _renderizar_lista_conferencia(itens, lista["ggv"], ctx)
    await query.edit_message_text(texto, parse_mode="HTML", reply_markup=markup)


async def _cb_pedido_abrir(query, ctx, partes):
    pfm_codigo = partes[1]
    pedido = buscar_pedido(pfm_codigo)
    if pedido:
        preparar_visualizacao_pedido(pedido)
        await query.edit_message_text(
            mostrar_pedido(pedido),
            reply_markup=teclado_pedido(pedido.doc_id, pfm_codigo, pedido.doc_id_nfe, pedido.doc_id_comprovante, pedido.qtd_fotos_entrega, pedido.obs_entrega, pedido.status, pedido.categoria, pedido.qtd_parcelas)
        )
    else:
        await query.answer(f"Pedido {pfm_codigo} não encontrado.", show_alert=True)


async def _cb_pedido_excluir_confirmar(query, ctx, partes):
    pfm_codigo = partes[1]
    await query.edit_message_text(
        f"Excluir #{pfm_codigo}?\n\n"
        "Apaga o pedido, parcelas, entrega e todos os documentos vinculados na Laura. "
        "Não apaga arquivos já arquivados no OneDrive. Não pode ser desfeito.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🗑 Sim, excluir", callback_data=f"pedido_excluir_ok:{pfm_codigo}"),
            InlineKeyboardButton("← Voltar",       callback_data=f"pedido_abrir:{pfm_codigo}"),
        ]])
    )


async def _cb_pedido_excluir_ok(query, ctx, partes):
    pfm_codigo = partes[1]
    ggv = pfm_codigo.rsplit("-", 1)[0]
    _excluir_pedido(pfm_codigo)
    await query.edit_message_text(
        f"#{pfm_codigo} excluído.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Pedidos", callback_data=f"obra_pedidos:{ggv}")
        ]])
    )


async def _cb_obra_ver(query, ctx, partes):
    codigo = partes[1]
    obra = buscar_obra(codigo)
    if obra:
        await query.edit_message_text(
            mostrar_cockpit_obra(obra),
            reply_markup=teclado_obra(codigo, _pedidos_obra(codigo))
        )
    else:
        await query.edit_message_text(f"Obra {codigo} não encontrada.")


async def _cb_obra_editar(query, ctx, partes):
    codigo = partes[1]
    obra = buscar_obra(codigo)
    if obra:
        await query.edit_message_text(
            f"Qual campo deseja editar em {codigo}?",
            reply_markup=teclado_obra_campos(codigo)
        )
    else:
        await query.edit_message_text(f"Obra {codigo} não encontrada.")


async def _cb_obra_campo(query, ctx, partes):
    _, codigo, campo = partes
    ctx.user_data["aguardando"]   = f"obra_edit_{campo}"
    ctx.user_data["obra_codigo"]  = codigo
    labels = {
        "descricao":         "Descrição",
        "endereco_entrega":  "Endereço de entrega",
        "encarregado_nome":  "Nome do encarregado",
        "encarregado_fone":  "Telefone do encarregado",
        "responsavel_nome":  "Nome do responsável",
        "responsavel_fone":  "Telefone do responsável",
    }
    label = labels.get(campo, campo)
    await query.edit_message_text(f"Novo valor para {label}:")


async def _cb_pfm_fechar(query, ctx, partes):
    await query.edit_message_text("Fechado.")


async def _cb_obra_fechar(query, ctx, partes):
    await query.edit_message_text("Fechado.")


async def _cb_obras_fechar(query, ctx, partes):
    await query.edit_message_text("Fechado.")


async def _cb_menu_inicio(query, ctx, partes):
    await query.edit_message_text(
        mostrar_boas_vindas(),
        reply_markup=teclado_boas_vindas()
    )


async def _cb_menu_obras(query, ctx, partes):
    obras = _listar_obras()
    await query.edit_message_text(
        mostrar_lista_obras(obras),
        reply_markup=teclado_lista_obras(obras)
    )


async def _cb_menu_ajuda(query, ctx, partes):
    await query.edit_message_text(
        mostrar_ajuda(),
        reply_markup=teclado_ajuda(),
        parse_mode="HTML"
    )


async def _cb_menu_nova_obra(query, ctx, partes):
    await query.edit_message_text("Código da nova obra (ex: GGV04):")
    ctx.user_data["aguardando"] = "nova_obra_codigo"




_CB_DISPATCH = {
    "ok": _cb_ok,
    "cancelar": _cb_cancelar,
    "sel_tipo": _cb_sel_tipo,
    "set_tipo": _cb_set_tipo,
    "sel_tipo_inicial": _cb_sel_tipo_inicial,
    "pix_confirmar": _cb_pix_confirmar,
    "pix_pagar": _cb_pix_pagar,
    "pix_cancelar": _cb_pix_cancelar,
    "sel_ggv": _cb_sel_ggv,
    "set_ggv": _cb_set_ggv,
    "pgto": _cb_pgto,
    "endsel": _cb_endsel,
    "sel_edit": _cb_sel_edit,
    "edit_campo": _cb_edit_campo,
    "voltar_edit": _cb_voltar_edit,
    "ver_itens": _cb_ver_itens,
    "pfm": _cb_pfm,
    "cat_confirmar": _cb_cat_confirmar,
    "cat_corrigir": _cb_cat_corrigir,
    "cat_sel": _cb_cat_sel,
    "cat_edit": _cb_cat_edit,
    "cat_upd": _cb_cat_upd,
    "pfm_revisar": _cb_pfm_revisar,
    "pfm_ver": _cb_pfm_ver,
    "pfm_orc": _cb_pfm_orc,
    "pfm_nfe": _cb_pfm_nfe,
    "pfm_comp": _cb_pfm_nfe,
    "pfm_recibo": _cb_pfm_nfe,
    "pfm_entregue": _cb_pfm_entregue,
    "entrega_sel": _cb_entrega_sel,
    "entrega_obs": _cb_entrega_obs,
    "entrega_cancelar": _cb_entrega_cancelar,
    "entrega_foto_primeiro": _cb_entrega_foto_primeiro,
    "entrega_editar": _cb_entrega_editar,
    "entrega_mudar_obs": _cb_entrega_mudar_obs,
    "entrega_editobs": _cb_entrega_editobs,
    "entrega_trocar_foto": _cb_entrega_trocar_foto,
    "entrega_ver_fotos": _cb_entrega_ver_fotos,
    "entrega_foto_ver": _cb_entrega_foto_ver,
    "entrega_remover_foto": _cb_entrega_remover_foto,
    "entrega_foto_apagar": _cb_entrega_foto_apagar,
    "entrega_apagar": _cb_entrega_apagar,
    "entrega_voltar": _cb_entrega_voltar,
    "nfe_confirmar": _cb_nfe_confirmar,
    "nfe_cancelar": _cb_nfe_cancelar,
    "parcelas_ver": _cb_parcelas_ver,
    "recibo_parcela_iniciar": _cb_recibo_parcela_iniciar,
    "recibo_parcela_motivo": _cb_recibo_parcela_motivo,
    "recibo_assinado_iniciar": _cb_recibo_assinado_iniciar,
    "obra_pedidos": _cb_obra_pedidos,
    "obra_listas": _cb_obra_listas,
    "pedido_abrir": _cb_pedido_abrir,
    "pedido_excluir_confirmar": _cb_pedido_excluir_confirmar,
    "pedido_excluir_ok": _cb_pedido_excluir_ok,
    "obra_ver": _cb_obra_ver,
    "obra_editar": _cb_obra_editar,
    "obra_campo": _cb_obra_campo,
    "pfm_fechar": _cb_pfm_fechar,
    "obra_fechar": _cb_obra_fechar,
    "obras_fechar": _cb_obras_fechar,
    "menu_inicio": _cb_menu_inicio,
    "menu_obras": _cb_menu_obras,
    "menu_ajuda": _cb_menu_ajuda,
    "menu_nova_obra": _cb_menu_nova_obra,
    "lc_editar": _cb_lc_editar,
    "lc_item": _cb_lc_item,
    "lc_campo": _cb_lc_campo,
    "lc_campolista": _cb_lc_campolista,
    "lc_usarsugestao": _cb_lc_usarsugestao,
    "lc_repetircompra": _cb_lc_repetircompra,
    "lc_concluir": _cb_lc_concluir,
    "lc_tecnicoitem": _cb_lc_tecnicoitem,
    "lc_reinterpretar": _cb_lc_reinterpretar,
    "lc_tecnico": _cb_lc_tecnico,
    "lc_voltar": _cb_lc_voltar,
    "lc_defobra": _cb_lc_defobra,
    "lc_setobra": _cb_lc_setobra,
    "lc_gerar": _cb_lc_gerar,
    "lc_fechar": _cb_lc_fechar,
    "lc_abrir": _cb_lc_abrir,
    "lc_buscar": _cb_lc_buscar,
}

async def responder_botao(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DONO_ID:
        return
    query = update.callback_query
    partes = query.data.split(":")
    acao   = partes[0]

    # GGV blocking — alert antes de responder, depois retorna
    if acao == "ok" and partes[3] == "nao_identificado":
        try:
            await query.answer("Selecione a obra antes de confirmar.", show_alert=True)
        except Exception:
            pass
        return

    try:
        await query.answer()
    except Exception:
        return  # callback expirado (bot reiniciado) — ignora silenciosamente

    try:
        handler = _CB_DISPATCH.get(acao)
        if handler:
            await handler(query, ctx, partes)
    except Exception as e:
        await ctx.bot.send_message(chat_id=DONO_ID, text=f"Erro inesperado — tente novamente.\n{e}")

# ── Inicialização ──────────────────────────────────────────────────────────

async def _post_init(app):
    await app.bot.set_my_commands([
        BotCommand("help",      "Ações e consultas disponíveis"),
        BotCommand("obras",     "Lista de obras"),
        BotCommand("nova_obra", "Cadastrar obra nova"),
        BotCommand("entrega",   "Registrar entrega de pedido"),
        BotCommand("lista",     "Lista de compras de uma obra"),
    ])

if __name__ == "__main__":
    init_db()
    app = Application.builder().token(TOKEN).post_init(_post_init).build()
    app.add_handler(CommandHandler("start",     start))
    app.add_handler(CommandHandler("help",      ajuda))
    app.add_handler(CommandHandler("obras",     obras_cmd))
    app.add_handler(CommandHandler("nova_obra", nova_obra))
    app.add_handler(CommandHandler("entrega",   entrega_cmd))
    app.add_handler(CommandHandler("lista",     lista_cmd))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, receber_arquivo))
    app.add_handler(CallbackQueryHandler(responder_botao))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_texto))
    app.add_handler(MessageHandler(filters.COMMAND, comando_desconhecido))
    app.job_queue.run_repeating(_sincronizar_receita_fornecedores, interval=6 * 60 * 60, first=120)
    app.run_polling()
