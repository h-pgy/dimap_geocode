"""
Quem pode cobrir quem, e quando (SPEC user_admin/015). Sem Django: a mesma regra responde ao
`clean()` da substituição, à lista de candidatos da tela e ao teste.
"""

from services.domain.exercicio.models import Designacao, Periodo
from services.domain.exercicio.periodos import contem, se_sobrepoem


class AvaliadorDesignacao:
    """A regra é uma só e é não-sobreposição, dos dois lados — mais o que cada papel exige de si."""

    def __call__(self, designacao: Designacao) -> bool:
        return self.pipeline(designacao)

    def pipeline(self, designacao: Designacao) -> bool:
        return (
            self._periodo_cabe_no_afastamento(designacao)
            and self._substituido_apto(designacao)
            and self._substituto_livre(designacao)
        )

    def _periodo_cabe_no_afastamento(self, designacao: Designacao) -> bool:
        # Substituir quem está na cadeira não é substituir: a cobertura só estreita o afastamento.
        return contem(designacao.periodo_do_impedimento, designacao.periodo)

    def _substituido_apto(self, designacao: Designacao) -> bool:
        substituido = designacao.substituido
        if not substituido.tem_cargo_comissao or substituido.exonerado:
            return False
        return self._livre_de(designacao.periodo, substituido.substituicoes_recebidas)

    def _substituto_livre(self, designacao: Designacao) -> bool:
        substituto = designacao.substituto
        if substituto.exonerado:
            return False
        if substituto.perfil_id == designacao.substituido.perfil_id:
            return False
        if not self._livre_de(designacao.periodo, substituto.impedimentos):
            return False
        return self._livre_de(designacao.periodo, substituto.substituicoes_exercidas)

    def _livre_de(self, periodo: Periodo, ocupados: tuple[Periodo, ...]) -> bool:
        return not any(se_sobrepoem(periodo, ocupado) for ocupado in ocupados)


def avaliar_designacao(designacao: Designacao) -> bool:
    return AvaliadorDesignacao()(designacao)
