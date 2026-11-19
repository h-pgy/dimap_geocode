from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import QueryDict
from pydantic import BaseModel, Field, ValidationError, field_validator

from apps.core.erros_formulario import de_validation_error
from apps.faq.models import PalavraChave as PalavraChaveModel
from services.domain.faq import PalavraChave
from services.utils.erros_formulario import (
    CampoDeFormulario,
    ErroBruto,
    Formulario,
    LeitorDeFormulario,
    RecusaDeFormulario,
    TradutorDeRecusa,
)

from .cadastro import (
    gravar_palavra_chave,
    gravar_tema,
    renomear_palavra_chave,
    renomear_tema,
)

CONTROLE_NOME = "nome"
CONTROLE_PAI = "pai"
CONTROLE_RELACIONADA = "relacionada"

FORMULARIO_TEMA = Formulario(
    campos=(
        CampoDeFormulario(controle=CONTROLE_NOME, rotulo="Nome"),
        CampoDeFormulario(controle=CONTROLE_PAI, rotulo="Dentro de"),
    ),
)
FORMULARIO_PALAVRA_CHAVE = Formulario(
    campos=(
        CampoDeFormulario(controle=CONTROLE_NOME, rotulo="Nome"),
        CampoDeFormulario(controle=CONTROLE_PAI, rotulo="Dentro de"),
        CampoDeFormulario(controle=CONTROLE_RELACIONADA, rotulo="Relacionadas"),
    ),
)


class NovoNoArvore(BaseModel):
    """Tema ou palavra-chave nova, como o modal a envia."""

    nome: str = Field(min_length=2, max_length=80)
    pai_id: int | None = None
    relacionadas: list[int] = []

    @field_validator("nome", mode="before")
    @classmethod
    def _aparar(cls, valor: str) -> str:
        return valor.strip() if isinstance(valor, str) else valor


class NovoNome(BaseModel):
    nome: str = Field(min_length=2, max_length=80)

    @field_validator("nome", mode="before")
    @classmethod
    def _aparar(cls, valor: str) -> str:
        return valor.strip() if isinstance(valor, str) else valor


ler_tema = LeitorDeFormulario(NovoNoArvore, FORMULARIO_TEMA)
ler_palavra_chave = LeitorDeFormulario(NovoNoArvore, FORMULARIO_PALAVRA_CHAVE)
ler_nome_de_tema = LeitorDeFormulario(NovoNome, FORMULARIO_TEMA)
ler_nome_de_palavra = LeitorDeFormulario(NovoNome, FORMULARIO_PALAVRA_CHAVE)


def valores_do_modal(post: QueryDict) -> dict[str, object]:
    return {
        "nome": post.get(CONTROLE_NOME, ""),
        "pai_id": post.get(CONTROLE_PAI) or None,
        "relacionadas": [v for v in post.getlist(CONTROLE_RELACIONADA) if v.isdigit()],
    }


def criar_tema(post: QueryDict) -> RecusaDeFormulario | int:
    leitura = ler_tema(valores_do_modal(post))
    if leitura.dto is None:
        assert leitura.recusa is not None
        return leitura.recusa
    try:
        return gravar_tema(leitura.dto.nome, leitura.dto.pai_id)
    except DjangoValidationError as erro:
        return TradutorDeRecusa(FORMULARIO_TEMA)(de_validation_error(erro))


def renomear_tema_do_modal(tema_id: int, post: QueryDict) -> RecusaDeFormulario | None:
    leitura = ler_nome_de_tema({"nome": post.get(CONTROLE_NOME, "")})
    if leitura.dto is None:
        return leitura.recusa
    try:
        renomear_tema(tema_id, leitura.dto.nome)
    except DjangoValidationError as erro:
        return TradutorDeRecusa(FORMULARIO_TEMA)(de_validation_error(erro))
    return None


def criar_palavra_chave(post: QueryDict) -> RecusaDeFormulario | int:
    leitura = ler_palavra_chave(valores_do_modal(post))
    if leitura.dto is None:
        assert leitura.recusa is not None
        return leitura.recusa
    pai = (
        PalavraChaveModel.objects.select_related("pai__pai")
        .filter(pk=leitura.dto.pai_id)
        .first()
        if leitura.dto.pai_id is not None
        else None
    )
    try:
        palavra = PalavraChave(
            nome=leitura.dto.nome,
            pai=_palavra_chave(pai) if pai is not None else None,
            relacionadas=leitura.dto.relacionadas,
        )
    except ValidationError as recusa:
        # Os três níveis são regra do domínio, mas quem está errado na tela é o "Dentro de".
        return TradutorDeRecusa(FORMULARIO_PALAVRA_CHAVE)(
            [
                ErroBruto(
                    controle=CONTROLE_PAI,
                    tipo=erro["type"],
                    mensagem=str(erro["ctx"]["error"]),
                )
                if not erro["loc"]
                else ErroBruto(controle=str(erro["loc"][0]), tipo=erro["type"])
                for erro in recusa.errors()
            ],
        )
    try:
        return gravar_palavra_chave(palavra)
    except DjangoValidationError as erro:
        return TradutorDeRecusa(FORMULARIO_PALAVRA_CHAVE)(de_validation_error(erro))


def renomear_palavra_do_modal(
    palavra_id: int, post: QueryDict
) -> RecusaDeFormulario | None:
    leitura = ler_nome_de_palavra({"nome": post.get(CONTROLE_NOME, "")})
    if leitura.dto is None:
        return leitura.recusa
    try:
        renomear_palavra_chave(palavra_id, leitura.dto.nome)
    except DjangoValidationError as erro:
        return TradutorDeRecusa(FORMULARIO_PALAVRA_CHAVE)(de_validation_error(erro))
    return None


def _palavra_chave(registro: PalavraChaveModel) -> PalavraChave:
    pai = _palavra_chave(registro.pai) if registro.pai is not None else None
    return PalavraChave(id=registro.pk, nome=registro.nome, pai=pai)
