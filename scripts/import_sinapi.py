"""
import_sinapi.py — baixa a planilha oficial do SINAPI (Caixa) e importa os insumos
de material para a tabela insumos_sinapi do laura.db.

Roda manualmente, de vez em quando (o SINAPI é atualizado todo mês pela Caixa).
Reexecutar é seguro: atualiza descrição/unidade/preço por código, mas nunca mexe
na coluna fabricante — essa é preenchida à mão, aos poucos, fora deste script.
"""
import sqlite3
import zipfile
import urllib.request
from datetime import date
from io import BytesIO
from pathlib import Path

import openpyxl

DB_PATH = Path("data/laura.db")

BASE_URL = "https://www.caixa.gov.br/Downloads/sinapi-relatorios-mensais"
ABA_INSUMOS = "ISD"          # Insumos Sem Desoneração
LINHA_CABECALHO = 10
CLASSIFICACOES_DESEJADAS = {"MATERIAL"}
UF_REFERENCIA = "PR"


def _candidatos_ano_mes(n=6):
    """Últimos n meses, do mais recente pro mais antigo — a Caixa publica com atraso variável."""
    hoje = date.today()
    ano, mes = hoje.year, hoje.month
    candidatos = []
    for _ in range(n):
        candidatos.append((ano, mes))
        mes -= 1
        if mes == 0:
            mes, ano = 12, ano - 1
    return candidatos


def baixar_zip():
    for ano, mes in _candidatos_ano_mes():
        url = f"{BASE_URL}/SINAPI-{ano}-{mes:02d}-formato-xlsx.zip"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                if resp.status == 200:
                    print(f"[download] {url}")
                    return resp.read(), f"{mes:02d}/{ano}"
        except Exception:
            continue
    raise RuntimeError(
        "Nenhum mês recente encontrado em " + BASE_URL +
        " — confira manualmente se a Caixa mudou o padrão de nome do arquivo."
    )


def extrair_planilha_referencia(zip_bytes):
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        nome = next(n for n in zf.namelist() if n.lower().startswith("sinapi_refer"))
        print(f"[planilha] {nome}")
        with zf.open(nome) as f:
            return openpyxl.load_workbook(BytesIO(f.read()), data_only=True, read_only=True)


def ler_insumos(wb):
    ws = wb[ABA_INSUMOS]
    linhas = ws.iter_rows(min_row=LINHA_CABECALHO, values_only=True)
    cabecalho = next(linhas)
    idx = {" ".join(str(nome).split()): i for i, nome in enumerate(cabecalho) if nome}

    col_classif = idx.get("Classificação")
    col_codigo  = idx.get("Código do Insumo")
    col_desc    = idx.get("Descrição do Insumo")
    col_und     = idx.get("Unidade")
    col_preco   = idx.get(UF_REFERENCIA)

    faltando = [n for n, c in {
        "Classificação": col_classif, "Código do Insumo": col_codigo,
        "Descrição do Insumo": col_desc, "Unidade": col_und, UF_REFERENCIA: col_preco,
    }.items() if c is None]
    if faltando:
        raise RuntimeError(f"Colunas não encontradas no cabeçalho da aba {ABA_INSUMOS}: {faltando}")

    insumos = []
    for linha in linhas:
        if not linha or linha[col_codigo] is None:
            continue
        classif = str(linha[col_classif] or "").strip().upper()
        if classif not in CLASSIFICACOES_DESEJADAS:
            continue
        preco = linha[col_preco]
        insumos.append({
            "codigo":    int(linha[col_codigo]),
            "descricao": str(linha[col_desc] or "").strip(),
            "unidade":   str(linha[col_und] or "").strip(),
            "preco_pr":  float(preco) if preco is not None else None,
        })
    return insumos


def criar_tabela():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS insumos_sinapi (
                codigo          INTEGER PRIMARY KEY,
                descricao       TEXT NOT NULL,
                unidade         TEXT,
                preco_pr        REAL,
                mes_referencia  TEXT,
                fabricante      TEXT,
                atualizado_em   TEXT DEFAULT (datetime('now','localtime'))
            )
        """)


def gravar(insumos, mes_referencia):
    with sqlite3.connect(DB_PATH) as con:
        for it in insumos:
            con.execute("""
                INSERT INTO insumos_sinapi (codigo, descricao, unidade, preco_pr, mes_referencia, atualizado_em)
                VALUES (?,?,?,?,?, datetime('now','localtime'))
                ON CONFLICT(codigo) DO UPDATE SET
                    descricao=excluded.descricao,
                    unidade=excluded.unidade,
                    preco_pr=excluded.preco_pr,
                    mes_referencia=excluded.mes_referencia,
                    atualizado_em=excluded.atualizado_em
            """, (it["codigo"], it["descricao"], it["unidade"], it["preco_pr"], mes_referencia))


def main():
    criar_tabela()
    zip_bytes, mes_referencia = baixar_zip()
    wb = extrair_planilha_referencia(zip_bytes)
    insumos = ler_insumos(wb)
    gravar(insumos, mes_referencia)
    print(f"\nOK {len(insumos)} insumos de MATERIAL importados "
          f"(referência {mes_referencia}, UF {UF_REFERENCIA}, sem desoneração)")
    print("Coluna 'fabricante' preservada em execuções futuras — preencha manualmente quando quiser.")


if __name__ == "__main__":
    main()
