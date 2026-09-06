from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TomDeRealce(StrEnum):
    """As quatro tonalidades do átomo `.campo-realce-*`. O valor É a classe: o template recebe a
    string pronta e nenhum filtro monta nome de classe por concatenação."""

    ERRO = "campo-realce-erro"
    ALERTA = "campo-realce-alerta"
    INFO = "campo-realce-info"
    SUCESSO = "campo-realce-sucesso"


class RegraDeErro(BaseModel):
    """O que uma recusa vira na tela. `mensagem` aceita `{rotulo}`."""

    model_config = ConfigDict(frozen=True)

    mensagem: str
    tom: TomDeRealce = TomDeRealce.ERRO


class CampoDeFormulario(BaseModel):
    """Um controle. `controle` é o `name=` do input — o mesmo nome que o template pergunta ao realce."""

    model_config = ConfigDict(frozen=True)

    controle: str
    rotulo: str
    # Por tipo de erro; vence REGRAS_PADRAO. Vazio significa "as padrão bastam".
    regras: Mapping[str, RegraDeErro] = Field(default_factory=dict)


class Formulario(BaseModel):
    """O catálogo: os controles que existem e como cada recusa se diz para quem preencheu."""

    model_config = ConfigDict(frozen=True)

    campos: tuple[CampoDeFormulario, ...]

    @property
    def por_controle(self) -> Mapping[str, CampoDeFormulario]:
        return {campo.controle: campo for campo in self.campos}


class ErroBruto(BaseModel):
    """A recusa como a fonte a entrega, antes de virar frase. `mensagem` preenchida é a fonte já
    falando português — o Django fala; o Pydantic, não."""

    model_config = ConfigDict(frozen=True)

    controle: str
    tipo: str
    mensagem: str | None = None


class CampoRecusado(BaseModel):
    model_config = ConfigDict(frozen=True)

    controle: str
    mensagem: str
    tom: TomDeRealce


class RecusaDeFormulario(BaseModel):
    """O que a view leva ao template."""

    model_config = ConfigDict(frozen=True)

    campos: tuple[CampoRecusado, ...] = ()
    # Recusa que não nomeia controle: o `__all__` do Django, a regra que cruza dois campos.
    gerais: tuple[str, ...] = ()

    @property
    def mensagens(self) -> tuple[str, ...]:
        return tuple(campo.mensagem for campo in self.campos) + self.gerais

    @property
    def realce(self) -> Mapping[str, str]:
        """`{{ realce.email }}` devolve a classe; chave ausente já rende string vazia no Django."""
        return {campo.controle: campo.tom.value for campo in self.campos}


class LeituraDeFormulario[T: BaseModel](BaseModel):
    """Ou o DTO, ou a recusa — nunca os dois, nunca nenhum. É o que dispensa o `try/except` de quem
    lê um formulário."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    dto: T | None = None
    recusa: RecusaDeFormulario | None = None
