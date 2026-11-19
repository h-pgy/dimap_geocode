from pydantic import BaseModel, computed_field

from services.domain.faq.conteudo import Faq
from services.domain.faq.taxonomia import Tema

from .leitor import Leitor


class MontagemIndiceInput(BaseModel):
    faqs: list[Faq]
    leitor: Leitor


class ItemIndice(BaseModel):
    faq: Faq
    relacionadas: list[Faq]


class SecaoSubtema(BaseModel):
    subtema: Tema
    itens: list[ItemIndice]


class SecaoTema(BaseModel):
    tema: Tema
    itens: list[ItemIndice]
    subtemas: list[SecaoSubtema]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> int:
        return len(self.itens) + sum(len(s.itens) for s in self.subtemas)


class IndiceFaq(BaseModel):
    secoes: list[SecaoTema]
