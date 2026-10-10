import pytest

from services.domain.geometry import LineGeometry, reprojetar
from services.domain.logradouro_geocod import (
    GavetaLogradouroInput,
    MontarGavetaLogradouro,
    SegmentoLogradouroAttributes,
    SegmentoLogradouroFeature,
)

CRS_MAPA = 4326
CRS_METRICO = 31983

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _eixo_no_mapa(comprimento_m: float) -> LineGeometry:
    x0 = 333000.0
    y0 = 7395000.0
    metrico = LineGeometry(type="LineString", coordinates=[[x0, y0], [x0 + comprimento_m, y0]])
    return reprojetar(metrico, CRS_METRICO, CRS_MAPA)


def _segmento(
    comprimento_m: float,
    par: tuple[int | None, int | None] = (None, None),
    impar: tuple[int | None, int | None] = (None, None),
) -> SegmentoLogradouroFeature:
    return SegmentoLogradouroFeature(
        geometry=_eixo_no_mapa(comprimento_m),
        attributes=SegmentoLogradouroAttributes(
            id_segmento="SEG",
            codlog="156566",
            tipo_logradouro="AV",
            nome_logradouro="PAULISTA",
            numero_inicial_par=par[0],
            numero_final_par=par[1],
            numero_inicial_impar=impar[0],
            numero_final_impar=impar[1],
        ),
        crs=CRS_MAPA,
    )


# ---------------------------------------------------------------------------
# O logradouro inteiro: extensão e numeração somadas de todos os segmentos
# ---------------------------------------------------------------------------


def test_gaveta_logradouro_apura_extensao_e_numeracao_do_logradouro_inteiro() -> None:
    montar_gaveta = MontarGavetaLogradouro()
    segmentos = [
        _segmento(30.0, par=(2, 10), impar=(0, 0)),
        _segmento(40.0, impar=(1, 25)),
    ]

    gaveta = montar_gaveta(GavetaLogradouroInput(segmentos=segmentos, crs_metrico=CRS_METRICO))

    assert gaveta.extensao_m == pytest.approx(70.0, abs=0.01)
    assert gaveta.quantidade_segmentos == 2
    assert gaveta.numeracao is not None
    assert gaveta.numeracao.menor == 1
    assert gaveta.numeracao.maior == 25
    assert gaveta.logradouro.nome_completo == "AV PAULISTA"

    sem_numeracao = [
        _segmento(30.0),
        _segmento(40.0, par=(0, 0)),
    ]

    gaveta_sem_numeracao = montar_gaveta(
        GavetaLogradouroInput(segmentos=sem_numeracao, crs_metrico=CRS_METRICO),
    )

    assert gaveta_sem_numeracao.numeracao is None
