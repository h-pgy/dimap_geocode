from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# `<app>.<nome>`: mesmo formato do app_label.codename do Django — origem do caminho dos ícones.
PADRAO_SLUG = r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"


class VarianteIcone(StrEnum):
    PEQUENO = "pequeno"
    GRANDE = "grande"


class Acao(BaseModel):
    """O que a ação é. Sem rota, sem template, sem Django."""

    model_config = ConfigDict(frozen=True)

    slug: str = Field(pattern=PADRAO_SLUG)
    nome: str = Field(min_length=1)
    tooltip: str = Field(min_length=1)
    nome_curto: str | None = None
    variantes_icone: frozenset[VarianteIcone] = frozenset()
