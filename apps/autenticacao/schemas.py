"""
DTOs da entrada no sistema (SPEC autenticacao/001): a consulta dinâmica de estado do RF, a
submissão de credenciais e a validação do código de uso único do primeiro acesso. A definição e a
redefinição de senha (SPEC autenticacao/002), e a recuperação de senha por e-mail (SPEC
autenticacao/003), entram aqui também.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr

from apps.user_admin.schemas import RegistroFuncional


class ConsultaRfInput(BaseModel):
    """A consulta dinâmica de estado do RF digitado na tela de login."""

    model_config = ConfigDict(frozen=True)

    rf: RegistroFuncional


class LoginInput(BaseModel):
    """A submissão de credenciais para autenticação padrão."""

    model_config = ConfigDict(frozen=True)

    rf: RegistroFuncional
    senha: SecretStr = Field(min_length=1)


class ValidacaoOtpInput(BaseModel):
    """A validação do código OTP de uso único no primeiro login."""

    model_config = ConfigDict(frozen=True)

    rf: RegistroFuncional
    codigo_otp: SecretStr = Field(min_length=8, max_length=8)


class EstadoRfOutput(BaseModel):
    """O estado resolvido do RF para renderização do partial do login."""

    model_config = ConfigDict(frozen=True)

    rf: str
    eh_primeiro_login: bool
    rf_encontrado: bool
    # SPEC autenticacao/003: há um link de redefinição emitido e ainda válido para este RF — o
    # partial do login avisa, para quem chegou aqui sem lembrar que pediu.
    recuperacao_em_aberto: bool = False


class DefinicaoSenhaInput(BaseModel):
    """A gravação da senha definitiva no primeiro acesso (sem senha atual)."""

    model_config = ConfigDict(frozen=True)

    nova_senha: SecretStr = Field(min_length=1)
    confirmacao_senha: SecretStr = Field(min_length=1)


class RedefinicaoSenhaInput(BaseModel):
    """A alteração de senha por servidor autenticado (com senha atual)."""

    model_config = ConfigDict(frozen=True)

    senha_atual: SecretStr = Field(min_length=1)
    nova_senha: SecretStr = Field(min_length=1)
    confirmacao_senha: SecretStr = Field(min_length=1)


class PedidoRecuperacaoInput(BaseModel):
    """O pedido de recuperação submetido na tela (SPEC autenticacao/003)."""

    model_config = ConfigDict(frozen=True)

    rf: RegistroFuncional
    # Esquema e host da requisição: o link precisa ser absoluto, e o domínio é da orquestração.
    base_url: HttpUrl
    validade_horas: int


class DestinoRecuperacaoOutput(BaseModel):
    """Para onde o link iria — o que a tela mostra antes de qualquer envio. Os três estados são
    excludentes, e cada um leva a uma tela diferente: o envio, a tarja de conta inexistente e o
    desvio para o primeiro acesso."""

    model_config = ConfigDict(frozen=True)

    rf: str
    nome: str = ""
    email: str = ""
    estado: Literal["recuperavel", "sem_conta", "primeiro_acesso"]


class LinkRecuperacaoInput(BaseModel):
    """As duas partes do link de uso único, como chegam da rota."""

    model_config = ConfigDict(frozen=True)

    uidb64: str = Field(min_length=1)
    token: str = Field(min_length=1)
