from datetime import UTC, datetime
from typing import Any

import pytest
from django.conf import settings

from apps.geocodificacao_externa.cache import CacheEmBanco
from apps.geocodificacao_externa.models import GeocodificacaoGuardada
from services.domain.geocodificador_externo import (
    ConsultaGeocodificacao,
    EnderecoExternoAttributes,
    EnderecoExternoFeature,
    GeocodificacaoExterna,
    Precisao,
    Provedor,
)
from services.domain.geometry import PointGeometry

banco = pytest.mark.banco

MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS


def _endereco_externo(**overrides: Any) -> EnderecoExternoFeature:
    # número, bairro e CEP ficam ausentes de propósito: é ausentes que precisam voltar do banco
    defaults: dict[str, Any] = {
        "endereco_formatado": "R. Augusta - São Paulo - SP",
        "logradouro": "Rua Augusta",
        "municipio": "São Paulo",
        "uf": "SP",
        "provedor": Provedor.GOOGLE,
        "precisao": Precisao.IMOVEL,
    }
    return EnderecoExternoFeature(
        geometry=PointGeometry(type="Point", coordinates=[-46.6522, -23.5537]),
        attributes=EnderecoExternoAttributes(**(defaults | overrides)),
        crs=MAP_OUTPUT_CRS,
    )


def _geocodificacao(
    texto: str = "Rua Augusta, 100",
    endereco: EnderecoExternoFeature | None = None,
    consultado_em: datetime = datetime(2026, 10, 2, 17, 32, tzinfo=UTC),
) -> GeocodificacaoExterna:
    return GeocodificacaoExterna(
        consulta=ConsultaGeocodificacao(texto=texto),
        endereco=endereco or _endereco_externo(),
        consultado_em=consultado_em,
    )


# ---------------------------------------------------------------------------
# Guardar e buscar
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_cache_em_banco_devolve_o_que_guardou() -> None:
    geocodificacao = _geocodificacao()
    cache = CacheEmBanco()

    cache.guardar(geocodificacao)

    assert cache.buscar(ConsultaGeocodificacao(texto="rua augusta 100")) == geocodificacao
    assert cache.buscar(ConsultaGeocodificacao(texto="rua augusta, 101")) is None


@banco
@pytest.mark.django_db
def test_cache_em_banco_guarda_uma_por_chave() -> None:
    primeira = _geocodificacao(texto="Rua Augusta, 100")
    segunda = _geocodificacao(
        texto="rua augusta 100",
        endereco=_endereco_externo(endereco_formatado="segunda", precisao=Precisao.INTERPOLADA),
        consultado_em=datetime(2026, 10, 9, 13, 15, tzinfo=UTC),
    )
    cache = CacheEmBanco()

    cache.guardar(primeira)
    cache.guardar(segunda)

    assert GeocodificacaoGuardada.objects.count() == 1
    assert cache.buscar(primeira.consulta) == segunda
