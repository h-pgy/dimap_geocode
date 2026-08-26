"""
Catálogo dos formulários de login e de primeiro acesso (SPEC autenticacao/001): quem devolve a
recusa é o próprio `<form>`, e não o partial genérico — skill `erros-de-formulario`.
"""

from services.utils.erros_formulario import CampoDeFormulario, Formulario, TradutorDeRecusa

FORMULARIO_LOGIN = Formulario(
    campos=(
        # A recusa não aponta RF nem senha: revelar qual dos dois está errado devolveria a
        # enumeração de RFs válidos que o partial dinâmico já se recusa a entregar.
        CampoDeFormulario(controle="rf", rotulo="RF"),
    )
)

FORMULARIO_OTP = Formulario(
    campos=(CampoDeFormulario(controle="otp", rotulo="Senha de uso único"),)
)

traduzir_recusa_login = TradutorDeRecusa(FORMULARIO_LOGIN)
traduzir_recusa_otp = TradutorDeRecusa(FORMULARIO_OTP)
