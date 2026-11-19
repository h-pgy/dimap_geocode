from pydantic import BaseModel

from .models import Pergunta


class PerguntaOcupada(BaseModel):
    pergunta: Pergunta
    faq_id: int


class PerguntaJaRespondida(Exception):
    """Uma ou mais perguntas já pertencem a outra FAQ."""

    def __init__(self, ocupadas: list[PerguntaOcupada]) -> None:
        super().__init__(f"{len(ocupadas)} pergunta(s) já pertence(m) a outra FAQ.")
        self.ocupadas = ocupadas
