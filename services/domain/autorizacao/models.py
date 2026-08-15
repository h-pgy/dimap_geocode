"""
Os DTOs do avaliador de competência (SPEC autorizacao/003): o perfil chega resolvido — o domínio
não lê banco, não conhece `Perfil` e não sabe quem é titular.
"""

from pydantic import BaseModel, ConfigDict


class Caneta(BaseModel):
    """Uma posição de onde se exerce competência. A própria, e — enquanto a substituição vigora —
    a de quem se cobre."""

    model_config = ConfigDict(frozen=True)

    unidade_id: int
    cargo_base_id: int | None = None
    cargo_comissao_id: int | None = None
    # Resolvido na aplicação pelo AvaliadorDirecao (SPEC user_admin/014): quem cobre o titular
    # dirige a unidade dele, sem receber o vínculo.
    dirige_a_unidade: bool = False


class PerfilCompetencia(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Fora da cadeira não se exerce competência nenhuma, nem a estrutural.
    em_exercicio: bool
    # A própria e, enquanto a substituição vigora, a de quem ele cobre — que pode ser de outra
    # unidade. Uma regra só para as duas: "bate com uma caneta que ele tem".
    canetas: tuple[Caneta, ...]


class ConcessaoVigente(BaseModel):
    model_config = ConfigDict(frozen=True)

    acao_slug: str
    acao_ativa: bool
    unidade_id: int
    cargo_base_id: int | None = None
    cargo_comissao_id: int | None = None


class AvaliacaoCompetenciaInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    perfil: PerfilCompetencia
    concessoes: tuple[ConcessaoVigente, ...]
    # Vêm do registro em código: o domínio não conhece o catálogo do app.
    slugs_estruturais: frozenset[str] = frozenset()


class AvaliacaoCompetenciaOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    slugs_liberados: frozenset[str]
