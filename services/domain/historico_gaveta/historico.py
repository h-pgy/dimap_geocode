from pydantic import BaseModel

from .models import LIMITE_HISTORICO, HistoricoGaveta, ItemHistorico


class AberturaInput(BaseModel):
    historico: HistoricoGaveta
    item: ItemHistorico


class AbrirNoHistorico:
    def __call__(self, entrada: AberturaInput) -> HistoricoGaveta:
        return self.pipeline(entrada)

    def pipeline(self, entrada: AberturaInput) -> HistoricoGaveta:
        demais = entrada.historico.fora(entrada.item.etiqueta.chave)
        itens = (entrada.item, *demais)[:LIMITE_HISTORICO]
        return HistoricoGaveta(itens=itens)


class RetiradaInput(BaseModel):
    historico: HistoricoGaveta
    chave: str


class TirarDoHistorico:
    def __call__(self, entrada: RetiradaInput) -> HistoricoGaveta:
        return HistoricoGaveta(itens=entrada.historico.fora(entrada.chave))
