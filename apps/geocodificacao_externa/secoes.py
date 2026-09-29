from django.template.loader import render_to_string

from apps.geocodificacao_externa.views import geocodificador_externo
from apps.search.secoes import SecaoResultado
from services.domain.roteamento_busca import GeocodificacaoExternaParse

TITULO_GEOCODIFICACAO_EXTERNA = "Geocodificação externa"


def secao_geocodificacao_externa(candidato: GeocodificacaoExternaParse) -> SecaoResultado | None:
    geocodificador = geocodificador_externo()
    if geocodificador is None:
        return None  # sem provedor configurado, não se oferece o que não se pode cumprir
    html = render_to_string(
        "geocodificacao_externa/partials/_sugestao_externa.html",
        {"texto": candidato.texto, "provedor": geocodificador.provedor.rotulo},
    )
    return SecaoResultado(titulo=TITULO_GEOCODIFICACAO_EXTERNA, html=html)
