from pydantic import BaseModel, Field

from services.domain.logradouro import Logradouro


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
    titulo: str | None = None
    preposicao: str | None = None
    nome_logradouro: str

    @property
    def logradouro(self) -> Logradouro:
        return Logradouro(
            codlog=f"{self.codlog}{self.dv}",
            tipo_logradouro=self.tipo_logradouro,
            titulo=self.titulo,
            preposicao=self.preposicao,
            nome_logradouro=self.nome_logradouro,
        )
