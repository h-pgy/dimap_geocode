"""Contratos do domínio (SPEC user_admin/018): onde uma unidade está no organograma."""

from pydantic import BaseModel, ConfigDict, computed_field


class ParHierarquia(BaseModel):
    """Uma aresta do organograma, achatada. O domínio recebe a hierarquia inteira assim porque não
    lê banco."""

    model_config = ConfigDict(frozen=True)

    unidade_id: int
    # Exatamente um pai, e só o topo do organograma não tem nenhum.
    pai_id: int | None


class NoHierarquia(BaseModel):
    """Uma unidade e o que pende dela, em qualquer profundidade. Sem filhas em qualquer nível: alto
    na hierarquia não implica ter subordinada."""

    model_config = ConfigDict(frozen=True)

    unidade_id: int
    filhas: tuple["NoHierarquia", ...] = ()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ids(self) -> frozenset[int]:
        """Derivado: a conferência de alvo pergunta pertinência, e guardar o conjunto ao lado da
        árvore seria o mesmo dado em dois campos livres para divergir."""
        return frozenset({self.unidade_id}).union(*(filha.ids for filha in self.filhas))


class PosicaoHierarquica(BaseModel):
    """Onde uma unidade está no organograma, vista dela mesma."""

    model_config = ConfigDict(frozen=True)

    # Do topo até o pai, nessa ordem; vazia quando o ego é o topo.
    acima: tuple[int, ...]
    ego: NoHierarquia


class ComandoPosicao(BaseModel):
    model_config = ConfigDict(frozen=True)

    unidade_id: int
    pares: tuple[ParHierarquia, ...]
