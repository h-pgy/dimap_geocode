import pytest
from reportlab.lib.colors import HexColor

from services.domain.documento_oficial import (
    PaletaDocumento,
    TemaConfig,
    TipografiaDocumento,
    montar_tema,
)


# ---------------------------------------------------------------------------
# Sem ambiente: preto sobre branco, nos corpos padrão
# ---------------------------------------------------------------------------


def test_tema_vem_do_ambiente_e_cai_no_padrao() -> None:
    padrao = montar_tema(TemaConfig())

    assert padrao.estilos["titulo"].textColor == HexColor("#000000")
    assert padrao.estilos["titulo"].fontSize == 14.0
    assert padrao.estilos["titulo"].leading == pytest.approx(14.0 * 1.45)
    assert padrao.estilos["paragrafo"].fontSize == 11.0
    assert padrao.estilos["subtitulo_1"].fontSize == 12.0
    assert padrao.estilos["subtitulo_3"].fontSize == 10.0

    # ---------------------------------------------------------------------
    # Com ambiente: corpo e cor definidos aparecem, e a entrelinha acompanha o corpo
    # ---------------------------------------------------------------------
    customizado = montar_tema(
        TemaConfig(
            paleta=PaletaDocumento(tinta="#123456"),
            tipografia=TipografiaDocumento(corpo_titulo_pt=20.0, fator_entrelinha=2.0),
        )
    )

    assert customizado.estilos["titulo"].textColor == HexColor("#123456")
    assert customizado.estilos["titulo"].fontSize == 20.0
    assert customizado.estilos["titulo"].leading == pytest.approx(20.0 * 2.0)
    # O parágrafo não foi customizado: continua no corpo padrão, com a entrelinha do
    # fator NOVO — é o que prova que a entrelinha nunca é declarada solta por estilo.
    assert customizado.estilos["paragrafo"].fontSize == 11.0
    assert customizado.estilos["paragrafo"].leading == pytest.approx(11.0 * 2.0)
