from pydantic import BaseModel, Field


class CodlogMatchInput(BaseModel):
    input_codlog: str = Field(pattern=r"^\d{1,5}$")
    digito_verificador: str | None = Field(default=None, pattern=r"^\d$")
    limite: int = Field(default=5, gt=0)

    def _validar_dv(self) -> bool:
        """Ponto de extensão: validar se digito_verificador é consistente
        com input_codlog segundo a fórmula do DV. A implementar."""
        raise NotImplementedError


class CodlogMatchOutput(BaseModel):
    codlog: str
    dv: str
    tipo_logradouro: str
    nome_logradouro: str

    @property
    def nome_completo(self) -> str:
        return f"{self.tipo_logradouro} {self.nome_logradouro}"
