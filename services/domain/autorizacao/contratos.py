from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# `<app>.<nome>`: mesmo formato do app_label.codename do Django — origem do caminho dos ícones.
PADRAO_SLUG = r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"

# Espelham as colunas da projeção no banco (SPEC autorizacao/002) — a recusa pertence ao contrato,
# primeira fronteira, não ao sincronizar_acoes.
LIMITE_SLUG = 120
LIMITE_NOME = 120
LIMITE_NOME_CURTO = 60
LIMITE_TOOLTIP = 255


class VarianteIcone(StrEnum):
    PEQUENO = "pequeno"
    GRANDE = "grande"


class Acao(BaseModel):
    """O que a ação é. Sem rota, sem template, sem Django."""

    model_config = ConfigDict(frozen=True)

    slug: str = Field(pattern=PADRAO_SLUG, max_length=LIMITE_SLUG)
    nome: str = Field(min_length=1, max_length=LIMITE_NOME)
    tooltip: str = Field(min_length=1, max_length=LIMITE_TOOLTIP)
    nome_curto: str | None = Field(default=None, max_length=LIMITE_NOME_CURTO)
    variantes_icone: frozenset[VarianteIcone] = frozenset()
    # Competência que decorre de dirigir a unidade (titularidade/001); não passa por atribuição
    # nem concessão. Permite à projeção (SPEC 002) excluir a ação da oferta em tela.
    estrutural: bool = False
