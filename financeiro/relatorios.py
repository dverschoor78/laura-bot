"""
Domínio: Relatórios Financeiros

Gera fluxos e relatórios de pagamentos, consolidando:
  - Lançamentos (transações)
  - Documentos vinculados (NFe, Recibos, Orçamentos)
  - Itens e descrições extraídas via IA
  - Percentual de quitação por pedido

Relatórios disponíveis:
  - gerar_relatorio_pagamentos() → todos os pagamentos consolidados
  - gerar_fluxo_pagamentos_obra() → fluxo por obra com detalhes de NFe/Recibo
"""

import sqlite3
import re
from pathlib import Path
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def _criar_diretorio_relatorios():
    """Garante que data/relatorios/ existe."""
    relatorios_dir = Path(__file__).parent.parent / "data" / "relatorios"
    relatorios_dir.mkdir(parents=True, exist_ok=True)
    return relatorios_dir


def _extrair_nfe(nome_arquivo: str) -> str:
    """Extrai número da NFe do nome do arquivo."""
    if not nome_arquivo:
        return "---"
    match = re.search(r'NFe\s*(\d+)', nome_arquivo, re.IGNORECASE)
    if match:
        return match.group(1)
    return "---"


def _extrair_numero_documento(dados_claude: str, nome_arquivo: str) -> str:
    """Extrai número de ART, ONR, CREA, etc do dados_claude ou nome do arquivo."""
    if not dados_claude and not nome_arquivo:
        return "---"

    # Procura ART no dados_claude
    match = re.search(r'ART\s*n[º°\.]*\s*(\d+)', dados_claude or "", re.IGNORECASE)
    if match:
        return f"ART {match.group(1)}"

    # Procura ART no nome do arquivo
    match = re.search(r'ART[_-]?(\d+)', nome_arquivo or "", re.IGNORECASE)
    if match:
        return f"ART {match.group(1)}"

    # Procura ONR
    match = re.search(r'ONR[_-]?(\d+)', nome_arquivo or "", re.IGNORECASE)
    if match:
        return f"ONR {match.group(1)}"

    return "---"


def _resumo_itens(db_path, pfm_codigo: str) -> str:
    """Consolida itens do pedido num resumo tipo 'item1, item2, item3'."""
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    itens = con.execute(
        "SELECT descricao FROM itens_pedido WHERE pfm_codigo = ? ORDER BY numero LIMIT 5",
        (pfm_codigo,)
    ).fetchall()
    con.close()

    if not itens:
        return ""

    # Extrai só a primeira palavra/termo significativo de cada item
    termos = []
    for item in itens:
        desc = item['descricao']
        # Pega o primeiro termo significativo (até 15 chars, sem números no início)
        palavras = desc.split()
        if palavras:
            termo = palavras[0]
            if len(termo) > 3:  # Ignora artigos muito curtos
                termos.append(termo)

    if termos:
        return " ".join(termos[:3])  # Primeiros 3 termos
    return ""


def _extrair_descricao(dados_claude: str, categoria: str = None, nome_arquivo: str = None, db_path = None, pfm_codigo: str = None) -> str:
    """Extrai resumo dos itens: 'Categoria - item1, item2, item3'."""
    if not dados_claude:
        return "---"

    # Tenta extrair "Resumo da compra:" — formato esperado
    match = re.search(r'Resumo da compra[:\s]+([^\n]+)', dados_claude, re.IGNORECASE)
    if match:
        resumo = match.group(1).strip()
        resumo = re.sub(r'\*\*', '', resumo)  # Remove **

        # Se tem itens no banco, consolida melhor
        if db_path and pfm_codigo:
            itens_resumo = _resumo_itens(db_path, pfm_codigo)
            if itens_resumo:
                return f"{resumo} - {itens_resumo}"

        return resumo[:100]

    # Para taxa/ART/servicos: tenta extrair do nome do arquivo
    if categoria in ("taxa", "servicos", "servico_publico") and nome_arquivo:
        match = re.search(r'([^/_-]*(?:Projeto|Execucao|Servico|Obra|Art)[^/_-]*)', nome_arquivo, re.IGNORECASE)
        if match:
            desc = match.group(1).strip()
            return desc[:100]

    # Para material: tenta primeira linha + itens
    lines = dados_claude.split('\n')
    for line in lines:
        line = line.strip()
        line = re.sub(r'\*\*', '', line)
        if line and len(line) > 10 and ':' not in line[:20]:
            categoria_desc = line[:100]

            # Se tem itens, adiciona depois do hífen
            if db_path and pfm_codigo:
                itens_resumo = _resumo_itens(db_path, pfm_codigo)
                if itens_resumo:
                    return f"{categoria_desc} - {itens_resumo}"

            return categoria_desc

    return "---"


def _parse_data(data_str: str) -> str:
    """Normaliza data para DD/MM/YYYY."""
    if not data_str:
        return None

    # Tenta padrão DD/MM/YYYY
    match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', data_str)
    if match:
        day, month, year = match.groups()
        return f"{int(day):02d}/{int(month):02d}/{year}"

    # Tenta formato "N de MM de YYYY"
    match = re.search(r'(\d{1,2})\s+de\s+(\d{1,2})\s+de\s+(\d{4})', data_str)
    if match:
        day, month, year = match.groups()
        return f"{int(day):02d}/{int(month):02d}/{year}"

    return None


def _setup_estilos_excel():
    """Retorna um dicionário com estilos padrão para Excel."""
    return {
        "header_fill": PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid"),
        "header_font": Font(bold=True, color="FFFFFF", size=11),
        "total_fill": PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid"),
        "total_font": Font(bold=True, size=11),
        "center_align": Alignment(horizontal="center", vertical="center"),
        "wrap_align": Alignment(horizontal="left", vertical="top", wrap_text=True),
        "border": Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
    }


def gerar_fluxo_pagamentos_obra(db_path: Path, ggv: str = None, output_dir: Path = None) -> Path:
    """
    Gera fluxo de pagamentos por obra.

    Colunas: ENTRADA, C CUSTO, PEDIDO, FORNECEDOR, CATEGORIA, DESCRICAO, VALOR, NFe/Recibo, VALOR PAGO, % QUITADO

    Args:
        db_path: Caminho do banco de dados (data/laura.db)
        ggv: Filtrar por obra específica (ex: "GGV03"). Se None, retorna todas.
        output_dir: Diretório para salvar Excel. Padrão: data/relatorios/

    Returns:
        Path do arquivo Excel gerado.
    """
    if output_dir is None:
        output_dir = _criar_diretorio_relatorios()

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    # Query base — inclui documento original (pra extrair ART) e NFe
    query = """
        SELECT
            l.pfm_codigo,
            l.ggv,
            l.fornecedor,
            l.valor,
            l.valor_pago,
            l.data_pagamento,
            l.categoria,
            d_orig.nome as doc_orig,
            d_orig.dados_claude,
            d_nfe.nome as doc_nfe
        FROM lancamentos l
        LEFT JOIN documentos d_orig ON l.doc_id = d_orig.id
        LEFT JOIN documentos d_nfe ON l.doc_id_nfe = d_nfe.id
        WHERE l.status = 'pago'
    """
    params = []

    if ggv:
        query += " AND l.ggv = ?"
        params.append(ggv)

    query += " ORDER BY l.data_pagamento, l.ggv"

    rows = con.execute(query, params).fetchall()

    # Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Fluxo Pagamentos"

    estilos = _setup_estilos_excel()

    # Cabeçalho
    headers = [
        "ENTRADA",
        "C CUSTO",
        "PEDIDO",
        "FORNECEDOR",
        "CATEGORIA",
        "DESCRICAO",
        "VALOR",
        "NFe/Recibo",
        "VALOR PAGO",
        "% QUITADO"
    ]

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.fill = estilos["header_fill"]
        cell.font = estilos["header_font"]
        cell.alignment = estilos["center_align"]
        cell.border = estilos["border"]

    # Dados
    row_num = 2
    total_valor = 0
    total_pago = 0

    cat_map = {
        'material': 'MATERIAL',
        'mo': 'MO',
        'servicos': 'SERVIÇOS',
        'servico_publico': 'SERVIÇO PÚBLICO',
        'taxa': 'TAXA',
        'imposto': 'IMPOSTO',
    }

    for row in rows:
        data_entrada = _parse_data(row['data_pagamento'] or '')
        cc = row['ggv'] or '---'
        pedido = row['pfm_codigo'] or '---'
        fornecedor = row['fornecedor'] or '---'
        categoria = cat_map.get(row['categoria'], row['categoria'] or '---').upper()
        # Extrai descrição do documento original + itens do pedido
        descricao = _extrair_descricao(row['dados_claude'], row['categoria'], row['doc_orig'], db_path, row['pfm_codigo'])
        valor = row['valor'] or 0
        valor_pago = row['valor_pago'] or 0
        # Para taxa/ART: extrai número do documento original; para material: extrai número da NFe
        if row['categoria'] == 'taxa':
            nfe = _extrair_numero_documento(row['dados_claude'], row['doc_orig'])
        else:
            nfe = _extrair_nfe(row['doc_nfe'])
        percent_quitado = (valor_pago / valor * 100) if valor > 0 else 0

        total_valor += valor
        total_pago += valor_pago

        cells_data = [
            data_entrada,
            cc,
            pedido,
            fornecedor,
            categoria,
            descricao,
            valor,
            nfe,
            valor_pago,
            percent_quitado
        ]

        for col_num, value in enumerate(cells_data, 1):
            cell = ws.cell(row=row_num, column=col_num)

            if isinstance(value, (int, float)):
                if col_num == 7:  # VALOR
                    cell.value = value
                    cell.number_format = 'R$ #,##0.00'
                elif col_num == 9:  # VALOR PAGO
                    cell.value = value
                    cell.number_format = 'R$ #,##0.00'
                elif col_num == 10:  # % QUITADO
                    cell.value = value / 100
                    cell.number_format = '0.0%'
                else:
                    cell.value = value
            else:
                cell.value = value

            cell.border = estilos["border"]

            if col_num in [1, 2, 3, 10]:
                cell.alignment = estilos["center_align"]
            elif col_num == 6:  # DESCRICAO
                cell.alignment = estilos["wrap_align"]
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

        row_num += 1

    # Linha de total
    total_row = row_num
    ws.cell(row=total_row, column=1).value = "TOTAL"
    ws.cell(row=total_row, column=1).font = estilos["total_font"]
    ws.cell(row=total_row, column=1).fill = estilos["total_fill"]
    ws.cell(row=total_row, column=1).border = estilos["border"]

    for col in range(2, 10):
        cell = ws.cell(row=total_row, column=col)
        cell.fill = estilos["total_fill"]
        cell.border = estilos["border"]

    cell_valor = ws.cell(row=total_row, column=7)
    cell_valor.value = total_valor
    cell_valor.font = estilos["total_font"]
    cell_valor.number_format = 'R$ #,##0.00'
    cell_valor.border = estilos["border"]

    cell_pago = ws.cell(row=total_row, column=9)
    cell_pago.value = total_pago
    cell_pago.font = estilos["total_font"]
    cell_pago.number_format = 'R$ #,##0.00'
    cell_pago.border = estilos["border"]

    # Largura das colunas
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 10
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 25
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 50
    ws.column_dimensions['G'].width = 14
    ws.column_dimensions['H'].width = 12
    ws.column_dimensions['I'].width = 14
    ws.column_dimensions['J'].width = 12

    # Altura das linhas
    ws.row_dimensions[1].height = 25
    for i in range(2, row_num):
        ws.row_dimensions[i].height = 35

    con.close()

    # Salva
    ggv_suffix = f"_{ggv}" if ggv else ""
    output_file = output_dir / f"fluxo_pagamentos{ggv_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb.save(output_file)

    return output_file


def gerar_relatorio_pagamentos(db_path: Path, output_dir: Path = None) -> Path:
    """
    Gera relatório consolidado de todos os pagamentos.

    Colunas: ENTRADA, C CUSTO, CATEGORIA, FONTE, PEDIDO, PFM, FORNECEDOR, CNPJ/CPF, TIPO, FORMA PGTO, PAGO

    Args:
        db_path: Caminho do banco de dados (data/laura.db)
        output_dir: Diretório para salvar Excel. Padrão: data/relatorios/

    Returns:
        Path do arquivo Excel gerado.
    """
    if output_dir is None:
        output_dir = _criar_diretorio_relatorios()

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    rows = con.execute("""
        SELECT
            l.pfm_codigo,
            l.ggv,
            l.fornecedor,
            l.valor_pago,
            l.data_pagamento,
            l.categoria,
            l.tipo_documento,
            d.condicao_pgto,
            f.cnpj,
            f.cpf
        FROM lancamentos l
        LEFT JOIN documentos d ON l.doc_id = d.id
        LEFT JOIN fornecedores f ON LOWER(f.nome) = LOWER(l.fornecedor)
        WHERE l.status = 'pago'
        ORDER BY l.data_pagamento, l.ggv
    """).fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Pagamentos"

    estilos = _setup_estilos_excel()

    headers = [
        "ENTRADA",
        "C CUSTO",
        "CATEGORIA",
        "FONTE DO RECURSO",
        "PEDIDO",
        "PFM",
        "FORNECEDOR/CLIENTE",
        "CNPJ/CPF",
        "TIPO",
        "FORMA PGTO",
        "PAGO"
    ]

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.fill = estilos["header_fill"]
        cell.font = estilos["header_font"]
        cell.alignment = estilos["center_align"]
        cell.border = estilos["border"]

    # Dados
    row_num = 2
    total = 0

    cat_map = {
        'material': 'MATERIAL',
        'mo': 'MO',
        'servicos': 'SERVIÇOS',
        'servico_publico': 'SERVIÇO PÚBLICO',
        'taxa': 'TAXA',
        'imposto': 'IMPOSTO',
    }

    for row in rows:
        data_entrada = _parse_data(row['data_pagamento'] or '')
        ggv = row['ggv'] or '---'
        categoria = cat_map.get(row['categoria'], row['categoria'] or '---').upper()
        fonte = f"VII - MP CC {ggv}" if ggv != '---' else '---'
        pedido = row['pfm_codigo'] or '---'
        tipo_doc = (row['tipo_documento'] or '---').upper() if row['tipo_documento'] else '---'
        fornecedor = (row['fornecedor'] or '---')
        cnpj = row['cnpj']
        cpf = row['cpf']
        cnpj_cpf = cnpj or cpf or '---'
        tipo_forn = 'PJ' if cnpj else 'PF' if cpf else '---'

        forma = '---'
        if row['condicao_pgto']:
            forma_lower = row['condicao_pgto'].lower()
            if 'pix' in forma_lower:
                forma = 'PIX'
            elif 'boleto' in forma_lower:
                forma = 'BOLETO'
            elif 'ted' in forma_lower:
                forma = 'TED'

        valor_pago = row['valor_pago'] or 0
        total += valor_pago

        cells_data = [
            data_entrada,
            ggv,
            categoria,
            fonte,
            pedido,
            tipo_doc,
            fornecedor[:25],
            str(cnpj_cpf)[:17],
            tipo_forn,
            forma,
            valor_pago
        ]

        for col_num, value in enumerate(cells_data, 1):
            cell = ws.cell(row=row_num, column=col_num)

            if isinstance(value, (int, float)):
                cell.value = value
                cell.number_format = 'R$ #,##0.00'
            else:
                cell.value = value

            cell.border = estilos["border"]

            if col_num in [1, 2, 3, 11]:
                cell.alignment = estilos["center_align"]
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

        row_num += 1

    # Total
    total_row = row_num
    ws.cell(row=total_row, column=1).value = "TOTAL"
    ws.cell(row=total_row, column=1).font = estilos["total_font"]
    ws.cell(row=total_row, column=1).fill = estilos["total_fill"]
    ws.cell(row=total_row, column=1).border = estilos["border"]

    for col in range(2, 11):
        cell = ws.cell(row=total_row, column=col)
        cell.fill = estilos["total_fill"]
        cell.border = estilos["border"]

    cell_total = ws.cell(row=total_row, column=11)
    cell_total.value = total
    cell_total.font = estilos["total_font"]
    cell_total.number_format = 'R$ #,##0.00'
    cell_total.border = estilos["border"]

    # Largura
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 10
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 22
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 10
    ws.column_dimensions['G'].width = 28
    ws.column_dimensions['H'].width = 18
    ws.column_dimensions['I'].width = 6
    ws.column_dimensions['J'].width = 12
    ws.column_dimensions['K'].width = 14

    con.close()

    output_file = output_dir / f"relatorio_pagamentos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb.save(output_file)

    return output_file


# ── Prestação de contas da conta Mercado Pago (modelo da contabilidade Diniz, 2026-10-09) ──────

_CATEGORIA_ROTULO = {"material": "Material", "mo": "Mão de obra", "servicos": "Serviços",
                     "taxa": "Taxa", "imposto": "Imposto", "servico_publico": "Serviço público"}
_SEM_NFE_OBRIGATORIA = {"taxa", "imposto", "servico_publico"}
BANCO_FORA_DO_EXTRATO = "Conta particular (Dennis)"  # decisão do Dennis, caso GGV03-036
_PREFIXOS_OPERACAO = ("Pagamento com QR Pix", "Pagamento com Pix", "Pagamento de conta",
                      "Pix enviado", "Pix recebido", "Transferência enviada", "Transferência recebida")

_CAB_PAGAMENTOS = ["Data Pagamento", "Documento", "Fornecedor /  Descrição Pagamento",
                   "Detalhes do pagamento", "Valor Original", "Valor Pago", "Banco (Portador)",
                   "Categoria (despesa)", "Obra", "PFM", "NF/Recibo", "R$ Valor Total", "Situação"]
_CAB_RECEBIMENTOS = ["Data Recebimento", "Documento", "Cliente /  Descrição Receita",
                     "Detalhes do Recebimento", "Valor Original", "Valor Recebido",
                     "Banco (Portador)", "Categoria (Receita)", "Obra", "Situação"]
_LARGURAS_MODELO = [19.4, 14.3, 43.5, 31.8, 16.8, 16.8, 24.0, 27.6]  # A–H do modelo (F e G ampliadas)
_LARGURAS_EXTRAS = {"Obra": 9.0, "PFM": 12.0, "NF/Recibo": 22.0, "R$ Valor Total": 16.0, "Situação": 30.0}


def _operacao_e_contraparte(descricao: str) -> tuple:
    """'Pix enviado Capital Vidros Ltda' → ('Pix enviado', 'Capital Vidros Ltda')."""
    for prefixo in _PREFIXOS_OPERACAO:
        if descricao.startswith(prefixo):
            return prefixo, descricao[len(prefixo):].strip()
    return "", descricao


def _documentos_dos_pedidos(db_path, pagamentos: list) -> tuple:
    """NF-e por pedido, resumo da compra por pedido e situação do recibo por parcela."""
    pfms = sorted({p["pfm_codigo"] for p in pagamentos})
    nfes, resumos, recibos = {}, {}, {}
    if not pfms:
        return nfes, resumos, recibos
    marcas = ",".join("?" * len(pfms))
    with sqlite3.connect(db_path) as con:
        for pfm, numero in con.execute(
                f"SELECT pfm_codigo, numero FROM notas_fiscais_pedido WHERE pfm_codigo IN ({marcas}) ORDER BY id", pfms):
            nfes.setdefault(pfm, []).append(numero or "s/nº")
        for pfm, resumo, dados in con.execute(
                f"SELECT l.pfm_codigo, l.resumo_compra, d.dados_claude FROM lancamentos l "
                f"LEFT JOIN documentos d ON d.id = l.doc_id WHERE l.pfm_codigo IN ({marcas})", pfms):
            if not resumo and dados:
                m = re.search(r"Resumo da compra:\**\s*(.+)", dados)
                resumo = m.group(1).strip(" *") if m else None
            resumos[pfm] = resumo
        ids = [p["parcela_id"] for p in pagamentos]
        for pid, gerado, assinado in con.execute(
                f"SELECT id, doc_id_recibo IS NOT NULL, doc_id_recibo_assinado IS NOT NULL "
                f"FROM parcelas_pagamento WHERE id IN ({','.join('?' * len(ids))})", ids):
            recibos[pid] = "Recibo assinado" if assinado else ("Recibo pendente" if gerado else None)
    return nfes, resumos, recibos


def _nf_ou_recibo(pag: dict, nfes: dict, recibos: dict) -> str:
    if pag["pfm_codigo"] in nfes:
        return "NF-e " + ", ".join(nfes[pag["pfm_codigo"]])
    if pag["categoria"] in _SEM_NFE_OBRIGATORIA:
        return "Fatura"
    if recibos.get(pag["parcela_id"]):
        return recibos[pag["parcela_id"]]
    return "Recibo pendente" if pag["categoria"] == "mo" else "Pendente"


def _linha_pagamento(pag: dict, nfes: dict, resumos: dict, recibos: dict, operacao: str) -> list:
    """Colunas C..M de um pagamento registrado. Valor Original: valor do pedido quando foi pago
    de uma vez; valor da própria parcela quando é parcelado (regra do Dennis, 2026-10-09)."""
    unico = pag["qtd_parcelas"] == 1 and pag["status"] == "pago"
    resumo = resumos.get(pag["pfm_codigo"])
    detalhe = "pagamento único" if unico else f"parcela {pag['ordem']}"
    return [
        pag["fornecedor"] + (f" — {resumo}" if resumo else ""),
        f"{operacao} · {detalhe}" if operacao else detalhe,
        pag["valor_pedido"] if unico else pag["valor"],
        pag["valor"],
        None,  # banco: preenchido por quem chama
        _CATEGORIA_ROTULO.get(pag["categoria"], pag["categoria"] or ""),
        pag["obra"], pag["pfm_codigo"], _nf_ou_recibo(pag, nfes, recibos), pag["valor_pedido"],
    ]


def gerar_planilha_prestacao_contas(extrato, resultado: dict, db_path, caminho_xlsx: Path) -> Path:
    """Planilha de prestação de contas da conta Mercado Pago no modelo da contabilidade (Diniz):
    abas PAGAMENTOS e RECEBIMENTOS, colunas A–H do modelo + Obra, PFM, NF/Recibo, R$ Valor Total
    e Situação (decisões do Dennis, 2026-10-09). Uma linha por movimento do extrato; pagamentos
    registrados que não passaram por esta conta vão no fim, como "Fora do extrato". O que a Laura
    não sabe fica em branco, com Situação "Preencher"."""
    from financeiro.conciliacao import apelido_conta  # aqui: o módulo também roda como script
    banco = f"Mercado Pago {apelido_conta(extrato)}"
    conciliados = {id(mov): (pag, como) for mov, pag, como in resultado["conciliados"]}
    pagamentos = [pag for _, pag, _ in resultado["conciliados"]] + resultado["fora_do_extrato"]
    nfes, resumos, recibos = _documentos_dos_pedidos(db_path, pagamentos)

    wb = Workbook()
    ws_pag = wb.active
    ws_pag.title = "PAGAMENTOS"
    ws_rec = wb.create_sheet("RECEBIMENTOS")
    negrito = Font(bold=True)
    for ws, cab in ((ws_pag, _CAB_PAGAMENTOS), (ws_rec, _CAB_RECEBIMENTOS)):
        for col, titulo in enumerate(cab, 1):
            ws.cell(row=2, column=col, value=titulo).font = negrito
            ws.column_dimensions[get_column_letter(col)].width = (
                _LARGURAS_MODELO[col - 1] if col <= len(_LARGURAS_MODELO) else _LARGURAS_EXTRAS[titulo])
        ws.freeze_panes = "A3"

    def escreve(ws, linha, valores):
        for col, valor in enumerate(valores, 1):
            cel = ws.cell(row=linha, column=col, value=valor)
            if col == 1 and valor is not None:
                cel.number_format = "DD/MM/YY"
            elif isinstance(valor, float):
                cel.number_format = "#,##0.00"

    def total(ws, linha, rotulo, valor):
        ws.cell(row=linha, column=1, value=rotulo).font = negrito
        cel = ws.cell(row=linha, column=6, value=round(valor, 2))
        cel.font, cel.number_format = negrito, "#,##0.00"

    linha = 3
    for mov in (m for m in extrato.movimentos if m.valor < 0):
        operacao, contraparte = _operacao_e_contraparte(mov.descricao)
        if id(mov) in conciliados:
            pag, _ = conciliados[id(mov)]
            c_m = _linha_pagamento(pag, nfes, resumos, recibos, operacao)
            c_m[4] = banco
            situacao = "Conciliado" + (f" · data na Laura {pag['data']:%d/%m}" if pag["data"] != mov.data else "")
            escreve(ws_pag, linha, [mov.data, mov.id_operacao] + c_m + [situacao])
        else:
            escreve(ws_pag, linha, [mov.data, mov.id_operacao, contraparte, operacao, -mov.valor,
                                    -mov.valor, banco, None, None, None, None, None, "Preencher"])
        linha += 1
    total(ws_pag, linha, "TOTAL NO EXTRATO", -sum(m.valor for m in extrato.movimentos if m.valor < 0))
    if resultado["fora_do_extrato"]:
        linha += 2
        for pag in resultado["fora_do_extrato"]:
            c_m = _linha_pagamento(pag, nfes, resumos, recibos, "Pago fora do extrato")
            c_m[4] = BANCO_FORA_DO_EXTRATO
            escreve(ws_pag, linha, [pag["data"], pag["identificador"] or None] + c_m + ["Fora do extrato"])
            linha += 1
        total(ws_pag, linha, "PAGO FORA DO EXTRATO", sum(p["valor"] for p in resultado["fora_do_extrato"]))

    linha = 3
    for mov in resultado["entradas"]:
        operacao, contraparte = _operacao_e_contraparte(mov.descricao)
        escreve(ws_rec, linha, [mov.data, mov.id_operacao, contraparte, operacao, mov.valor,
                                mov.valor, banco, None, None, "Preencher"])
        linha += 1
    total(ws_rec, linha, "TOTAL", sum(m.valor for m in resultado["entradas"]))

    caminho_xlsx = Path(caminho_xlsx)
    caminho_xlsx.parent.mkdir(parents=True, exist_ok=True)
    wb.save(caminho_xlsx)
    return caminho_xlsx


if __name__ == "__main__":
    # Teste local
    db = Path(__file__).parent.parent / "data" / "laura.db"
    print(f"Gerando fluxo de pagamentos...")
    arquivo = gerar_fluxo_pagamentos_obra(db)
    print(f"[OK] {arquivo.name}")

    print(f"Gerando relatorio de pagamentos...")
    arquivo = gerar_relatorio_pagamentos(db)
    print(f"[OK] {arquivo.name}")
