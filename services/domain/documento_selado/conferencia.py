from services.utils.assinatura import EstadoSelo

from .ficha import codigo_alegado, ler_ficha_do_ato
from .models import (
    ConferenciaInput,
    ConferenciaOutput,
    EstadoDocumento,
    FichaDoAto,
    RegistroDocumento,
)


class ClassificarConferencia:
    """Callable: o veredito do selo + a existência no acervo → o que a tela mostra."""

    def __call__(self, pedido: ConferenciaInput) -> ConferenciaOutput:
        return self.pipeline(pedido)

    def pipeline(self, pedido: ConferenciaInput) -> ConferenciaOutput:
        estado = self._estado(pedido)
        return ConferenciaOutput(
            estado=estado,
            codigo=codigo_alegado(pedido.resultado_selo),
            ficha=self._ficha(estado, pedido.registro),
            # Só há original a oferecer se o documento existe no acervo.
            tem_original=pedido.registro is not None,
        )

    def _estado(self, pedido: ConferenciaInput) -> EstadoDocumento:
        selo = pedido.resultado_selo.estado
        if selo is EstadoSelo.SEM_SELO:
            return EstadoDocumento.SEM_SELO
        if selo is EstadoSelo.VIOLADO:
            # Violado com código conhecido continua NAO_CONFERE: quem decide o que fazer com o
            # original é a tela, pelo `tem_original`.
            return EstadoDocumento.NAO_CONFERE
        # Íntegro é o caso que se bifurca: selo que fecha com um código que o acervo nunca emitiu
        # não é documento bom — é sinal de que o segredo saiu daqui.
        if pedido.registro is None:
            return EstadoDocumento.DESCONHECIDO
        return EstadoDocumento.CONFERE

    def _ficha(
        self,
        estado: EstadoDocumento,
        registro: RegistroDocumento | None,
    ) -> FichaDoAto | None:
        # A ficha é uma AFIRMAÇÃO sobre o ato, e só o selo que fecha contra o acervo autoriza fazê-la.
        # Nos outros três estados o que existe é a alegação do arquivo, que a tela não repete como
        # se fosse fato. E ela sai do envelope guardado, nunca do que veio dentro do arquivo.
        if estado is not EstadoDocumento.CONFERE or registro is None:
            return None
        return ler_ficha_do_ato(registro.envelope)


classificar_conferencia = ClassificarConferencia()
