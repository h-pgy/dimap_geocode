"""
Os DTOs da extinção e da reativação de unidade (SPEC user_admin/025): as duas faces do ato, o que
cada uma pergunta e o que a regra decide sobre ela.
"""

from pydantic import BaseModel, ConfigDict


class IdentidadeUnidade(BaseModel):
    """A unidade projetada: o domínio não conhece o model, e do model só precisa disto."""

    model_config = ConfigDict(frozen=True)

    unidade_id: int
    sigla: str


class PreviaDaExtincao(BaseModel):
    model_config = ConfigDict(frozen=True)

    unidade: IdentidadeUnidade
    # Ausente é raiz — e raiz não tem para onde mandar o que carrega.
    destino: IdentidadeUnidade | None
    servidores: int
    subordinadas: int
    ja_extinta: bool = False


class PreviaDaReativacao(BaseModel):
    """O reverso: o que volta, não o que sai."""

    model_config = ConfigDict(frozen=True)

    unidade: IdentidadeUnidade
    # A unidade superior de onde ela volta a pender. Extinta, não há para onde voltar.
    superior: IdentidadeUnidade
    superior_extinta: bool
    atribuicoes: int
    concessoes: int
    ja_vigente: bool = False


class Veredito(BaseModel):
    """Um só para as duas faces: a pergunta muda, a resposta tem a mesma forma."""

    model_config = ConfigDict(frozen=True)

    pode: bool
    motivo: str = ""
