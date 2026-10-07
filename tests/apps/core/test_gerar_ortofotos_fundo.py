from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command

from services.scripts.ortofotos_fundo import OrtofotoResultado


def _resultado_com_pendentes(*pendentes: str) -> OrtofotoResultado:
    return OrtofotoResultado(
        geradas=[],
        puladas=[],
        pendentes=list(pendentes),
        indisponibilidade="WMS inacessível",
    )


# ---------------------------------------------------------------------------
# GeoSampa fora do ar
# ---------------------------------------------------------------------------


def test_comando_com_geosampa_fora_do_ar_sai_zero_com_aviso() -> None:
    gerador = Mock(return_value=_resultado_com_pendentes("anhangabau", "butanta"))
    saida = StringIO()

    with patch(
        "apps.core.management.commands.gerar_ortofotos_fundo.GeradorOrtofotosFundo",
        return_value=gerador,
    ):
        call_command("gerar_ortofotos_fundo", stdout=saida)

    aviso = saida.getvalue()
    assert "AVISO" in aviso
    assert "WMS inacessível" in aviso
    assert "anhangabau" in aviso
    assert "butanta" in aviso
