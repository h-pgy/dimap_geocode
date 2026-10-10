from apps.mapping.models import ConsultaSobreDesenho
from services.domain.desenho import TipoDesenho

CONSULTA_LOGRADOURO_MAIS_PROXIMO = ConsultaSobreDesenho(
    slug="logradouro_mais_proximo.do_ponto",
    nome="Logradouro mais próximo",
    tooltip="Logradouro oficial cujo eixo passa mais perto do ponto marcado.",
    url_name="logradouro_mais_proximo:do_ponto",
    tipos=frozenset({TipoDesenho.PONTO}),
)
