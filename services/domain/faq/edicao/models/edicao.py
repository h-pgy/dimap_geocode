from typing import Self

from pydantic import BaseModel, model_validator

from services.domain.faq.conteudo import Faq, Situacao


class Editor(BaseModel):
    """O superusuário que está editando. A marca de superusuário é conferida na view."""

    perfil_id: int


class Edicao(BaseModel):
    """Pedido de regravação de uma FAQ existente, pelo editor."""

    faq: Faq
    editor: Editor

    @model_validator(mode="after")
    def _sem_excluir_pela_edicao(self) -> Self:
        if self.faq.id is None:
            raise ValueError("Só se regrava uma FAQ já gravada.")
        if self.faq.situacao is Situacao.EXCLUIDA:
            raise ValueError("A exclusão é feita pelo botão de excluir.")
        return self
