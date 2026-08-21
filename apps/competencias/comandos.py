"""O DTO do ato de competência (SPEC autorizacao/007): atribuir e remover incidem sobre o mesmo
par unidade × ação, e por isso compartilham um comando só."""

from pydantic import BaseModel, ConfigDict, Field

from services.domain.autorizacao import PADRAO_SLUG


class ComandoAtribuicao(BaseModel):
    """Construído na view, que deixa o `PydanticValidationMiddleware` interceptar o
    `ValidationError` — id não-numérico e slug fora do padrão morrem aqui, antes de virar consulta."""

    model_config = ConfigDict(frozen=True)

    unidade_alvo_id: int
    acao_slug: str = Field(pattern=PADRAO_SLUG)
