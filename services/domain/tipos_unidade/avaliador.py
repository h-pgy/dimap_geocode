"""
As regras dos atos sobre o catálogo de tipos de unidade (SPEC user_admin/031): o que a edição pode
tocar, e o veredito de extinguir/reativar. Domínio puro — recebem a prévia já projetada e devolvem
o resultado, sem tocar em banco nem em Django.
"""

from .models import (
    PreviaDaEdicaoTipoUnidade,
    PreviaDaExtincaoTipoUnidade,
    PreviaDaReativacaoTipoUnidade,
    TravasDaEdicaoTipoUnidade,
    Veredito,
)

MOTIVO_JA_EXTINTO = "Este tipo de unidade já está extinto."
MOTIVO_JA_VIGENTE = "Este tipo de unidade não está extinto."


class AvaliadorEdicaoTipoUnidade:
    """Estrutura travada quando há unidades vinculadas: alterar nível, titularidade ou subordinação
    sob unidades ativas quebraria a árvore ou destituiria titulares sem ato específico."""

    def __call__(self, previa: PreviaDaEdicaoTipoUnidade) -> TravasDaEdicaoTipoUnidade:
        if previa.unidades_ativas == 0:
            return TravasDaEdicaoTipoUnidade(estrutura_travada=False)
        return TravasDaEdicaoTipoUnidade(
            estrutura_travada=True,
            motivo=(
                f"{previa.unidades_ativas} unidade(s) utilizam este tipo. Realoque-as ou extinga-as "
                "antes de alterar nível, permissão de raiz, requisitos de titular ou regras de "
                "subordinação."
            ),
        )


class AvaliadorExtincaoTipoUnidade:
    def __call__(self, previa: PreviaDaExtincaoTipoUnidade) -> Veredito:
        # Unidade vinculada não impede: o tipo entra em extinção e as unidades seguem sob ele.
        if previa.ja_extinto:
            return Veredito(pode=False, motivo=MOTIVO_JA_EXTINTO)
        return Veredito(pode=True)


class AvaliadorReativacaoTipoUnidade:
    def __call__(self, previa: PreviaDaReativacaoTipoUnidade) -> Veredito:
        if previa.ja_vigente:
            return Veredito(pode=False, motivo=MOTIVO_JA_VIGENTE)
        return Veredito(pode=True)


# A classe é o passo, o nome minúsculo é a porta — reexportados pelo `__init__.py` do submódulo.
avaliar_edicao_tipo = AvaliadorEdicaoTipoUnidade()
avaliar_extincao_tipo = AvaliadorExtincaoTipoUnidade()
avaliar_reativacao_tipo = AvaliadorReativacaoTipoUnidade()
