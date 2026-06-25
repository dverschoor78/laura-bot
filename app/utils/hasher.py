"""
hasher.py — Calcula hash SHA256 de arquivos.

Usado para idempotência: detectar se o mesmo arquivo foi enviado duas vezes.
"""

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Retorna o hash SHA256 do arquivo como string hexadecimal."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Retorna o hash SHA256 de bytes em memória."""
    return hashlib.sha256(data).hexdigest()
