"""
Os menus declarados no código (SPEC autorizacao/005): cada um pinça as ações que exibe — a ação não
se inscreve em menu algum. Nenhuma tela renderiza `MENU_ADMINISTRADOR` nesta iteração (SPEC
autorizacao/007, §4): onde ele aparece na área administrativa é decisão de outra SPEC.
"""

from services.domain.autorizacao import VarianteIcone

from .acoes_declaradas import ACAO_DEFINIR_ATRIBUICAO
from .menus import ContratoMenu, FormaItem, ItemDeMenu

MENU_ADMINISTRADOR = ContratoMenu(
    slug="competencias.administrador",
    nome="Administração",
    itens=(
        ItemDeMenu(
            acao_implementada=ACAO_DEFINIR_ATRIBUICAO,
            variante_icone=VarianteIcone.PEQUENO,
            forma=FormaItem.LINHA,
        ),
    ),
)
