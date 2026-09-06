from pydantic import BaseModel, ConfigDict, computed_field


class ErroHtml(BaseModel):
    """Uma tag problemática, localizada no texto. Erro sem tag não existe: tudo aqui é sobre marcação."""

    model_config = ConfigDict(frozen=True)

    tag: str
    linha: int
    coluna: int
    mensagem: str


class ResultadoValidacaoHtml(BaseModel):
    """O veredito e o que o sustenta. Válido é exatamente 'sem erro'."""

    model_config = ConfigDict(frozen=True)

    erros: tuple[ErroHtml, ...] = ()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def valido(self) -> bool:
        return not self.erros
