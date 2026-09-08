from services.domain.documento_oficial import (
    ConteudoDocumento,
    Paragrafo,
    QuadroSeloConfig,
    SeloDeFecho,
    SeloDeFechoInput,
    Tabela,
    Titulo,
    acrescentar_selo_de_fecho,
)
from services.domain.documento_selado import SeloImpresso
from services.utils.pdf import ColunaFluida

QUADRO = QuadroSeloConfig(largura_mm=90.0, largura_qr_mm=35.0, respiro_interno_mm=6.0)


def _selo_impresso(**overrides: object) -> SeloImpresso:
    defaults: dict[str, object] = {
        "chamada": "Assinado eletronicamente",
        "url_conferencia": "https://geocode.dimap.sp.gov.br/d/ABCDEFGHJKMN",
        "link_impresso": "geocode.dimap.sp.gov.br/d/ABCDEFGHJKMN",
        "assinante": "Fulano de Tal",
        "cargo": "Chefe da Divisão do Mapa de Valores",
        "data_por_extenso": "8 de setembro de 2026, às 14h32min",
    }
    return SeloImpresso(**(defaults | overrides))


def _conteudo(*blocos: object) -> ConteudoDocumento:
    return ConteudoDocumento(titulo="Teste", nome_arquivo="teste.pdf", blocos=blocos)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# O quadro de fecho é sempre o ÚLTIMO bloco, os demais preservam a ordem
# ---------------------------------------------------------------------------


def test_selo_de_fecho_eh_o_ultimo_bloco_do_conteudo() -> None:
    original = _conteudo(
        Titulo(texto="Certidão de Lançamento"),
        Paragrafo(texto="Corpo do ato"),
        Tabela(colunas=(ColunaFluida(),), linhas=(("Linha final",),)),
    )

    resultado = acrescentar_selo_de_fecho(
        SeloDeFechoInput(conteudo=original, selo=_selo_impresso(), quadro=QUADRO)
    )

    assert resultado.blocos[:-1] == original.blocos
    assert len(resultado.blocos) == len(original.blocos) + 1
    ultimo = resultado.blocos[-1]
    assert isinstance(ultimo, SeloDeFecho)
    assert ultimo.selo == _selo_impresso()
    assert ultimo.quadro == QUADRO
