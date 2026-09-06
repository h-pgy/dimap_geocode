"""Os DTOs dos atos de competência: atribuir e remover (SPEC autorizacao/007) incidem sobre o
mesmo par unidade × ação, e compartilham um comando só; conceder e revogar (SPEC autorizacao/008)
miram, respectivamente, o par atribuição × cargo e a concessão em si."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from services.domain.autorizacao import PADRAO_SLUG

ERRO_CARGO_XOR = "A concessão mira exatamente um cargo: base ou em comissão, nunca os dois."


class ComandoAtribuicao(BaseModel):
    """Construído na view, que deixa o `PydanticValidationMiddleware` interceptar o
    `ValidationError` — id não-numérico e slug fora do padrão morrem aqui, antes de virar consulta."""

    model_config = ConfigDict(frozen=True)

    unidade_alvo_id: int
    acao_slug: str = Field(pattern=PADRAO_SLUG)


class ComandoConcessao(BaseModel):
    """A concessão mira UM cargo — base ou em comissão —, e é a linha da atribuição que ela
    pendura, não a dupla unidade × ação (SPEC autorizacao/002)."""

    model_config = ConfigDict(frozen=True)

    unidade_alvo_id: int
    atribuicao_id: int
    cargo_base_id: int | None = None
    cargo_comissao_id: int | None = None

    @model_validator(mode="after")
    def _exatamente_um_cargo(self) -> "ComandoConcessao":
        if (self.cargo_base_id is None) == (self.cargo_comissao_id is None):
            raise ValueError(ERRO_CARGO_XOR)
        return self


class ComandoRevogacao(BaseModel):
    """A revogação mira a concessão em si: já é a linha exata, sem precisar recompor de qual
    cargo ela é."""

    model_config = ConfigDict(frozen=True)

    unidade_alvo_id: int
    concessao_id: int
