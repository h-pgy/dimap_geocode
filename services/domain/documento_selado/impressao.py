from .constants import CHAMADA_SELO, ROTA_CONFERENCIA
from .datas import por_extenso
from .models import SeloImpresso, SeloImpressoInput


class MontarSeloImpresso:
    """Callable: o envelope → o texto dos dois quadros. É o único lugar que redige o selo."""

    def __call__(self, pedido: SeloImpressoInput) -> SeloImpresso:
        return self.pipeline(pedido)

    def pipeline(self, pedido: SeloImpressoInput) -> SeloImpresso:
        url = self._url(pedido)
        autor = pedido.envelope.autor
        return SeloImpresso(
            chamada=CHAMADA_SELO,
            url_conferencia=url,
            link_impresso=self._sem_esquema(url),
            assinante=autor.nome,
            # O de comissão manda: é ele que descreve a competência que praticou o ato.
            cargo=autor.cargo_comissao or autor.cargo_base,
            substituindo=autor.substituindo,
            data_por_extenso=por_extenso(pedido.envelope.emitido_em),
        )

    def _url(self, pedido: SeloImpressoInput) -> str:
        return f"{pedido.base_url.rstrip('/')}/{ROTA_CONFERENCIA}/{pedido.envelope.codigo}"

    def _sem_esquema(self, url: str) -> str:
        # O que se lê e se digita no papel: "https://" ocupa oito caracteres e não ajuda ninguém.
        return url.split("://", 1)[-1]


montar_selo_impresso = MontarSeloImpresso()
