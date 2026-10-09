"""
Domínio: Conciliação Mensal

Conciliação: confronto entre o extrato bancário (Mercado Pago) e os pagamentos registrados na
Laura. Identifica as correspondências automaticamente e devolve o que não casou — o que não
casou vai para a planilha de prestação de contas, para o Dennis preencher (2026-10-09).

Fluxo implementado (2026-10-09):
  1. Usuário envia o PDF do extrato Mercado Pago via Telegram (tipo "Extrato MP")
  2. processar_extrato_mp() lê o PDF sem IA (formato fixo) e confere o saldo linha a linha
  3. identificar_correspondencias() cruza as saídas com os pagamentos registrados (parcelas)
  4. financeiro/relatorios.py gera a planilha no modelo da contabilidade (Diniz)

Previsto, ainda não implementado: Período fechado (mês conciliado e travado) — só quando
houver necessidade real.

Funções deste módulo recebem db_path como parâmetro explícito.
Nenhuma variável de ambiente é lida aqui.
"""
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

# pdfminer avisa (FontBBox etc.) ao abrir PDF que não é extrato — ruído no log do bot
logging.getLogger("pdfminer").setLevel(logging.ERROR)


class ExtratoInvalido(Exception):
    """O PDF não é um extrato do Mercado Pago, ou a leitura não fecha o saldo."""


@dataclass
class Movimento:
    data: date
    descricao: str
    id_operacao: str
    valor: float          # negativo = saída
    saldo: float


@dataclass
class ExtratoMP:
    titular: str
    cnpj: str
    agencia: str
    conta: str
    inicio: date
    fim: date
    saldo_inicial: float
    entradas: float
    saidas: float         # negativo, como vem no extrato
    saldo_final: float
    movimentos: list = field(default_factory=list)


_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
          "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
_CNPJ_VII = "58358802000158"


def apelido_conta(extrato: "ExtratoMP") -> str:
    """Nome curto da conta pra relatório e mensagem: 'VII' pra conta da Verschoor
    Investimentos Imobiliários; senão, o titular do extrato."""
    return "VII" if extrato.cnpj == _CNPJ_VII else extrato.titular


def _valor_brl(texto: str) -> float:
    """'R$ -1.500,00' → -1500.0 (o extrato sempre traz vírgula decimal)."""
    s = texto.replace("R$", "").replace(" ", "")
    return float(s.replace(".", "").replace(",", "."))


def _data(texto: str) -> Optional[date]:
    """Mesma regra de bot._parse_data_qualquer (corrigida em 2026-10-09 para mês numérico em
    'DD de MM de AAAA', formato real de 12 pagamentos da GGV03). Hora no fim é ignorada;
    devolve None quando não reconhece — nunca adivinha."""
    if not texto:
        return None
    s = texto.strip().lower()
    for padrao, ordem, no_meio in ((r"(\d{4})-(\d{1,2})-(\d{1,2})", "amd", False),
                                   (r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", "dma", False),
                                   (r"(\d{1,2})/(\D[^/]*)/(\d{4})", "dma", False),
                                   (r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", "dma", True)):
        m = re.search(padrao, s) if no_meio else re.match(padrao, s)
        if not m:
            continue
        a, b, c = m.groups()
        dia, mes, ano = (c, b, a) if ordem == "amd" else (a, b, c)
        mes = mes.strip()
        mes = _MESES.index(mes) + 1 if mes in _MESES else (int(mes) if mes.isdigit() else None)
        if mes is None:
            continue
        ano = int(ano) + (2000 if len(ano) == 2 else 0)
        try:
            return date(ano, mes, int(dia))
        except ValueError:
            continue
    return None


def _cabecalho(texto: str, rotulo: str, padrao: str = r"(-?[\d.]+,\d{2})") -> str:
    m = re.search(rf"{rotulo}\s*R?\$?\s*{padrao}", texto)
    if not m:
        raise ExtratoInvalido(f"campo '{rotulo}' não encontrado — não parece extrato do Mercado Pago")
    return m.group(1)


def conferir_saldos(extrato: ExtratoMP) -> None:
    """Garante que a leitura está certa: cada linha fecha com o saldo anterior, a última bate
    com o saldo final e as somas batem com Entradas/Saídas. Qualquer diferença → ExtratoInvalido
    (nada é gerado a partir de uma leitura que não fecha)."""
    saldo = extrato.saldo_inicial
    for mov in extrato.movimentos:
        if abs(saldo + mov.valor - mov.saldo) > 0.005:
            raise ExtratoInvalido(
                f"o saldo não fecha no movimento de {mov.data:%d/%m} ({mov.descricao}, "
                f"R$ {mov.valor:,.2f})")
        saldo = mov.saldo
    if abs(saldo - extrato.saldo_final) > 0.005:
        raise ExtratoInvalido("o último saldo não bate com o saldo final do extrato")
    entradas = sum(m.valor for m in extrato.movimentos if m.valor > 0)
    saidas = sum(m.valor for m in extrato.movimentos if m.valor < 0)
    if abs(entradas - extrato.entradas) > 0.005 or abs(saidas - extrato.saidas) > 0.005:
        raise ExtratoInvalido("a soma dos movimentos não bate com Entradas/Saídas do extrato")


def processar_extrato_mp(caminho_pdf) -> ExtratoMP:
    """Lê o PDF do extrato do Mercado Pago sem IA — o formato é fixo: cada movimento fica entre
    duas linhas horizontais, com data, número da operação, valor e saldo na mesma faixa e a
    descrição quebrada em volta. Os campos são reconhecidos pelo formato, não pela posição.
    Termina conferindo o saldo linha a linha (conferir_saldos)."""
    import pdfplumber
    try:
        pdf = pdfplumber.open(caminho_pdf)
    except Exception as e:
        raise ExtratoInvalido(f"não consegui abrir o PDF ({e.__class__.__name__})")
    movimentos = []
    with pdf:
        if not pdf.pages:
            raise ExtratoInvalido("PDF vazio")
        texto1 = pdf.pages[0].extract_text() or ""
        if "EXTRATO DE CONTA" not in texto1 or "Mercado Pago" not in "".join(
                (p.extract_text() or "") for p in pdf.pages):
            raise ExtratoInvalido("não parece um extrato de conta do Mercado Pago")
        conta = re.search(r"CPF/CNPJ:\s*(\d+)\s+Ag[eê]ncia:\s*(\d+)\s+Conta:\s*(\d+)", texto1)
        periodo = re.search(r"Periodo:\s*De\s*(\d{2}-\d{2}-\d{4})\s*al\s*(\d{2}-\d{2}-\d{4})", texto1)
        if not conta or not periodo:
            raise ExtratoInvalido("conta ou período não encontrados no cabeçalho")
        linhas_texto = texto1.splitlines()
        titular = linhas_texto[linhas_texto.index("EXTRATO DE CONTA") + 1].strip() \
            if "EXTRATO DE CONTA" in linhas_texto else ""

        for page in pdf.pages:
            palavras = page.extract_words()
            cab = [w for w in palavras if w["text"] == "Descrição"]
            col_id = [w for w in palavras if w["text"] == "ID"]
            if not cab or not col_id:
                continue  # página sem tabela de movimentos
            topo_tabela = cab[0]["bottom"]
            regras = sorted({round(l["top"], 1) for l in page.lines + page.rects
                             if abs(l["top"] - l["bottom"]) < 2 and l["top"] > topo_tabela - 1})
            for cima, baixo in zip(regras, regras[1:]):
                faixa = [w for w in palavras if cima < (w["top"] + w["bottom"]) / 2 < baixo]
                if not faixa:
                    continue
                datas = [w for w in faixa if re.fullmatch(r"\d{2}-\d{2}-\d{4}", w["text"])]
                ids = [w for w in faixa if re.fullmatch(r"\d{9,}", w["text"]) and w["x0"] >= col_id[0]["x0"] - 5]
                valores = sorted((w for w in faixa if re.fullmatch(r"-?[\d.]+,\d{2}", w["text"])),
                                 key=lambda w: w["x0"])
                if len(datas) != 1 or len(ids) != 1 or len(valores) != 2:
                    raise ExtratoInvalido("um movimento não tem data, número da operação, valor e saldo")
                usados = {id(datas[0]), id(ids[0])} | {id(v) for v in valores}
                descricao = ""
                for w in sorted(faixa, key=lambda w: (round(w["top"]), w["x0"])):
                    if id(w) in usados or w["text"] == "R$" or w["x0"] >= ids[0]["x0"]:
                        continue
                    # palavra quebrada no fim da linha ("COPEL-" + "DIS", "registrouol." + "com.br")
                    colada = descricao.endswith("-") or (descricao.endswith(".") and w["text"][:1].islower())
                    descricao += w["text"] if (colada or not descricao) else " " + w["text"]
                d, m_, a = datas[0]["text"].split("-")
                movimentos.append(Movimento(date(int(a), int(m_), int(d)), descricao.strip(),
                                            ids[0]["text"], _valor_brl(valores[0]["text"]),
                                            _valor_brl(valores[1]["text"])))
    if not movimentos:
        raise ExtratoInvalido("nenhum movimento encontrado")
    d1, d2 = (date(*reversed([int(x) for x in p.split("-")])) for p in periodo.groups())
    extrato = ExtratoMP(
        titular=titular, cnpj=conta.group(1), agencia=conta.group(2), conta=conta.group(3),
        inicio=d1, fim=d2,
        saldo_inicial=_valor_brl(_cabecalho(texto1, "Saldo inicial:")),
        entradas=_valor_brl(_cabecalho(texto1, "Entradas:")),
        saidas=_valor_brl(_cabecalho(texto1, "Saidas:")),
        saldo_final=_valor_brl(_cabecalho(texto1, "Saldo final:")),
        movimentos=movimentos,
    )
    conferir_saldos(extrato)
    return extrato


def _pagamentos_registrados(db_path, inicio: date, fim: date) -> list:
    """Pagamentos (parcelas) de todas as obras com data entre `inicio` e `fim`, com o texto do
    comprovante — onde aparece o número da operação do Mercado Pago, quando aparece."""
    with sqlite3.connect(db_path) as con:
        linhas = con.execute("""
            SELECT p.id, p.pfm_codigo, l.ggv, l.fornecedor, l.categoria, l.valor, l.status,
                   p.valor, p.data_pagamento, COALESCE(p.identificador_comprovante, ''),
                   COALESCE(d.dados_claude, ''),
                   (SELECT COUNT(*) FROM parcelas_pagamento q WHERE q.pfm_codigo = p.pfm_codigo),
                   (SELECT COUNT(*) FROM parcelas_pagamento q WHERE q.pfm_codigo = p.pfm_codigo AND q.id <= p.id)
            FROM parcelas_pagamento p
            JOIN lancamentos l ON l.pfm_codigo = p.pfm_codigo
            LEFT JOIN documentos d ON d.id = p.doc_id_comprovante
        """).fetchall()
    pagamentos = []
    for (pid, pfm, ggv, forn, cat, valor_pedido, status, valor, data_txt, ident, texto_comp,
         qtd, ordem) in linhas:
        d = _data(data_txt)
        if d and inicio <= d <= fim:
            pagamentos.append(dict(parcela_id=pid, pfm_codigo=pfm, obra=ggv, fornecedor=forn,
                                   categoria=cat, valor_pedido=valor_pedido, status=status,
                                   valor=valor, data=d, identificador=ident, texto=texto_comp,
                                   qtd_parcelas=qtd, ordem=ordem))
    return pagamentos


def identificar_correspondencias(extrato: ExtratoMP, db_path, tolerancia_dias: int = 3) -> dict:
    """Casa cada saída do extrato com um pagamento registrado: primeiro pelo número da operação
    (está no comprovante — certeza), depois por valor exato + data até `tolerancia_dias` dias
    (o mais próximo na data). Cada pagamento casa uma vez só. Devolve:
      conciliados      [(movimento, pagamento, "número da operação" | "valor e data")]
      a_preencher      [movimento]  — saídas sem pagamento registrado
      entradas         [movimento]
      fora_do_extrato  [pagamento]  — pagos no período, mas não por esta conta
    """
    folga = timedelta(days=7)
    pagamentos = _pagamentos_registrados(db_path, extrato.inicio - folga, extrato.fim + folga)
    usados, conciliados, a_preencher = set(), [], []
    saidas = [m for m in extrato.movimentos if m.valor < 0]
    pendentes = []
    for mov in saidas:
        achado = next((p for p in pagamentos if p["parcela_id"] not in usados and
                       (mov.id_operacao == p["identificador"] or mov.id_operacao in p["texto"])), None)
        if achado:
            usados.add(achado["parcela_id"])
            conciliados.append((mov, achado, "número da operação"))
        else:
            pendentes.append(mov)
    for mov in pendentes:
        candidatos = [p for p in pagamentos if p["parcela_id"] not in usados
                      and abs(p["valor"] + mov.valor) < 0.01
                      and abs((p["data"] - mov.data).days) <= tolerancia_dias]
        if candidatos:
            achado = min(candidatos, key=lambda p: abs((p["data"] - mov.data).days))
            usados.add(achado["parcela_id"])
            conciliados.append((mov, achado, "valor e data"))
        else:
            a_preencher.append(mov)
    conciliados.sort(key=lambda c: extrato.movimentos.index(c[0]))
    fora = [p for p in pagamentos if p["parcela_id"] not in usados
            and extrato.inicio <= p["data"] <= extrato.fim]
    return {
        "conciliados": conciliados,
        "a_preencher": a_preencher,
        "entradas": [m for m in extrato.movimentos if m.valor > 0],
        "fora_do_extrato": sorted(fora, key=lambda p: p["data"]),
    }
