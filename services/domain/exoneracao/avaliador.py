"""
As duas regras que decidem se o ato pode acontecer (SPEC user_admin/027): só sai do quadro quem
está nele e não é quem assina, e só volta quem está fora e tem lotação de pé para onde voltar.
Domínio puro — recebem a prévia já projetada e devolvem o veredito, sem tocar em banco nem em
Django.
"""

from .models import PreviaDaExoneracao, PreviaDaReintegracao, Veredito

MOTIVO_JA_EXONERADO = "Este servidor já foi exonerado."
MOTIVO_NO_QUADRO = "Este servidor não está exonerado."
MOTIVO_AUTO_EXONERACAO = (
    "Você não pode exonerar a si mesmo: peça a quem dirige a unidade superior."
)
MOTIVO_UNIDADE_EXTINTA = "Reative antes a {sigla}: um servidor não é lotado em unidade extinta."


class AvaliadorExoneracao:
    def __call__(self, previa: PreviaDaExoneracao) -> Veredito:
        # Antes de tudo: o POST repetido chega com o servidor já fora do quadro.
        if previa.ja_exonerado:
            return Veredito(pode=False, motivo=MOTIVO_JA_EXONERADO)
        if previa.eh_o_proprio_autor:
            return Veredito(pode=False, motivo=MOTIVO_AUTO_EXONERACAO)
        return Veredito(pode=True)


class AvaliadorReintegracao:
    def __call__(self, previa: PreviaDaReintegracao) -> Veredito:
        if previa.ja_no_quadro:
            return Veredito(pode=False, motivo=MOTIVO_NO_QUADRO)
        if previa.unidade_extinta:
            return Veredito(
                pode=False,
                motivo=MOTIVO_UNIDADE_EXTINTA.format(sigla=previa.unidade),
            )
        return Veredito(pode=True)


# Instâncias de módulo, no padrão do `avaliar_extincao`: a classe é o passo, o nome minúsculo é a
# porta. Reexportadas pelo `__init__.py` do submódulo, que é por onde `apps/` importa (§7.2).
avaliar_exoneracao = AvaliadorExoneracao()
avaliar_reintegracao = AvaliadorReintegracao()
