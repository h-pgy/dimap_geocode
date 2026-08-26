"""
DTOs da entrada no sistema (SPEC autenticacao/001): a consulta dinâmica de estado do RF, a
submissão de credenciais e a validação do código de uso único do primeiro acesso.
"""

from pydantic import BaseModel, ConfigDict, Field, SecretStr

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
