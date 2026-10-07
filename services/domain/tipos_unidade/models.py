"""
Os DTOs do catálogo de tipos de unidade como ato administrativo (SPEC user_admin/031): o domínio
não conhece `TipoUnidade` — do tipo só precisa da identidade, e de cada ato só do que a regra dele
avalia.
"""

from pydantic import BaseModel, ConfigDict


class IdentidadeTipoUnidade(BaseModel):
    model_config = ConfigDict(frozen=True)

    tipo_id: int
    nome: str


class PreviaDaEdicaoTipoUnidade(BaseModel):
    model_config = ConfigDict(frozen=True)

    tipo: IdentidadeTipoUnidade
    # Unidades no organograma vinculadas a este tipo — impedem mudança estrutural.
    unidades_ativas: int


class TravasDaEdicaoTipoUnidade(BaseModel):
    """O que a edição não pode tocar, e a mensagem explicativa."""

    model_config = ConfigDict(frozen=True)

    estrutura_travada: bool
    motivo: str = ""


class PreviaDaExtincaoTipoUnidade(BaseModel):
    model_config = ConfigDict(frozen=True)

    tipo: IdentidadeTipoUnidade
    # Extinguir tipo em uso é o cenário normal: a contagem é o que o modal informa, não uma
    # condição de passagem.
    unidades_ativas: int
    ja_extinto: bool = False


class PreviaDaReativacaoTipoUnidade(BaseModel):
    model_config = ConfigDict(frozen=True)

    tipo: IdentidadeTipoUnidade
    ja_vigente: bool = False


class Veredito(BaseModel):
    # Do próprio submódulo: `tipos_unidade` não importa o veredito de `cargos`, `extincao_unidade`
    # nem `exoneracao` — um submódulo não cruza domínios.
    model_config = ConfigDict(frozen=True)

    pode: bool
    motivo: str = ""
