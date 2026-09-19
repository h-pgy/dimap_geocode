from apps.mapping.acoes_desenho import ConsultaSobreDesenho
from services.domain.desenho import TipoDesenho

CONSULTA_LOTES_INTERSECTADOS = ConsultaSobreDesenho(
    slug="lotes_mais_proximos.lotes_intersectados",
    nome="Lotes intersectados",
    tooltip="Lotes cadastrados que o polígono marcado cruza.",
    url_name="lotes_mais_proximos:lotes_do_desenho",
    tipos=frozenset({TipoDesenho.POLIGONO}),
)
