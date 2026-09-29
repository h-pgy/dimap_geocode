import pytest

from services.domain.geocodificador_externo import (
    ConsultaGeocodificacao,
    EnderecoExternoAttributes,
    EnderecoExternoFeature,
    GeocodificacaoExternaInput,
    GeocodificadorExterno,
    PoliticaGeocodificacao,
    Precisao,
    Provedor,
    ProvedorGeocodificacao,
    SemResultadoAceitoError,
)
from services.domain.geometry import PointGeometry


class ProvedorDuble(ProvedorGeocodificacao):
    """Um provedor qualquer que implementa a porta: devolve os endereços combinados, na ordem."""

    provedor = Provedor.GOOGLE

    def __init__(self, enderecos: list[EnderecoExternoFeature]) -> None:
        super().__init__(PoliticaGeocodificacao())
        self._enderecos = enderecos

    def __call__(self, consulta: ConsultaGeocodificacao) -> list[EnderecoExternoFeature]:
        return self._enderecos


def _endereco_externo(
    precisao: Precisao = Precisao.IMOVEL,
    municipio: str | None = "São Paulo",
    uf: str | None = "SP",
    endereco_formatado: str = "R. Augusta, 100 - São Paulo - SP",
) -> EnderecoExternoFeature:
    return EnderecoExternoFeature(
        geometry=PointGeometry(type="Point", coordinates=[-46.6522, -23.5537]),
        attributes=EnderecoExternoAttributes(
            endereco_formatado=endereco_formatado,
            municipio=municipio,
            uf=uf,
            provedor=Provedor.GOOGLE,
            precisao=precisao,
        ),
        crs=4326,
    )


def _entrada(output_crs: int = 4326) -> GeocodificacaoExternaInput:
    return GeocodificacaoExternaInput(
        consulta=ConsultaGeocodificacao(texto="rua augusta, 100"),
        output_crs=output_crs,
    )


def _geocodificar(
    enderecos: list[EnderecoExternoFeature],
    output_crs: int = 4326,
) -> EnderecoExternoFeature:
    return GeocodificadorExterno(ProvedorDuble(enderecos))(_entrada(output_crs))


# ---------------------------------------------------------------------------
# Regras de aceite
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("endereco", "aceito"),
    [
        (_endereco_externo(precisao=Precisao.LOGRADOURO), False),
        (_endereco_externo(municipio="Campinas"), False),
        (_endereco_externo(uf="RJ"), False),
        (_endereco_externo(municipio=None), False),
        (_endereco_externo(precisao=Precisao.INTERPOLADA, municipio="Sao Paulo"), True),
    ],
    ids=["logradouro", "outra-cidade", "outro-estado", "sem-municipio", "sem-acento"],
)
def test_geocodificador_descarta_resultado_fora_da_politica(
    endereco: EnderecoExternoFeature,
    aceito: bool,
) -> None:
    if aceito:
        assert _geocodificar([endereco]) == endereco
    else:
        with pytest.raises(SemResultadoAceitoError):
            _geocodificar([endereco])


def test_geocodificador_escolhe_a_maior_precisao_e_desempata_pela_ordem() -> None:
    interpolada = _endereco_externo(precisao=Precisao.INTERPOLADA, endereco_formatado="interpolada")
    primeiro_imovel = _endereco_externo(endereco_formatado="primeiro imóvel")
    segundo_imovel = _endereco_externo(endereco_formatado="segundo imóvel")

    escolhido = _geocodificar([interpolada, primeiro_imovel, segundo_imovel])

    assert escolhido.attributes.endereco_formatado == "primeiro imóvel"


@pytest.mark.parametrize(
    "enderecos",
    [[], [_endereco_externo(municipio="Campinas"), _endereco_externo(precisao=Precisao.APROXIMADA)]],
    ids=["lista-vazia", "so-descartados"],
)
def test_sem_resultado_aceito_levanta_erro_proprio(enderecos: list[EnderecoExternoFeature]) -> None:
    with pytest.raises(SemResultadoAceitoError):
        _geocodificar(enderecos)


# ---------------------------------------------------------------------------
# CRS de saída
# ---------------------------------------------------------------------------


def test_geocodificador_entrega_no_crs_pedido() -> None:
    escolhido = _geocodificar([_endereco_externo()], output_crs=31983)

    assert escolhido.crs == 31983
    x, y = escolhido.geometry.coordinates
    # UTM 23S em São Paulo: centenas de milhares de metros a leste, milhões ao norte
    assert 300_000 < x < 360_000
    assert 7_380_000 < y < 7_420_000
