import pytest
from pydantic import ValidationError

from services.domain.address_geocod import (
    AddressGeocodInput,
    AddressGeocoder,
    EnderecoAttributes,
    NumeracaoNaoEncontradaError,
    SegmentoNaoEncontradoError,
)
from services.domain.geometry import PointGeometry
from services.domain.logradouro_geocod import (
    LogradouroGeocodInput,
    SegmentoLogradouroFeature,
)

# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

CODLOG = "156566"


def _seg(
    id_segmento: str,
    coords: list[list[float]],
    *,
    inicial_par: int | None = None,
    final_par: int | None = None,
    inicial_impar: int | None = None,
    final_impar: int | None = None,
    crs: int = 31983,
    tipo: str = "LineString",
) -> SegmentoLogradouroFeature:
    return SegmentoLogradouroFeature(
        geometry={"type": tipo, "coordinates": coords},  # type: ignore[arg-type]
        attributes={
            "id_segmento": id_segmento,
            "codlog": CODLOG,
            "cd_tipo_logradouro": "AV",
            "nome_logradouro": "PAULISTA",
            "titulo": "DR",
            "preposicao": None,
            "numero_inicial_par": inicial_par,
            "numero_final_par": final_par,
            "numero_inicial_impar": inicial_impar,
            "numero_final_impar": final_impar,
        },  # type: ignore[arg-type]
        crs=crs,
    )


class _FakeLogradouroGeocoder:
    """Substitui o LogradouroGeocoder na fronteira de composição — sem rede.
    Registra a entrada recebida para permitir asserts sobre o CRS pedido."""

    def __init__(self, segmentos: list[SegmentoLogradouroFeature]) -> None:
        self._segmentos = segmentos
        self.entrada_recebida: LogradouroGeocodInput | None = None

    def __call__(self, entrada: LogradouroGeocodInput) -> list[SegmentoLogradouroFeature]:
        self.entrada_recebida = entrada
        return self._segmentos


def _entrada(
    numero: int,
    *,
    codlog: str = CODLOG,
    interpolation_crs: int = 31983,
    output_crs: int = 4326,
) -> AddressGeocodInput:
    return AddressGeocodInput(
        codlog=codlog,
        numero=numero,
        layer_name="segmento_logradouro",
        interpolation_crs=interpolation_crs,
        output_crs=output_crs,
    )


# Rua reta sobre o eixo x, numeração crescente da esquerda para a direita.
def _rua_reta() -> list[SegmentoLogradouroFeature]:
    return [
        _seg("SEG1", [[0.0, 0.0], [100.0, 0.0]], inicial_impar=1, final_impar=49,
             inicial_par=2, final_par=50),
        _seg("SEG2", [[100.0, 0.0], [200.0, 0.0]], inicial_impar=51, final_impar=99,
             inicial_par=52, final_par=100),
    ]


# ---------------------------------------------------------------------------
# AddressGeocodInput — validação
# ---------------------------------------------------------------------------


def test_input_rejeita_numero_zero() -> None:
    with pytest.raises(ValidationError):
        _entrada(0)


def test_input_rejeita_numero_negativo() -> None:
    with pytest.raises(ValidationError):
        _entrada(-5)


# ---------------------------------------------------------------------------
# Composição: pede segmentos no CRS de interpolação
# ---------------------------------------------------------------------------


def test_busca_segmentos_no_crs_de_interpolacao() -> None:
    fake = _FakeLogradouroGeocoder(_rua_reta())
    AddressGeocoder(fake)(_entrada(51, interpolation_crs=31983, output_crs=4326))
    assert fake.entrada_recebida is not None
    assert fake.entrada_recebida.output_crs == 31983  # pediu no CRS de interpolação
    assert fake.entrada_recebida.codlog == CODLOG


def test_resultado_e_endereco_feature() -> None:
    resultado = AddressGeocoder(_FakeLogradouroGeocoder(_rua_reta()))(_entrada(51))
    # EnderecoFeature é um GeoFeature parametrizado (não dá isinstance direto): verifica a
    # composição das três camadas — PointGeometry + EnderecoAttributes + crs.
    assert isinstance(resultado.geometry, PointGeometry)
    assert resultado.geometry.type == "Point"
    assert isinstance(resultado.attributes, EnderecoAttributes)


# ---------------------------------------------------------------------------
# Paridade
# ---------------------------------------------------------------------------


def test_numero_par_usa_colunas_par() -> None:
    # só o lado PAR tem numeração cobrindo 50; o ímpar está deslocado
    seg = _seg("S", [[0.0, 0.0], [100.0, 0.0]], inicial_par=2, final_par=100,
               inicial_impar=1001, final_impar=1099)
    resultado = AddressGeocoder(_FakeLogradouroGeocoder([seg]))(
        _entrada(50, interpolation_crs=31983, output_crs=31983)
    )
    # 50 par -> proporção (50-2)/(100-2) ~ 0.4898 -> x ~ 48.98
    assert resultado.geometry.coordinates[0] == pytest.approx(48.9795, abs=1e-3)


def test_numero_impar_usa_colunas_impar() -> None:
    seg = _seg("S", [[0.0, 0.0], [100.0, 0.0]], inicial_par=1002, final_par=1100,
               inicial_impar=1, final_impar=99)
    resultado = AddressGeocoder(_FakeLogradouroGeocoder([seg]))(
        _entrada(51, interpolation_crs=31983, output_crs=31983)
    )
    # 51 ímpar -> proporção (51-1)/(99-1) ~ 0.5102 -> x ~ 51.02
    assert resultado.geometry.coordinates[0] == pytest.approx(51.0204, abs=1e-3)


def test_descarta_segmento_sem_numeracao_do_lado_buscado() -> None:
    # número par: o segmento tem só numeração ímpar -> deve ser descartado -> nenhum resta
    seg = _seg("S", [[0.0, 0.0], [100.0, 0.0]], inicial_impar=1, final_impar=99)
    with pytest.raises(NumeracaoNaoEncontradaError):
        AddressGeocoder(_FakeLogradouroGeocoder([seg]))(_entrada(50))


def test_descarta_segmento_com_um_lado_par_nulo() -> None:
    # inicial_par presente mas final_par nulo -> lado par incompleto -> descartado
    seg = _seg("S", [[0.0, 0.0], [100.0, 0.0]], inicial_par=2, final_par=None,
               inicial_impar=1, final_impar=99)
    with pytest.raises(NumeracaoNaoEncontradaError):
        AddressGeocoder(_FakeLogradouroGeocoder([seg]))(_entrada(50))


# ---------------------------------------------------------------------------
# Seleção do segmento
# ---------------------------------------------------------------------------


def test_seleciona_segmento_que_contem_o_numero() -> None:
    # 75 ímpar cai no SEG2 (51..99)
    resultado = AddressGeocoder(_FakeLogradouroGeocoder(_rua_reta()))(
        _entrada(75, interpolation_crs=31983, output_crs=31983)
    )
    assert resultado.attributes.id_segmento == "SEG2"


def test_numero_no_primeiro_segmento() -> None:
    resultado = AddressGeocoder(_FakeLogradouroGeocoder(_rua_reta()))(
        _entrada(13, interpolation_crs=31983, output_crs=31983)
    )
    assert resultado.attributes.id_segmento == "SEG1"


def test_numero_fora_de_todos_levanta_numeracao_nao_encontrada() -> None:
    with pytest.raises(NumeracaoNaoEncontradaError):
        AddressGeocoder(_FakeLogradouroGeocoder(_rua_reta()))(_entrada(9999))


def test_codlog_sem_segmentos_levanta_segmento_nao_encontrado() -> None:
    with pytest.raises(SegmentoNaoEncontradoError):
        AddressGeocoder(_FakeLogradouroGeocoder([]))(_entrada(51))


def test_multiplos_segmentos_contendo_o_numero_usa_o_primeiro() -> None:
    seg_a = _seg("A", [[0.0, 0.0], [100.0, 0.0]], inicial_impar=1, final_impar=99)
    seg_b = _seg("B", [[100.0, 0.0], [200.0, 0.0]], inicial_impar=1, final_impar=99)
    resultado = AddressGeocoder(_FakeLogradouroGeocoder([seg_a, seg_b]))(_entrada(51))
    assert resultado.attributes.id_segmento == "A"


# ---------------------------------------------------------------------------
# Interpolação
# ---------------------------------------------------------------------------


def test_proporcao_geral() -> None:
    # SEG2 impar 51..99, numero 75 -> (75-51)/(99-51)=0.5 -> meio do SEG2 (100..200) = 150
    resultado = AddressGeocoder(_FakeLogradouroGeocoder(_rua_reta()))(
        _entrada(75, interpolation_crs=31983, output_crs=31983)
    )
    assert resultado.geometry.coordinates == pytest.approx([150.0, 0.0])


def test_intervalo_degenerado_usa_ponto_medio() -> None:
    # inicial == final -> proporção 0.5 (ponto médio), sem divisão por zero
    seg = _seg("S", [[0.0, 0.0], [100.0, 0.0]], inicial_impar=51, final_impar=51)
    resultado = AddressGeocoder(_FakeLogradouroGeocoder([seg]))(
        _entrada(51, interpolation_crs=31983, output_crs=31983)
    )
    assert resultado.geometry.coordinates == pytest.approx([50.0, 0.0])


def test_ponto_reprojetado_para_output_crs() -> None:
    # segmento em coordenadas UTM 23S plausíveis; saída 4326 deve cair em São Paulo
    seg = _seg("S", [[333000.0, 7395000.0], [333100.0, 7395000.0]],
               inicial_impar=1, final_impar=99)
    resultado = AddressGeocoder(_FakeLogradouroGeocoder([seg]))(
        _entrada(51, interpolation_crs=31983, output_crs=4326)
    )
    lon, lat = resultado.geometry.coordinates
    assert -47.0 < lon < -46.0
    assert -24.0 < lat < -23.0
    assert resultado.crs == 4326


# ---------------------------------------------------------------------------
# Correção de orientação
# ---------------------------------------------------------------------------


def test_orientacao_ja_correta_nao_altera_o_ponto() -> None:
    resultado = AddressGeocoder(_FakeLogradouroGeocoder(_rua_reta()))(
        _entrada(63, interpolation_crs=31983, output_crs=31983)
    )
    # SEG2 51..99, 63 -> proporção 0.25 -> x = 125 (linha 100..200 na ordem correta)
    assert resultado.geometry.coordinates == pytest.approx([125.0, 0.0])


def test_orientacao_invertida_comum_e_corrigida() -> None:
    # SEG2 com coords em ordem invertida (200 -> 100); solver deve reverter
    seg1 = _seg("SEG1", [[0.0, 0.0], [100.0, 0.0]], inicial_impar=1, final_impar=49)
    seg2_rev = _seg("SEG2", [[200.0, 0.0], [100.0, 0.0]], inicial_impar=51, final_impar=99)
    resultado = AddressGeocoder(_FakeLogradouroGeocoder([seg1, seg2_rev]))(
        _entrada(63, interpolation_crs=31983, output_crs=31983)
    )
    # sem correção cairia em 175; corrigido cai em 125
    assert resultado.geometry.coordinates == pytest.approx([125.0, 0.0])


def test_orientacao_invertida_primeiro_segmento_e_corrigida() -> None:
    # o segmento escolhido é o PRIMEIRO da via (usa o posterior como adjacente), invertido
    seg1_rev = _seg("SEG1", [[100.0, 0.0], [0.0, 0.0]], inicial_impar=1, final_impar=49)
    seg2 = _seg("SEG2", [[100.0, 0.0], [200.0, 0.0]], inicial_impar=51, final_impar=99)
    resultado = AddressGeocoder(_FakeLogradouroGeocoder([seg1_rev, seg2]))(
        _entrada(13, interpolation_crs=31983, output_crs=31983)
    )
    # SEG1 1..49, 13 -> proporção 0.25 -> x = 25 (após corrigir a ordem invertida)
    assert resultado.geometry.coordinates == pytest.approx([25.0, 0.0])


# ---------------------------------------------------------------------------
# Borda: geometria MultiLineString
# ---------------------------------------------------------------------------


def test_multilinestring_contiguo_e_fundido_antes_de_interpolar() -> None:
    # dois pedaços contíguos do MESMO segmento -> merge -> linha 0..200; 75 -> 0.5 -> 100
    coords = [[[0.0, 0.0], [100.0, 0.0]], [[100.0, 0.0], [200.0, 0.0]]]
    seg = _seg("S", coords, inicial_impar=51, final_impar=99, tipo="MultiLineString")  # type: ignore[arg-type]
    resultado = AddressGeocoder(_FakeLogradouroGeocoder([seg]))(
        _entrada(75, interpolation_crs=31983, output_crs=31983)
    )
    assert resultado.geometry.coordinates == pytest.approx([100.0, 0.0])


# ---------------------------------------------------------------------------
# Proveniência (attributes)
# ---------------------------------------------------------------------------


def test_attributes_carregam_proveniencia() -> None:
    resultado = AddressGeocoder(_FakeLogradouroGeocoder(_rua_reta()))(
        _entrada(75, interpolation_crs=31983, output_crs=31983)
    )
    a = resultado.attributes
    assert a.codlog == CODLOG
    assert a.nome_logradouro == "PAULISTA"
    assert a.cd_tipo_logradouro == "AV"
    assert a.numero == 75
    assert a.id_segmento == "SEG2"
    assert a.titulo == "DR"


# ---------------------------------------------------------------------------
# Integração — WFS GeoSampa real (Av. Paulista, 300)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestIntegracaoGeoSampa:
    """Geocodifica um endereço real interpolando sobre os segmentos do WFS do GeoSampa.
    Endereço-alvo: Av. Paulista, 300 (codlog 156566). Execute com: pytest -m integration
    """

    # limites grosseiros do município de São Paulo em WGS84
    LON_MIN, LON_MAX = -46.9, -46.3
    LAT_MIN, LAT_MAX = -23.9, -23.4

    def _build_geocoder(self) -> AddressGeocoder:
        from services.domain.logradouro_geocod import LogradouroGeocoder
        from services.integrations.wfs import WfsConnectionConfig, WfsFetcher

        config = WfsConnectionConfig(
            domain="wfs.geosampa.prefeitura.sp.gov.br",
            endpoint="geoserver/geoportal/wfs",
            namespace="geoportal",
        )
        return AddressGeocoder(LogradouroGeocoder(WfsFetcher(config)))

    def _paulista_300(self) -> AddressGeocodInput:
        # interpola em UTM 23S (métrico, nativo do GeoSampa) e entrega em WGS84
        return AddressGeocodInput(
            codlog="156566",
            numero=300,
            layer_name="segmento_logradouro",
            interpolation_crs=31983,
            output_crs=4326,
        )

    def test_paulista_300_gera_ponto(self) -> None:
        resultado = self._build_geocoder()(self._paulista_300())
        # imprime as coordenadas para conferência manual (rode com -s para ver o stdout)
        lon, lat = resultado.geometry.coordinates
        print(
            f"\n[integração] Av. Paulista, 300 (codlog 156566) -> "
            f"lon={lon}, lat={lat} | segmento={resultado.attributes.id_segmento}"
        )
        assert resultado.geometry.type == "Point"
        assert resultado.crs == 4326

    def test_paulista_300_ponto_dentro_de_sao_paulo(self) -> None:
        resultado = self._build_geocoder()(self._paulista_300())
        lon, lat = resultado.geometry.coordinates
        assert self.LON_MIN < lon < self.LON_MAX, f"lon fora de SP: {lon}"
        assert self.LAT_MIN < lat < self.LAT_MAX, f"lat fora de SP: {lat}"

    def test_paulista_300_proveniencia(self) -> None:
        resultado = self._build_geocoder()(self._paulista_300())
        a = resultado.attributes
        assert a.codlog == "156566"
        assert a.numero == 300
        assert a.id_segmento           # segmento de origem preenchido
        assert a.nome_logradouro       # nome do logradouro preenchido
