from typing import Any

from services.domain.documento_selado import ConferenciaInput, EstadoDocumento, classificar_conferencia
from services.utils.assinatura import EstadoSelo, ResultadoConferencia


def _resultado_selo(**overrides: Any) -> ResultadoConferencia:
    defaults: dict[str, object] = {"estado": EstadoSelo.INTEGRO, "envelope": {"codigo": "ABCDEFGHJKMN"}}
    return ResultadoConferencia(**(defaults | overrides))


# ---------------------------------------------------------------------------
# Selo íntegro cujo código não está no acervo é DESCONHECIDO, nunca CONFERE
# ---------------------------------------------------------------------------


def test_selo_integro_de_codigo_ausente_eh_desconhecido() -> None:
    pedido = ConferenciaInput(resultado_selo=_resultado_selo(), registro=None)

    resultado = classificar_conferencia(pedido)

    assert resultado.estado is EstadoDocumento.DESCONHECIDO
    assert resultado.ficha is None
    assert resultado.tem_original is False
    assert resultado.codigo == "ABCDEFGHJKMN"


# ---------------------------------------------------------------------------
# PDF nunca selado é SEM_SELO
# ---------------------------------------------------------------------------


def test_arquivo_sem_selo_eh_sem_selo() -> None:
    pedido = ConferenciaInput(
        resultado_selo=_resultado_selo(estado=EstadoSelo.SEM_SELO, envelope=None),
        registro=None,
    )

    resultado = classificar_conferencia(pedido)

    assert resultado.estado is EstadoDocumento.SEM_SELO
    assert resultado.ficha is None
    assert resultado.codigo is None
    assert resultado.tem_original is False
