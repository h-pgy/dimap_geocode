from typing import Any

from .constants import ALGORITMO, CHAVE_TAG, PLACEHOLDER
from .envelope import embutir_envelope, ler_envelope
from .models import DocumentoSelado, SelarInput
from .tag import calcular_tag, localizar_unica, trocar


class SelarDocumento:
    """Callable: um PDF entra, o mesmo PDF selado sai. A tag cobre o arquivo INTEIRO — texto,
    fontes, imagens e o próprio envelope —, e não o texto extraído: mapa e brasão também precisam
    estar cobertos."""

    def __call__(self, pedido: SelarInput) -> DocumentoSelado:
        return self.pipeline(pedido)

    def pipeline(self, pedido: SelarInput) -> DocumentoSelado:
        self._recusar_se_ja_selado(pedido.pdf)
        envelope = self._envelope(pedido)
        base = embutir_envelope(pedido.pdf, envelope)
        posicao = localizar_unica(base, PLACEHOLDER)
        tag = calcular_tag(base, pedido.segredo)
        # A tag no lugar do placeholder, sem mudar um byte de tamanho — é o que faz a conferência
        # poder desfazer o passo e chegar de volta em `base`.
        return DocumentoSelado(
            pdf=trocar(base, posicao, tag),
            envelope={**envelope, CHAVE_TAG: tag},
            tag=tag,
        )

    def _envelope(self, pedido: SelarInput) -> dict[str, Any]:
        return {
            **pedido.dados,
            "alg": ALGORITMO,
            "id_chave": pedido.id_chave,
            "campos_publicos": list(pedido.campos_publicos),
            CHAVE_TAG: PLACEHOLDER,
        }

    def _recusar_se_ja_selado(self, pdf: bytes) -> None:
        # Selar duas vezes deixaria duas tags no arquivo e nenhuma conferível: a segunda cobriria
        # bytes que a primeira já alterou.
        if ler_envelope(pdf) is not None:
            raise ValueError("Este PDF já traz selo: sele o documento recém-gerado, não o selado.")


selar_documento = SelarDocumento()
