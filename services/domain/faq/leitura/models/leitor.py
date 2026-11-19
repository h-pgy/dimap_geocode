from pydantic import BaseModel, Field, computed_field


class Leitor(BaseModel):
    """Quem lê a FAQ: servidor logado, identificado pelo RF, ou visitante sem login."""

    rf: str | None = Field(default=None, min_length=1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def eh_interno(self) -> bool:
        return self.rf is not None
