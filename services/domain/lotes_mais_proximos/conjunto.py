from pydantic import BaseModel, Field

from .models import ConjuntoDeLotes


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
