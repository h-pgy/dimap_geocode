from apps.mapping.acoes_desenho import ConsultaSobreDesenho
from services.domain.desenho import TipoDesenho

CONSULTA_ENDERECO_MAIS_PROXIMO = ConsultaSobreDesenho(
    slug="endereco_mais_proximo.do_ponto",
    nome="Endereço mais próximo",
    tooltip="Endereço oficial do logradouro mais perto do ponto marcado.",
    url_name="endereco_mais_proximo:do_ponto",
    tipos=frozenset({TipoDesenho.PONTO}),
)
