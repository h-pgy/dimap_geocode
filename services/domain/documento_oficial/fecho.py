from .models import ConteudoDocumento, SeloDeFecho, SeloDeFechoInput


class AcrescentarSeloDeFecho:
    """Callable: o conteúdo + o selo → o mesmo conteúdo com o quadro no ÚLTIMO bloco. É o único
    ponto que decide onde o fecho entra, e por isso nenhum documento consegue assiná-lo no meio."""

    def __call__(self, pedido: SeloDeFechoInput) -> ConteudoDocumento:
        return self.pipeline(pedido)

    def pipeline(self, pedido: SeloDeFechoInput) -> ConteudoDocumento:
        bloco = SeloDeFecho(selo=pedido.selo, quadro=pedido.quadro)
        return pedido.conteudo.model_copy(update={"blocos": (*pedido.conteudo.blocos, bloco)})


acrescentar_selo_de_fecho = AcrescentarSeloDeFecho()
