"""
import_fornecedores.py — executa uma vez para popular a tabela fornecedores
com dados extraídos dos PFMs das obras GGV01 e GGV02.
"""
import sqlite3
import re
from pathlib import Path
from docx import Document
from lxml import etree

DB_PATH = Path("data/laura.db")

PASTAS = [
    Path(r"C:\Users\denni\OneDrive\00 Obras\2024-02 GGV01\04 Aquisição e Execução\51 Obra - Materiais e serviços"),
]

IGNORAR_TEXTOS = {
    "FORNECEDOR", "MATERIAIS", "DADOS PARA FATURA", "DADOS PARA ENTREGA",
    "ID", "UND", "QTDE", "DESCONTO", "CLIENTE", "CONTATO", "LOGRADOURO",
    "BAIRRO", "CIDADE", "UF", "CEP", "IE", "WHATSAPP", "e-mail",
    "PRAZO PARA ENTREGA E CONDIÇÕES DE PAGAMENTO", "REGISTRO DA ENTREGA",
    "DATA ENTREGA", "CONDIÇÕES DE PAGAMENTO", "PRAZO", "ENTREGA",
    "FAVOR TIRAR FOTOS DO MATERIAL RECEBIDO E ENVIAR POR WHATSAPP PARA DENNIS",
}


def extrair_textos_unicos(doc_path):
    """Extrai todos os <w:t> do XML (inclui caixas de texto), sem duplicatas."""
    doc = Document(doc_path)
    xml = etree.tostring(doc.element, encoding="unicode")
    todos = re.findall(r"<w:t[^>]*>([^<]+)</w:t>", xml)
    vistos, unicos = set(), []
    for t in todos:
        t = t.strip()
        if t and t not in vistos:
            vistos.add(t)
            unicos.append(t)
    return unicos


def extrair_fornecedor(doc_path):
    unicos = extrair_textos_unicos(doc_path)
    texto  = " ".join(unicos)

    # CNPJ: primeiro ocorre o do fornecedor; segundo é DeltaD/Verschoor
    cnpjs = re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", texto)
    cnpj  = cnpjs[0] if cnpjs else None

    # CPF (pessoa física): XX.XXX.XXX-XX
    cpfs = re.findall(r"\d{3}\.\d{3}\.\d{3}-\d{2}", texto)
    cpf  = cpfs[0] if (not cnpj and cpfs) else None

    # Razão social: texto imediatamente após o CNPJ/CPF na lista
    razao_social = None
    doc_id = cnpj or cpf
    if doc_id and doc_id in unicos:
        idx = unicos.index(doc_id)
        for candidato in unicos[idx + 1 : idx + 5]:
            if (
                len(candidato) > 5
                and not re.match(r"^\d", candidato)
                and candidato.upper() not in IGNORAR_TEXTOS
                and "/" not in candidato
            ):
                razao_social = candidato
                break

    # Fallback: nome do arquivo "GGV02-002 - Costa Ferro - aco.docx" → "Costa Ferro"
    nome_arquivo = doc_path.stem
    partes = [p.strip() for p in nome_arquivo.split(" - ")]
    nome_curto = partes[1] if len(partes) >= 2 else nome_arquivo

    # Contato, email, WhatsApp
    emails   = re.findall(r"[\w.+-]+@[\w.-]+\.\w+", texto)
    fones    = re.findall(r"(?:\(\d{2}\)\s*\d{4,5}[-\s]\d{4}|\d{2}\s*9\d{4}[-\s]\d{4})", texto)
    ceps     = re.findall(r"\d{2}\.\d{3}-\d{3}", texto)

    # Contato: nome após e-mail
    contato = None
    if emails:
        try:
            idx_email = unicos.index(emails[0])
            for c in unicos[idx_email + 1 : idx_email + 3]:
                if re.match(r"^[A-Za-zÀ-ú]", c) and len(c) > 2:
                    contato = c
                    break
        except ValueError:
            pass

    # Chave PIX
    pix_m = re.search(r"chave[:\s]+(\S+)", texto, re.IGNORECASE)
    pix   = pix_m.group(1) if pix_m else None

    # Cidade: texto antes do CEP
    cidade, uf = None, None
    if ceps:
        try:
            idx_cep = unicos.index(ceps[0])
            # PR/SC/SP geralmente aparece logo antes ou depois
            for c in unicos[max(0, idx_cep - 3) : idx_cep]:
                if re.match(r"^[A-ZÀ-Ú][a-zA-ZÀ-ú\s]+$", c) and len(c) > 3:
                    cidade = c
                if re.match(r"^[A-Z]{2}$", c):
                    uf = c
        except ValueError:
            pass

    return {
        "nome":         nome_curto,
        "razao_social": razao_social,
        "cnpj":         cnpj,
        "cpf":          cpf,
        "chave_pix":    pix,
        "email":        emails[0] if emails else None,
        "whatsapp":     fones[0] if fones else None,
        "contato":      contato,
        "cidade":       cidade,
        "uf":           uf,
        "cep":          ceps[0] if ceps else None,
        "origem":       doc_path.name,
    }


def criar_tabela():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS fornecedores (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                nome          TEXT NOT NULL,
                razao_social  TEXT,
                cnpj          TEXT,
                cpf           TEXT,
                chave_pix     TEXT,
                email         TEXT,
                whatsapp      TEXT,
                contato       TEXT,
                logradouro    TEXT,
                numero        TEXT,
                bairro        TEXT,
                cidade        TEXT,
                uf            TEXT,
                cep           TEXT,
                origem        TEXT,
                criado_em     TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(cnpj),
                UNIQUE(cpf)
            )
        """)


def inserir(dados):
    doc_id = dados.get("cnpj") or dados.get("cpf")
    if not doc_id and not dados.get("nome"):
        return None

    with sqlite3.connect(DB_PATH) as con:
        # verifica se já existe pelo CNPJ/CPF
        if doc_id:
            col = "cnpj" if dados.get("cnpj") else "cpf"
            row = con.execute(f"SELECT id FROM fornecedores WHERE {col}=?", (doc_id,)).fetchone()
            if row:
                return row[0]  # já existe

        cur = con.execute("""
            INSERT OR IGNORE INTO fornecedores
              (nome, razao_social, cnpj, cpf, chave_pix, email, whatsapp,
               contato, cidade, uf, cep, origem)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            dados["nome"], dados["razao_social"],
            dados["cnpj"], dados["cpf"],
            dados["chave_pix"], dados["email"],
            dados["whatsapp"], dados["contato"],
            dados["cidade"], dados["uf"],
            dados["cep"], dados["origem"],
        ))
        return cur.lastrowid


def main():
    criar_tabela()

    pfms = []
    for pasta in PASTAS:
        if pasta.exists():
            pfms += [f for f in pasta.rglob("*.docx")
                     if any(x in f.name for x in ["GGV01", "GGV02", "GGV03", "PFM"])]
        else:
            print(f"WARN Pasta não encontrada: {pasta}")

    print(f"[PFMs] {len(pfms)} encontrados\n")

    inseridos, ignorados = 0, 0
    for f in sorted(pfms):
        try:
            dados = extrair_fornecedor(f)
            fid = inserir(dados)
            status = "OK" if fid else "JA (já existe)"
            if fid:
                inseridos += 1
            else:
                ignorados += 1
            print(f"{status}  {dados['nome']:<35}  CNPJ: {dados['cnpj'] or dados['cpf'] or '—':<20}  PIX: {dados['chave_pix'] or '—'}")
        except Exception as e:
            print(f"ERR {f.name}: {e}")

    print(f"\nOK {inseridos} inseridos | JA {ignorados} já existiam")


if __name__ == "__main__":
    main()
