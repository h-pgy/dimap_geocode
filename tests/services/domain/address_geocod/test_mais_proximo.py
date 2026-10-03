import math

import pytest

from services.domain.address_geocod import (
    AddressGeocodInput,
    AddressGeocoder,
    EnderecoFeature,
    EnderecoMaisProximo,
    EnderecoMaisProximoInput,
    NenhumSegmentoNumeradoNoRaioError,
)
from services.domain.geometry import LineGeometry, PointGeometry
from services.domain.logradouro_geocod import (
    LogradouroGeocodInput,
    SegmentoLogradouroAttributes,
    SegmentoLogradouroFeature,
    SegmentoProximo,
    SegmentosNoRaioInput,
)

CODLOG = "156566"
CRS_METRICO = 31983

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _segmento(
    id_segmento: str,
    coords: list[list[float]],
    *,
    par: tuple[int, int] | None = None,
    impar: tuple[int, int] | None = None,
) -> SegmentoLogradouroFeature:
    return SegmentoLogradouroFeature(
        geometry=LineGeometry(type="LineString", coordinates=coords),
        attributes=SegmentoLogradouroAttributes(
            id_segmento=id_segmento,
            codlog=CODLOG,
            tipo_logradouro="AV",
            nome_logradouro="PAULISTA",
            numero_inicial_par=None if par is None else par[0],
            numero_final_par=None if par is None else par[1],
            numero_inicial_impar=None if impar is None else impar[0],
            numero_final_impar=None if impar is None else impar[1],
        ),
        crs=CRS_METRICO,
    )


# Rua sobre o eixo x, numeração crescendo para leste. O primeiro segmento vem com a geometria
# invertida, e o 0–0 encosta na ponta errada dele: só o vizinho numerado o orienta certo.
def _rua_com_inicio_invertido() -> list[SegmentoLogradouroFeature]:
    return [
        _segmento("VAZIO", [[100.0, 10.0], [100.0, 30.0]], par=(0, 0), impar=(0, 0)),
        _segmento("INICIO", [[100.0, 0.0], [0.0, 0.0]], par=(2, 50), impar=(1, 49)),
        _segmento("SEGUINTE", [[100.0, 0.0], [200.0, 0.0]], par=(52, 100), impar=(51, 99)),
    ]


def _girar(x: float, y: float, graus: float) -> list[float]:
    angulo = math.radians(graus)
    return [
        x * math.cos(angulo) - y * math.sin(angulo),
        x * math.sin(angulo) + y * math.cos(angulo),
    ]


def _entrada(ponto: list[float]) -> EnderecoMaisProximoInput:
    return EnderecoMaisProximoInput(
        consulta=SegmentosNoRaioInput(
            ponto=PointGeometry(type="Point", coordinates=ponto),
            crs_ponto=CRS_METRICO,
            raio_m=50.0,
            layer_name="segmento_logradouro",
            campo_geometria="ge_linha",
            crs_metrico=CRS_METRICO,
        ),
        output_crs=CRS_METRICO,
    )


class _FakeSegmentosNoRaio:
    """Devolve os segmentos na ordem dada, como se já viessem do mais perto ao mais longe."""

    def __init__(self, segmentos: list[SegmentoLogradouroFeature]) -> None:
        self._segmentos = segmentos

    def __call__(self, entrada: SegmentosNoRaioInput) -> tuple[SegmentoProximo, ...]:
        return tuple(
            SegmentoProximo(segmento=segmento, distancia_m=float(ordem))
            for ordem, segmento in enumerate(self._segmentos)
        )


class _FakeSegmentosDoCodlog:
    def __init__(self, segmentos: list[SegmentoLogradouroFeature]) -> None:
        self._segmentos = segmentos
        self.entradas: list[LogradouroGeocodInput] = []

    def __call__(self, entrada: LogradouroGeocodInput) -> list[SegmentoLogradouroFeature]:
        self.entradas.append(entrada)
        return self._segmentos


def _buscar(
    no_raio: list[SegmentoLogradouroFeature],
    do_codlog: list[SegmentoLogradouroFeature],
    ponto: list[float],
) -> EnderecoFeature:
    buscar_endereco = EnderecoMaisProximo(
        _FakeSegmentosNoRaio(no_raio),
        _FakeSegmentosDoCodlog(do_codlog),
    )
    return buscar_endereco(_entrada(ponto))


def _faixa(endereco: EnderecoFeature) -> tuple[int, int]:
    return (endereco.attributes.numeracao_inicial, endereco.attributes.numeracao_final)


# ---------------------------------------------------------------------------
# Escolha do segmento
# ---------------------------------------------------------------------------


def test_escolhe_o_numerado_mais_perto() -> None:
    sem_numeracao = _segmento("SEM", [[0.0, 2.0], [100.0, 2.0]])
    zerado = _segmento("ZERADO", [[0.0, 4.0], [100.0, 4.0]], par=(0, 0), impar=(0, 0))
    numerado = _segmento("NUMERADO", [[0.0, 10.0], [100.0, 10.0]], par=(2, 50), impar=(1, 49))

    endereco = _buscar([sem_numeracao, zerado, numerado], [numerado], [50.0, 0.0])

    assert endereco.attributes.id_segmento == "NUMERADO"


@pytest.mark.parametrize(
    "no_raio",
    [
        [],
        [
            _segmento("SEM", [[0.0, 2.0], [100.0, 2.0]]),
            _segmento("ZERADO", [[0.0, 4.0], [100.0, 4.0]], par=(0, 0), impar=(0, 0)),
        ],
    ],
    ids=["nenhum", "sem-numeracao"],
)
def test_sem_segmento_numerado_no_raio_levanta_erro_proprio(
    no_raio: list[SegmentoLogradouroFeature],
) -> None:
    segmentos_do_codlog = _FakeSegmentosDoCodlog([])
    buscar_endereco = EnderecoMaisProximo(_FakeSegmentosNoRaio(no_raio), segmentos_do_codlog)

    with pytest.raises(NenhumSegmentoNumeradoNoRaioError):
        buscar_endereco(_entrada([50.0, 0.0]))

    assert segmentos_do_codlog.entradas == []


# ---------------------------------------------------------------------------
# Número e paridade
# ---------------------------------------------------------------------------


def test_numero_acompanha_a_posicao_no_segmento() -> None:
    faixa_cem = _segmento("CEM", [[0.0, 0.0], [100.0, 0.0]], par=(100, 200))
    faixa_zero = _segmento("ZERO", [[0.0, 0.0], [100.0, 0.0]], par=(0, 42))

    a_30 = _buscar([faixa_cem], [faixa_cem], [30.0, -5.0])
    a_30_6 = _buscar([faixa_cem], [faixa_cem], [30.6, -5.0])
    no_inicio = _buscar([faixa_zero], [faixa_zero], [0.0, -5.0])

    assert a_30.attributes.numero == 130
    assert _faixa(a_30) == (100, 200)
    assert a_30_6.attributes.numero == 130
    assert no_inicio.attributes.numero == 2


@pytest.mark.parametrize("graus", [0.0, -90.0, 180.0], ids=["leste", "sul", "oeste"])
def test_lado_do_ponto_decide_a_paridade(graus: float) -> None:
    coords = [_girar(0.0, 0.0, graus), _girar(100.0, 0.0, graus)]
    segmento = _segmento("S", coords, par=(2, 50), impar=(1, 49))

    a_direita = _buscar([segmento], [segmento], _girar(40.0, -5.0, graus))
    a_esquerda = _buscar([segmento], [segmento], _girar(40.0, 5.0, graus))

    assert a_direita.attributes.numero == 22
    assert _faixa(a_direita) == (2, 50)
    assert a_esquerda.attributes.numero == 21
    assert _faixa(a_esquerda) == (1, 49)


def test_segmento_contra_a_numeracao_e_invertido_antes_do_lado() -> None:
    rua = _rua_com_inicio_invertido()
    inicio = rua[1]

    endereco = _buscar([inicio], rua, [25.0, -5.0])

    assert endereco.attributes.numero == 14
    assert _faixa(endereco) == (2, 50)


@pytest.mark.parametrize("par_vazio", [None, (0, 0)], ids=["None", "0-0"])
def test_segmento_de_um_lado_so_devolve_a_paridade_dele(par_vazio: tuple[int, int] | None) -> None:
    so_impar = _segmento("S", [[0.0, 0.0], [100.0, 0.0]], par=par_vazio, impar=(1, 49))

    endereco = _buscar([so_impar], [so_impar], [40.0, -5.0])

    assert endereco.attributes.numero == 21
    assert _faixa(endereco) == (1, 49)


# ---------------------------------------------------------------------------
# Ida e volta com a geocodificação da busca
# ---------------------------------------------------------------------------


def test_ida_e_volta_com_a_geocodificacao() -> None:
    rua = _rua_com_inicio_invertido()
    inicio = rua[1]
    endereco = _buscar([inicio], rua, [25.0, -5.0])

    geocodificar = AddressGeocoder(_FakeSegmentosDoCodlog(rua))
    de_volta = geocodificar(
        AddressGeocodInput(
            codlog=CODLOG,
            numero=endereco.attributes.numero,
            layer_name="segmento_logradouro",
            interpolation_crs=CRS_METRICO,
            output_crs=CRS_METRICO,
        ),
    )

    assert de_volta.geometry.coordinates == pytest.approx(endereco.geometry.coordinates)


# ---------------------------------------------------------------------------
# Integração — WFS GeoSampa real
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIntegracaoGeoSampa:
    """Roda apenas com: uv run pytest -m integration"""

    def test_endereco_mais_proximo_no_geosampa(self) -> None:
        from services.domain.logradouro_geocod import LogradouroGeocoder, SegmentosNoRaio
        from services.integrations.wfs import WfsConnectionConfig, WfsFetcher

        config = WfsConnectionConfig(
            domain="wfs.geosampa.prefeitura.sp.gov.br",
            endpoint="geoserver/geoportal/wfs",
            namespace="geoportal",
        )
        fetcher = WfsFetcher(config)
        buscar_endereco = EnderecoMaisProximo(SegmentosNoRaio(fetcher), LogradouroGeocoder(fetcher))
        # Pista par da Av. Paulista em frente ao MASP: na calçada, a Esplanada Lina Bo Bardi e o
        # túnel sob o museu ficam mais perto.
        entrada = EnderecoMaisProximoInput(
            consulta=SegmentosNoRaioInput(
                ponto=PointGeometry(type="Point", coordinates=[-46.65594, -23.56182]),
                crs_ponto=4326,
                raio_m=50.0,
                layer_name="segmento_logradouro",
                campo_geometria="ge_linha",
                crs_metrico=CRS_METRICO,
            ),
            output_crs=4326,
        )

        endereco = buscar_endereco(entrada)

        assert endereco.attributes.logradouro.codlog == "156566"
        assert endereco.attributes.numero % 2 == 0
        assert 1576 <= endereco.attributes.numero <= 1590
