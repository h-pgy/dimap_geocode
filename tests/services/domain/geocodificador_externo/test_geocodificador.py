from datetime import UTC, datetime, timedelta

import pytest

from services.domain.geocodificador_externo import (
    ConsultaGeocodificacao,
    EnderecoExternoAttributes,
    EnderecoExternoFeature,
    GeocodificacaoExterna,
    GeocodificacaoExternaInput,
    GeocodificacaoExternaOutput,
    GeocodificadorExterno,
    PoliticaGeocodificacao,
    Precisao,
    Provedor,
    ProvedorGeocodificacao,
    ProvedorIndisponivelError,
    SemResultadoAceitoError,
    ValidacaoGeocodificacaoInput,
    ValidadorGeocodificacao,
)
from services.domain.geometry import PointGeometry

AGORA = datetime(2026, 10, 9, 13, 15, tzinfo=UTC)
TEXTO = "Rua Augusta, 100"


class ProvedorDuble(ProvedorGeocodificacao):
    """Devolve os endereços combinados, ou levanta o erro combinado, e conta as chamadas."""

    provedor = Provedor.GOOGLE

    def __init__(
        self,
        enderecos: list[EnderecoExternoFeature],
        politica: PoliticaGeocodificacao | None = None,
        erro: Exception | None = None,
    ) -> None:
        super().__init__(politica or PoliticaGeocodificacao())
        self._enderecos = enderecos
        self._erro = erro
        self.chamadas = 0

    def __call__(self, consulta: ConsultaGeocodificacao) -> list[EnderecoExternoFeature]:
        self.chamadas += 1
        if self._erro is not None:
            raise self._erro
        return self._enderecos


class CacheDuble:
    """Em memória, uma por chave: satisfaz o CacheGeocodificacaoLike e conta o que foi guardado."""

    def __init__(self, guardadas: list[GeocodificacaoExterna] | None = None) -> None:
        self.guardadas = {g.consulta.chave: g for g in guardadas or []}
        self.gravacoes = 0

    def buscar(self, consulta: ConsultaGeocodificacao) -> GeocodificacaoExterna | None:
        return self.guardadas.get(consulta.chave)

    def guardar(self, geocodificacao: GeocodificacaoExterna) -> None:
        self.gravacoes += 1
        self.guardadas[geocodificacao.consulta.chave] = geocodificacao


class ValidadorQueRecusaTudo(ValidadorGeocodificacao):
    def __call__(self, entrada: ValidacaoGeocodificacaoInput) -> bool:
        return False


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


def _geocodificacao(
    endereco: EnderecoExternoFeature | None = None,
    consultado_em: datetime = AGORA,
) -> GeocodificacaoExterna:
    return GeocodificacaoExterna(
        consulta=ConsultaGeocodificacao(texto=TEXTO),
        endereco=endereco or _endereco_externo(endereco_formatado="guardada"),
        consultado_em=consultado_em,
    )


def _entrada(
    output_crs: int = 4326,
    texto: str = TEXTO,
    agora: datetime = AGORA,
) -> GeocodificacaoExternaInput:
    return GeocodificacaoExternaInput(
        consulta=ConsultaGeocodificacao(texto=texto),
        output_crs=output_crs,
        agora=agora,
    )


def _geocodificar(
    enderecos: list[EnderecoExternoFeature],
    output_crs: int = 4326,
) -> EnderecoExternoFeature:
    saida = GeocodificadorExterno(ProvedorDuble(enderecos))(_entrada(output_crs))
    return saida.geocodificacao.endereco


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


def test_geocodificador_obedece_ao_validador_que_recebe() -> None:
    provedor = ProvedorDuble([_endereco_externo()])
    cache = CacheDuble([_geocodificacao()])
    geocodificador = GeocodificadorExterno(
        provedor,
        cache,
        ValidadorQueRecusaTudo(PoliticaGeocodificacao()),
    )

    with pytest.raises(SemResultadoAceitoError):
        geocodificador(_entrada())

    assert provedor.chamadas == 1
    assert cache.gravacoes == 0


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


def test_geocodificacao_eh_guardada_ja_no_crs_pedido() -> None:
    provedor = ProvedorDuble([_endereco_externo()])
    cache = CacheDuble()
    geocodificador = GeocodificadorExterno(provedor, cache)

    primeira = geocodificador(_entrada(output_crs=31983))
    repetida = geocodificador(_entrada(output_crs=31983))

    assert primeira.geocodificacao.endereco.crs == 31983
    assert [g.endereco.crs for g in cache.guardadas.values()] == [31983]
    assert repetida.geocodificacao.endereco.geometry == primeira.geocodificacao.endereco.geometry


# ---------------------------------------------------------------------------
# Cache: o que é servido sem chamar o provedor
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "intervalo",
    [timedelta(0), timedelta(days=29)],
    ids=["mesmo-instante", "29-dias-depois"],
)
def test_consulta_repetida_dentro_da_validade_nao_chama_o_provedor(intervalo: timedelta) -> None:
    provedor = ProvedorDuble([_endereco_externo()])
    geocodificador = GeocodificadorExterno(provedor, CacheDuble())

    primeira = geocodificador(_entrada())
    segunda = geocodificador(_entrada(agora=AGORA + intervalo))

    assert primeira.cacheada is False
    assert segunda == GeocodificacaoExternaOutput(
        geocodificacao=primeira.geocodificacao,
        cacheada=True,
    )
    assert segunda.geocodificacao.consultado_em == AGORA
    assert provedor.chamadas == 1


@pytest.mark.parametrize(
    ("texto", "chamadas"),
    [
        ("rua augusta 100", 1),
        ("RUA  AUGUSTA,100", 1),
        ("rua augusta, 101", 2),
    ],
    ids=["sem-caixa-nem-virgula", "caixa-alta-e-espacos", "outro-numero"],
)
def test_cache_casa_pela_chave_e_nao_pelo_texto_literal(texto: str, chamadas: int) -> None:
    provedor = ProvedorDuble([_endereco_externo()])
    geocodificador = GeocodificadorExterno(provedor, CacheDuble())

    geocodificador(_entrada(texto="Rua Augusta, 100"))
    geocodificador(_entrada(texto=texto))

    assert provedor.chamadas == chamadas


# ---------------------------------------------------------------------------
# Cache: o que deixa de valer e o que nunca é guardado
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("guardada", "politica"),
    [
        (
            _geocodificacao(consultado_em=AGORA - timedelta(days=30)),
            PoliticaGeocodificacao(),
        ),
        (
            _geocodificacao(consultado_em=AGORA - timedelta(days=7)),
            PoliticaGeocodificacao(validade_dias=7),
        ),
        (
            _geocodificacao(endereco=_endereco_externo(precisao=Precisao.LOGRADOURO)),
            PoliticaGeocodificacao(),
        ),
        (
            _geocodificacao(endereco=_endereco_externo(municipio="Campinas")),
            PoliticaGeocodificacao(),
        ),
    ],
    ids=["30-dias-depois", "7-dias-com-validade-7", "precisao-abaixo-da-minima", "outra-cidade"],
)
def test_guardada_que_nao_vale_mais_eh_refeita_e_sobrescrita(
    guardada: GeocodificacaoExterna,
    politica: PoliticaGeocodificacao,
) -> None:
    nova = _endereco_externo(endereco_formatado="nova")
    provedor = ProvedorDuble([nova], politica)
    cache = CacheDuble([guardada])

    saida = GeocodificadorExterno(provedor, cache)(_entrada())

    assert provedor.chamadas == 1
    assert saida.cacheada is False
    assert list(cache.guardadas.values()) == [
        GeocodificacaoExterna(
            consulta=ConsultaGeocodificacao(texto=TEXTO),
            endereco=nova,
            consultado_em=AGORA,
        )
    ]


@pytest.mark.parametrize(
    ("erro_do_provedor", "erro_esperado"),
    [
        (None, SemResultadoAceitoError),
        (ProvedorIndisponivelError("cota"), ProvedorIndisponivelError),
    ],
    ids=["sem-resultado-aceito", "provedor-indisponivel"],
)
def test_falha_do_provedor_nao_eh_guardada(
    erro_do_provedor: Exception | None,
    erro_esperado: type[Exception],
) -> None:
    provedor = ProvedorDuble([], erro=erro_do_provedor)
    cache = CacheDuble()
    geocodificador = GeocodificadorExterno(provedor, cache)

    with pytest.raises(erro_esperado):
        geocodificador(_entrada())
    with pytest.raises(erro_esperado):
        geocodificador(_entrada())

    assert cache.guardadas == {}
    assert provedor.chamadas == 2
