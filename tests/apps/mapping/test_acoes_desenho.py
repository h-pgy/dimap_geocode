from apps.competencias.schemas import AcaoImplementada
from apps.mapping.acoes_desenho import (
    AcaoSobreDesenho,
    ConsultaSobreDesenho,
    OfertaPocoInput,
    OfertarNoPoco,
    RegistroDesenho,
)
from services.domain.autorizacao import Acao
from services.domain.desenho import TipoDesenho

SLUG_CONSULTA = "fake.consulta_poligono"
SLUG_ATO = "fake.ato_poligono"

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _consulta_sobre_desenho(slug: str = SLUG_CONSULTA) -> ConsultaSobreDesenho:
    return ConsultaSobreDesenho(
        slug=slug,
        nome="Consulta fake",
        tooltip="Consulta sobre polígono.",
        url_name="fake:consulta",
        tipos=frozenset({TipoDesenho.POLIGONO}),
    )


def _acao_sobre_desenho(slug: str = SLUG_ATO) -> AcaoSobreDesenho:
    return AcaoSobreDesenho(
        acao=AcaoImplementada(
            acao=Acao(slug=slug, nome="Ato fake", tooltip="Ato sobre polígono."),
            url_name="fake:ato",
        ),
        tipos=frozenset({TipoDesenho.POLIGONO}),
    )


def _ofertar(
    registro: RegistroDesenho,
    tipo: TipoDesenho,
    liberados: frozenset[str] = frozenset(),
) -> tuple[str, ...]:
    itens = OfertarNoPoco(registro)(OfertaPocoInput(tipo=tipo, slugs_liberados=liberados))
    return tuple(item.slug for item in itens)


# ---------------------------------------------------------------------------
# Router: tipo do poço e canetas do usuário
# ---------------------------------------------------------------------------


def test_poco_oferece_so_o_que_opera_sobre_o_tipo() -> None:
    registro = RegistroDesenho(itens=(_consulta_sobre_desenho(),))

    assert _ofertar(registro, TipoDesenho.POLIGONO) == (SLUG_CONSULTA,)
    assert _ofertar(registro, TipoDesenho.PONTO) == ()


def test_ato_sobre_desenho_so_para_quem_tem_a_caneta() -> None:
    registro = RegistroDesenho(itens=(_consulta_sobre_desenho(), _acao_sobre_desenho()))

    assert _ofertar(registro, TipoDesenho.POLIGONO) == (SLUG_CONSULTA,)
    assert _ofertar(registro, TipoDesenho.POLIGONO, frozenset({SLUG_ATO})) == (
        SLUG_CONSULTA,
        SLUG_ATO,
    )
