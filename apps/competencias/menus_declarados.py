"""
Os menus declarados no código (SPEC autorizacao/005): cada um pinça as ações que exibe — a ação não
se inscreve em menu algum. Nenhuma tela renderiza `MENU_ADMINISTRADOR` nesta iteração (SPEC
autorizacao/007, §4, e SPEC user_admin/022, §4): onde ele aparece na área administrativa é decisão
de outra SPEC.
"""

from apps.user_admin.acoes_declaradas import (
    ACAO_DESIGNAR_SUBSTITUTO,
    ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR,
    ACAO_TORNAR_ADMINISTRADOR,
)
from services.domain.autorizacao import VarianteIcone

from .acoes_declaradas import ACAO_CONCEDER, ACAO_DEFINIR_ATRIBUICAO
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
        ItemDeMenu(
            acao_implementada=ACAO_CONCEDER,
            variante_icone=VarianteIcone.PEQUENO,
            forma=FormaItem.LINHA,
        ),
        # O caminho direto para a ação (SPEC user_admin/022): mesmo item genérico, sem escolher
        # alvo nenhum ainda — é a tela que abre quem escolhe.
        ItemDeMenu(
            acao_implementada=ACAO_TORNAR_ADMINISTRADOR,
            variante_icone=VarianteIcone.PEQUENO,
            forma=FormaItem.LINHA,
        ),
        # O caminho direto para o ato (SPEC user_admin/023): a tela que abre é quem escolhe a
        # unidade e, dentro dela, o servidor.
        ItemDeMenu(
            acao_implementada=ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR,
            variante_icone=VarianteIcone.PEQUENO,
            forma=FormaItem.LINHA,
        ),
        # O caminho direto para designar substituto (SPEC user_admin/024).
        ItemDeMenu(
            acao_implementada=ACAO_DESIGNAR_SUBSTITUTO,
            variante_icone=VarianteIcone.PEQUENO,
            forma=FormaItem.LINHA,
        ),
    ),
)
