"""
Módulo NF-e da Laura.

Domínio: parsing e exibição da Nota Fiscal eletrônica extraída pelo Claude,
e a montagem da tela/teclado de vinculação a um pedido pago sem NF-e.

O matching de candidatos (buscar_candidatos_nfe) e a vinculação em si
(vincular_nfe) já vivem em financeiro/lancamento.py — este módulo cobre só
a camada de parsing/exibição que ainda estava solta em bot.py.

Uso em bot.py:
  from nfe import parse_nfe, mostrar_nfe, teclado_candidatos_nfe

Este módulo não depende de bot.py nem de variáveis de ambiente.
"""
from .nfe import parse_nfe, mostrar_nfe, teclado_candidatos_nfe

__all__ = ["parse_nfe", "mostrar_nfe", "teclado_candidatos_nfe"]
