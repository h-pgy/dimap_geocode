"""
Quem dirige a unidade hoje (SPEC user_admin/014): leitura derivada das marcas de titularidade e
exercício, sem tocar banco.
"""

from services.domain.titularidade.models import Direcao, EstadoDaDirecao


class AvaliadorDirecao:
    """Quem dirige a unidade hoje — e, quando ninguém dirige, qual das duas faltas é."""

    def __call__(self, estado: EstadoDaDirecao) -> Direcao:
        # A vaga responde antes de qualquer marca de exercício: não há de quem consultá-la.
        if not estado.tem_titular:
            return Direcao.SEM_TITULAR
        if estado.titular_em_exercicio:
            return Direcao.TITULAR
        if estado.substituto_do_titular_em_exercicio:
            return Direcao.SUBSTITUTO
        return Direcao.SEM_DIRECAO


def avaliar_direcao(estado: EstadoDaDirecao) -> Direcao:
    return AvaliadorDirecao()(estado)
