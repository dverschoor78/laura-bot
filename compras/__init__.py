"""
Domínio de Compras — Lista de Compras (momento "antes da compra").

Contrato conceitual: docs/POLITICA_COMPRAS.md, docs/CASOS_DE_USO_COMPRAS.md,
docs/MODELO_DOMINIO_COMPRAS.md.

Fiada 1: criar e consultar Lista de Compras, com sugestão de itens baseada em
histórico real (nunca inventada). Sem vínculo com orçamento, sem alertas
proativos, sem alteração no fluxo orçamento -> pedido existente.
"""

from .lista import (
    init_db_compras,
    criar_ou_buscar_lista_aberta,
    buscar_lista_aberta,
    buscar_lista,
    atualizar_lista,
    sugerir_itens,
    adicionar_item,
    remover_item,
    listar_itens,
    StatusLista,
    StatusItem,
    GrauConfianca,
    OrigemReferencia,
)
