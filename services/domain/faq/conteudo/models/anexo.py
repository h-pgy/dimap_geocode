from pydantic import BaseModel, Field

from services.utils.extracao_texto import TextoExtraido, TipoDocumento


class Anexo(BaseModel):
    id: int | None = None
    titulo: str = Field(min_length=2, max_length=160)
    nome_arquivo: str
    tipo: TipoDocumento
    hash_conteudo: str = Field(pattern=r"^[0-9a-f]{64}$")
    tamanho_bytes: int = Field(gt=0)
    texto: TextoExtraido
    enviado_por_id: int
