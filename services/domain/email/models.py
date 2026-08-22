from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    SecretStr,
    model_validator,
)

# Cada caixa ocupa largura fixa, e a placa do e-mail tem 600px: acima disto a fileira quebra e o
# código deixa de se ler como um só.
LIMITE_CARACTERES_OTP = 10


class BlocoEmail(BaseModel):
    """Base dos blocos: bloco não compartilha atributo, compartilha posição no corpo."""

    model_config = ConfigDict(frozen=True)


class Titulo(BlocoEmail):
    tipo: Literal["titulo"] = "titulo"
    texto: str


class Subtitulo(BlocoEmail):
    tipo: Literal["subtitulo"] = "subtitulo"
    texto: str


class Paragrafo(BlocoEmail):
    tipo: Literal["paragrafo"] = "paragrafo"
    texto: str


class Destaque(BlocoEmail):
    """O que o e-mail quer que se leia primeiro: os dados do teste hoje, a senha temporária amanhã."""

    tipo: Literal["destaque"] = "destaque"
    rotulo: str
    valor: str
    # Monoespaçada quando o valor é para ser copiado à mão — senha, código, identificador.
    monoespacado: bool = False


def _celula_preenchida(valor: str | None) -> str:
    return "" if valor is None else valor


# Célula sem valor é célula em branco, nunca linha mais curta: a forma não depende do preenchimento.
Celula = Annotated[str, BeforeValidator(_celula_preenchida)]


class Tabela(BlocoEmail):
    """Cabeçalho opcional, porque nem toda tabela nomeia coluna; linha, nenhuma é opcional."""

    tipo: Literal["tabela"] = "tabela"
    cabecalho: tuple[Celula, ...] = ()
    linhas: tuple[tuple[Celula, ...], ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validar_forma(self) -> "Tabela":
        # Sem cabeçalho, é a primeira linha que fixa a largura da tabela.
        larguras = {len(linha) for linha in self.linhas}
        if self.cabecalho:
            larguras.add(len(self.cabecalho))
        if len(larguras) > 1:
            raise ValueError(
                f"Tabela mal estruturada: larguras {sorted(larguras)} entre cabeçalho e linhas."
            )
        return self


class Imagem(BlocoEmail):
    tipo: Literal["imagem"] = "imagem"
    # Absoluta: e-mail não tem base de onde resolver caminho relativo.
    url: HttpUrl
    # Obrigatório: bloquear imagem é o default de vários clientes, e o alternativo é o que sobra.
    alternativo: str
    largura: int | None = None


class Botao(BlocoEmail):
    tipo: Literal["botao"] = "botao"
    rotulo: str
    url: HttpUrl


class Divisor(BlocoEmail):
    """Só separa. Sem atributo: o que ele carrega é a pausa."""

    tipo: Literal["divisor"] = "divisor"


class Otp(BlocoEmail):
    """O código que se digita caractere a caractere — uma caixa por caractere, como o campo de OTP
    do design system."""

    tipo: Literal["otp"] = "otp"
    rotulo: str
    valor: str = Field(min_length=1, max_length=LIMITE_CARACTERES_OTP)


Bloco = Annotated[
    Titulo | Subtitulo | Paragrafo | Destaque | Otp | Tabela | Imagem | Botao | Divisor,
    Field(discriminator="tipo"),
]


class ConteudoEmail(BaseModel):
    """O que o e-mail diz. Assunto e rodapé ficam fora dos blocos: todo e-mail tem os dois,
    exatamente uma vez."""

    model_config = ConfigDict(frozen=True)

    assunto: str
    blocos: tuple[Bloco, ...] = Field(min_length=1)
    rodape: str


class EmailTesteInput(BaseModel):
    """O pedido do teste. Sem conta remetente: quem envia é a configuração, não o caso de uso."""

    model_config = ConfigDict(frozen=True)

    destinatario: EmailStr
    # De onde o e-mail partiu, para quem recebe saber qual ambiente está sendo provado.
    ambiente: str
    momento: datetime


class EmailAcessoInput(BaseModel):
    """O pedido do e-mail que entrega o acesso. Sem conta remetente: quem envia é a configuração,
    não o caso de uso."""

    model_config = ConfigDict(frozen=True)

    nome: str
    rf: str
    destinatario: EmailStr
    # SecretStr para a senha não aparecer em repr, log nem traceback de quem passa o pedido adiante;
    # no corpo da mensagem ela viaja em claro, que é o propósito dela.
    senha_temporaria: SecretStr
    url_acesso: HttpUrl
