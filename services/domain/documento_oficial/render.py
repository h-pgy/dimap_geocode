from collections.abc import Callable, Mapping
from typing import Any

from reportlab.platypus import Flowable

from services.utils.pdf import DocumentoPdfInput, gerar_pdf

from .escritores import montar_escritores
from .models import BlocoDocumento, DocumentoRenderizado, RenderizarDocumentoInput, Tema


class RenderizarDocumentoOficial:
    """Callable: o que o documento diz, sobre o papel que ele usa, vira PDF. O tema vem no
    construtor: é ele que decide como cada bloco se escreve, e não muda entre documentos."""

    def __init__(
        self,
        tema: Tema,
        # Injetável para o teste forçar um registro incompleto; o default é o registro do tema.
        escritores: Mapping[str, Callable[[Any], Flowable]] | None = None,
    ) -> None:
        self._escritores = dict(escritores) if escritores is not None else montar_escritores(tema)

    def __call__(self, pedido: RenderizarDocumentoInput) -> DocumentoRenderizado:
        return self.pipeline(pedido)

    def pipeline(self, pedido: RenderizarDocumentoInput) -> DocumentoRenderizado:
        return DocumentoRenderizado(
            pdf=self._pdf(pedido),
            nome_arquivo=pedido.conteudo.nome_arquivo,
        )

    def _pdf(self, pedido: RenderizarDocumentoInput) -> bytes:
        return gerar_pdf(
            DocumentoPdfInput(
                titulo=pedido.conteudo.titulo,
                corpo=tuple(self._escrever(bloco) for bloco in pedido.conteudo.blocos),
                marcacao=pedido.marcacao,
            )
        )

    def _escrever(self, bloco: BlocoDocumento) -> Flowable:
        # Bloco sem escritor levanta KeyError na montagem — onde há teste e stack trace —, e não
        # como buraco silencioso num documento que alguém vai assinar.
        return self._escritores[bloco.tipo](bloco)  # type: ignore[attr-defined]
