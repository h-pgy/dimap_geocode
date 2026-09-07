from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from services.utils.pdf import Coluna


class BlocoDocumento(BaseModel):
    """Base dos blocos: o que todos compartilham é a posição no corpo, não atributo."""

    model_config = ConfigDict(frozen=True)


class BlocoTextual(BlocoDocumento):
    """A exceção: título, subtítulo e parágrafo são UMA linha de texto, e o que os separa é só qual
    estilo do tema os escreve. É esta base que o escritor genérico do §6 recebe."""

    texto: str


class Titulo(BlocoTextual):
    tipo: Literal["titulo"] = "titulo"


class Subtitulo(BlocoTextual):
    tipo: Literal["subtitulo"] = "subtitulo"
    # Nível é escala do mesmo bloco, não bloco próprio: o que muda é o corpo da fonte. Três níveis
    # bastam para a hierarquia de um ato administrativo, e o `Literal` recusa o quarto.
    nivel: Literal[1, 2, 3] = 1


class Paragrafo(BlocoTextual):
    tipo: Literal["paragrafo"] = "paragrafo"
    # Recuo é variação do mesmo bloco, não bloco próprio: o que muda é a margem, não a natureza do
    # que se lê. Transcrição e citação em documento oficial saem assim.
    recuado: bool = False


class Lista(BlocoDocumento):
    """Um bloco por lista, não por item: a numeração é a posição do item, e nada precisa contar."""

    tipo: Literal["lista"] = "lista"
    ordenada: bool = False
    itens: tuple[str, ...] = Field(min_length=1)


class Tabela(BlocoDocumento):
    """A coluna é declarada como TIPO — fixa em milímetros ou fluida por peso — e só vira medida na
    página. `ColunaFixa` e `ColunaFluida` são o vocabulário da SPEC 002."""

    tipo: Literal["tabela"] = "tabela"
    colunas: tuple[Coluna, ...] = Field(min_length=1)
    linhas: tuple[tuple[str, ...], ...] = Field(min_length=1)
    # `None` é a tabela sem cabeçalho, não um cabeçalho vazio: presença é dado, não bandeira.
    cabecalho: tuple[str, ...] | None = None


class Imagem(BlocoDocumento):
    tipo: Literal["imagem"] = "imagem"
    # Caminho já resolvido: o domínio não sabe onde ficam os estáticos do projeto.
    caminho: Path
    # Sem default: quanto a imagem ocupa é decisão do documento, não do tema.
    largura_mm: float


Bloco = Annotated[
    Titulo | Subtitulo | Paragrafo | Lista | Tabela | Imagem,
    Field(discriminator="tipo"),
]
