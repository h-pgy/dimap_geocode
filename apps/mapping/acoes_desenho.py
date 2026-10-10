from apps.mapping.models import (
    AcaoSobreDesenho,
    ConsultaSobreDesenho,
    ItemPoco,
    OfertaPocoInput,
    RegistroDesenho,
)


class OfertarNoPoco:
    def __init__(self, registro: RegistroDesenho) -> None:
        self.registro = registro

    def __call__(self, entrada: OfertaPocoInput) -> tuple[ItemPoco, ...]:
        return self.pipeline(entrada)

    def pipeline(self, entrada: OfertaPocoInput) -> tuple[ItemPoco, ...]:
        return tuple(
            self._item(item)
            for item in self.registro.itens
            if entrada.tipo in item.tipos and self._liberado(item, entrada.slugs_liberados)
        )

    def _liberado(
        self,
        item: AcaoSobreDesenho | ConsultaSobreDesenho,
        slugs: frozenset[str],
    ) -> bool:
        # A consulta não é ato: não há caneta que a libere. Quem recusa o ato é a rota, a cada execução.
        if isinstance(item, ConsultaSobreDesenho):
            return True
        return item.acao.acao.slug in slugs

    def _item(self, item: AcaoSobreDesenho | ConsultaSobreDesenho) -> ItemPoco:
        if isinstance(item, ConsultaSobreDesenho):
            return ItemPoco(
                slug=item.slug,
                nome=item.nome,
                tooltip=item.tooltip,
                url_name=item.url_name,
            )
        acao = item.acao.acao
        return ItemPoco(
            slug=acao.slug,
            nome=acao.nome,
            tooltip=acao.tooltip,
            url_name=item.acao.url_name,
        )
