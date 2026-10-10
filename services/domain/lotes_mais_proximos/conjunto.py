from collections.abc import Callable

from pydantic import BaseModel, Field

from .do_desenho import LotesDoDesenhoInput
from .models import CamadaLotes, ConjuntoDeLotes, LotesDoDesenho


class RemocaoDoConjuntoInput(BaseModel):
    conjunto: ConjuntoDeLotes
    id_poligono: str = Field(pattern=r"^\d+$")


class RemoverDoConjunto:
    def __call__(self, entrada: RemocaoDoConjuntoInput) -> ConjuntoDeLotes:
        return self.pipeline(entrada)

    def pipeline(self, entrada: RemocaoDoConjuntoInput) -> ConjuntoDeLotes:
        # Só se tira o que a consulta apurou: um id de fora devolve o conjunto como estava.
        apurados = {lote.attributes.id_poligono for lote in entrada.conjunto.apurado.lotes}
        if entrada.id_poligono not in apurados:
            return entrada.conjunto
        return entrada.conjunto.model_copy(
            update={"removidos": entrada.conjunto.removidos | {entrada.id_poligono}},
        )


class EsvaziarConjunto:
    def __call__(self, conjunto: ConjuntoDeLotes) -> ConjuntoDeLotes:
        # Limpar é remover tudo o que foi apurado: o conjunto continua vivo, vazio, e a tabela
        # cai no estado de falta do conjunto esvaziado — não no do desenho sem lote.
        apurados = frozenset(lote.attributes.id_poligono for lote in conjunto.apurado.lotes)
        return conjunto.model_copy(update={"removidos": apurados})


class ReleituraDoConjuntoInput(BaseModel):
    conjunto: ConjuntoDeLotes
    crs_mapa: int
    camada: CamadaLotes
    area_maxima_m2: float = Field(gt=0)


class RelerConjunto:
    def __init__(self, buscar: Callable[[LotesDoDesenhoInput], LotesDoDesenho]) -> None:
        self._buscar = buscar

    def __call__(self, entrada: ReleituraDoConjuntoInput) -> ConjuntoDeLotes:
        return self.pipeline(entrada)

    def pipeline(self, entrada: ReleituraDoConjuntoInput) -> ConjuntoDeLotes:
        apurado = self._buscar(
            LotesDoDesenhoInput(
                desenho=entrada.conjunto.apurado.desenho,
                crs_mapa=entrada.crs_mapa,
                camada=entrada.camada,
                area_maxima_m2=entrada.area_maxima_m2,
            )
        )
        escolhidos = {lote.attributes.id_poligono for lote in entrada.conjunto.lotes}
        cruzados = frozenset(lote.attributes.id_poligono for lote in apurado.lotes)
        # O que o desenho cruza hoje e não foi escolhido entra como removido: a camada não acrescenta
        # lote. O escolhido que saiu dela não volta, e quem o acusa é a conferência da emissão.
        return ConjuntoDeLotes(apurado=apurado, removidos=cruzados - escolhidos)
