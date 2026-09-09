import hmac
from typing import Any

from .constants import CHAVE_TAG, PLACEHOLDER, TAMANHO_TAG
from .envelope import ler_envelope
from .models import ConferirInput, EstadoSelo, ResultadoConferencia
from .publicos import extrair_publicos
from .tag import calcular_tag, localizar, trocar

DIGITOS_HEX = frozenset("0123456789abcdef")


class ConferirSelo:
    """Callable: bytes → o que o arquivo sozinho consegue afirmar. Não consulta banco, rede nem
    relógio: é isso que faz o selo valer com o acervo fora do ar. E não levanta com arquivo nenhum:
    o que chega aqui veio de fora, e arquivo ruim é um ESTADO do selo, não um erro do sistema."""

    def __call__(self, pedido: ConferirInput) -> ResultadoConferencia:
        return self.pipeline(pedido)

    def pipeline(self, pedido: ConferirInput) -> ResultadoConferencia:
        envelope = ler_envelope(pedido.pdf)
        if envelope is None or CHAVE_TAG not in envelope:
            return ResultadoConferencia(estado=EstadoSelo.SEM_SELO)
        return ResultadoConferencia(
            estado=self._estado(pedido, envelope),
            envelope=envelope,
            publicos=self._publicos(envelope),
        )

    def _estado(self, pedido: ConferirInput, envelope: dict[str, Any]) -> EstadoSelo:
        tag = envelope[CHAVE_TAG]
        # Envelope escrito à mão põe o que quiser em `tag`; a troca de bytes abaixo só faz sentido
        # sobre 64 dígitos hexadecimais, e o que não tem essa forma nunca saiu da selagem.
        if not self._eh_tag(tag):
            return EstadoSelo.VIOLADO
        posicao = localizar(pedido.pdf, tag)
        # Zero ou mais de uma ocorrência: o arquivo não é o que a selagem produziu.
        if posicao is None:
            return EstadoSelo.VIOLADO
        base = trocar(pedido.pdf, posicao, PLACEHOLDER)
        # `compare_digest`, e não `==`: comparação que sai no primeiro byte diferente mede o quanto
        # a tag tentada acertou.
        if not hmac.compare_digest(calcular_tag(base, pedido.segredo), tag):
            return EstadoSelo.VIOLADO
        return EstadoSelo.INTEGRO

    def _eh_tag(self, valor: Any) -> bool:
        if not isinstance(valor, str) or len(valor) != TAMANHO_TAG:
            return False
        return DIGITOS_HEX.issuperset(valor)

    def _publicos(self, envelope: dict[str, Any]) -> dict[str, Any]:
        return extrair_publicos(envelope)


conferir_selo = ConferirSelo()
