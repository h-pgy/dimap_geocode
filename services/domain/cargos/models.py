"""
Os DTOs do cargo em comissão como ato administrativo (SPEC user_admin/029): o domínio não conhece
`CargoComissao` — do cargo só precisa da identidade, e de cada ato só precisa do que a regra dele
avalia.
"""

from pydantic import BaseModel, ConfigDict


class IdentidadeCargo(BaseModel):
    """O cargo projetado: o domínio não conhece o model, e do model só precisa disto."""

    model_config = ConfigDict(frozen=True)

    cargo_id: int
    nome: str
    padrao: str


class PreviaDaEdicao(BaseModel):
    model_config = ConfigDict(frozen=True)

    cargo: IdentidadeCargo
    # Servidores no quadro que ocupam o cargo — exonerado não ocupa mais e não trava nada.
    ocupantes: int


class TravasDaEdicao(BaseModel):
    """O que a edição não pode tocar, e o texto que explica por quê."""

    model_config = ConfigDict(frozen=True)

    natureza_travada: bool
    motivo: str = ""


class PreviaDaExtincaoCargo(BaseModel):
    model_config = ConfigDict(frozen=True)

    cargo: IdentidadeCargo
    # Extinguir cargo ocupado é o cenário normal: a contagem é o que o modal informa, não uma
    # condição de passagem.
    ocupantes: int
    ja_extinto: bool = False


class PreviaDaReativacaoCargo(BaseModel):
    model_config = ConfigDict(frozen=True)

    cargo: IdentidadeCargo
    ja_vigente: bool = False


class Veredito(BaseModel):
    model_config = ConfigDict(frozen=True)

    pode: bool
    motivo: str = ""
