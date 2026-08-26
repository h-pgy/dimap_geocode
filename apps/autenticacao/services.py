"""
A resolução de estado do RF na tela de login e a validação da senha provisória do primeiro acesso
(SPEC autenticacao/001).
"""

from apps.autenticacao.schemas import ConsultaRfInput, EstadoRfOutput, ValidacaoOtpInput
from apps.user_admin.models import Perfil


def resolver_estado_rf(consulta: ConsultaRfInput) -> EstadoRfOutput:
    # RF inexistente devolve o mesmo formato de saída do RF já ativo: é o que impede a
    # enumeração de RFs válidos por força bruta (SPEC, Caveats).
    try:
        perfil = Perfil.objects.get(rf=consulta.rf, is_active=True)
        return EstadoRfOutput(
            rf=consulta.rf,
            eh_primeiro_login=perfil.senha_provisoria,
            rf_encontrado=True,
        )
    except Perfil.DoesNotExist:
        return EstadoRfOutput(
            rf=consulta.rf,
            eh_primeiro_login=False,
            rf_encontrado=False,
        )


def autenticar_primeiro_login(validacao: ValidacaoOtpInput) -> Perfil | None:
    # A senha temporária mora no mesmo hash de sempre: `check_password` é quem confere o OTP.
    try:
        perfil = Perfil.objects.get(rf=validacao.rf, is_active=True, senha_provisoria=True)
    except Perfil.DoesNotExist:
        return None
    if not perfil.check_password(validacao.codigo_otp.get_secret_value()):
        return None
    return perfil
