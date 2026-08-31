"""
As duas regras que decidem se o ato pode acontecer (SPEC user_admin/025): só sai quem tem para onde
mandar o que carrega, e só volta quem está fora e tem onde pendurar. Domínio puro — recebem a prévia
já projetada e devolvem o veredito, sem tocar em banco nem em Django.
"""

from .models import PreviaDaExtincao, PreviaDaReativacao, Veredito

MOTIVO_RAIZ = "A unidade raiz não se extingue: não há unidade superior para receber o que ela carrega."
MOTIVO_JA_EXTINTA = "Esta unidade já foi extinta."
MOTIVO_JA_VIGENTE = "Esta unidade não está extinta."
MOTIVO_SUPERIOR_EXTINTA = "Reative antes a {sigla}: uma unidade não pende de unidade extinta."


class AvaliadorExtincao:
    def __call__(self, previa: PreviaDaExtincao) -> Veredito:
        # Antes do destino: o POST repetido chega com a unidade já extinta e o destino ainda de pé.
        if previa.ja_extinta:
            return Veredito(pode=False, motivo=MOTIVO_JA_EXTINTA)
        if previa.destino is None:
            return Veredito(pode=False, motivo=MOTIVO_RAIZ)
        return Veredito(pode=True)


class AvaliadorReativacao:
    def __call__(self, previa: PreviaDaReativacao) -> Veredito:
        if previa.ja_vigente:
            return Veredito(pode=False, motivo=MOTIVO_JA_VIGENTE)
        if previa.superior_extinta:
            return Veredito(
                pode=False,
                motivo=MOTIVO_SUPERIOR_EXTINTA.format(sigla=previa.superior.sigla),
            )
        return Veredito(pode=True)


# Instâncias de módulo, no padrão do `traduzir_recusa`: a classe é o passo, o nome minúsculo é a
# porta. Reexportadas pelo `__init__.py` do submódulo, que é por onde `apps/` importa (§7.2).
avaliar_extincao = AvaliadorExtincao()
avaliar_reativacao = AvaliadorReativacao()
