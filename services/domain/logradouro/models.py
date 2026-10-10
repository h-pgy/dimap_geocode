from pydantic import BaseModel, computed_field


class Logradouro(BaseModel):
    """O logradouro como entidade: a identidade que todos os seus segmentos repetem."""

    codlog: str
    tipo_logradouro: str
    titulo: str | None = None
    preposicao: str | None = None
    nome_logradouro: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def denominacao(self) -> str:
        partes = [self.titulo, self.preposicao, self.nome_logradouro]
        return " ".join(p for p in partes if p)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def nome_completo(self) -> str:
        # O catálogo de nomes tem logradouro sem tipo: sem ele, sai só a denominação.
        partes = [self.tipo_logradouro, self.denominacao]
        return " ".join(p for p in partes if p)
