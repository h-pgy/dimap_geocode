"""
As regras dos atos sobre os dois catálogos de cargo (SPECs user_admin/029 e 030): o que a edição
pode tocar, e o veredito de extinguir/reativar. Domínio puro — recebem a prévia já projetada e
devolvem o resultado, sem tocar em banco nem em Django.
"""

from .models import (
    PreviaDaEdicao,
    PreviaDaExtincaoCargo,
    PreviaDaExtincaoCargoBase,
    PreviaDaReativacaoCargo,
    PreviaDaReativacaoCargoBase,
    TravasDaEdicao,
    Veredito,
)

MOTIVO_JA_EXTINTO = "Este cargo já está extinto."
MOTIVO_JA_VIGENTE = "Este cargo não está extinto."


class AvaliadorEdicao:
    """O que a edição pode tocar. Natureza é nível + chefia + alta administração: mudá-la sob um
    ocupante mudaria, sem ato nenhum, a competência que ele exerce e a unidade que ele titulariza."""

    def __call__(self, previa: PreviaDaEdicao) -> TravasDaEdicao:
        if previa.ocupantes == 0:
            return TravasDaEdicao(natureza_travada=False)
        return TravasDaEdicao(
            natureza_travada=True,
            motivo=(
                f"{previa.ocupantes} servidor(es) ocupam este cargo. Exonere-os antes de alterar "
                "nível, natureza ou alta administração."
            ),
        )


class AvaliadorExtincaoCargo:
    def __call__(self, previa: PreviaDaExtincaoCargo) -> Veredito:
        # Ocupante não impede: o cargo entra em extinção e vai esvaziando conforme as exonerações.
        if previa.ja_extinto:
            return Veredito(pode=False, motivo=MOTIVO_JA_EXTINTO)
        return Veredito(pode=True)


class AvaliadorReativacaoCargo:
    def __call__(self, previa: PreviaDaReativacaoCargo) -> Veredito:
        if previa.ja_vigente:
            return Veredito(pode=False, motivo=MOTIVO_JA_VIGENTE)
        return Veredito(pode=True)


class AvaliadorExtincaoCargoBase:
    """Mesma regra de `AvaliadorExtincaoCargo`, para o catálogo de cargo base (SPEC user_admin/030,
    Caveats): generalizar exigiria uma identidade comum aos dois catálogos, acoplando cargo base ao
    `padrao` que só `CargoComissao` tem."""

    def __call__(self, previa: PreviaDaExtincaoCargoBase) -> Veredito:
        if previa.ja_extinto:
            return Veredito(pode=False, motivo=MOTIVO_JA_EXTINTO)
        return Veredito(pode=True)


class AvaliadorReativacaoCargoBase:
    def __call__(self, previa: PreviaDaReativacaoCargoBase) -> Veredito:
        if previa.ja_vigente:
            return Veredito(pode=False, motivo=MOTIVO_JA_VIGENTE)
        return Veredito(pode=True)


# Instâncias de módulo, no padrão de `extincao_unidade`: a classe é o passo, o nome minúsculo é a
# porta. Reexportadas pelo `__init__.py` do submódulo, que é por onde `apps/` importa (§7.2).
avaliar_edicao = AvaliadorEdicao()
avaliar_extincao_cargo = AvaliadorExtincaoCargo()
avaliar_reativacao_cargo = AvaliadorReativacaoCargo()
avaliar_extincao_cargo_base = AvaliadorExtincaoCargoBase()
avaliar_reativacao_cargo_base = AvaliadorReativacaoCargoBase()
