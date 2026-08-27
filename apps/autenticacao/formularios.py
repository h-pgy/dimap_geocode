"""
Catálogo dos formulários de login, primeiro acesso e definição/redefinição de senha (SPEC
autenticacao/001 e 002): quem devolve a recusa é o próprio `<form>`, e não o partial genérico —
skill `erros-de-formulario`.
"""

from apps.autenticacao.schemas import DefinicaoSenhaInput, RedefinicaoSenhaInput
from services.utils.erros_formulario import (
    CampoDeFormulario,
    Formulario,
    LeitorDeFormulario,
    TradutorDeRecusa,
)

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

# SPEC autenticacao/002: um catálogo só para os três controles, compartilhado entre o primeiro
# acesso (sem senha_atual) e a redefinição voluntária — a política forte fala por si, então
# nenhuma regra própria de complexidade entra aqui.
FORMULARIO_SENHA = Formulario(
    campos=(
        CampoDeFormulario(controle="senha_atual", rotulo="Senha atual"),
        CampoDeFormulario(controle="nova_senha", rotulo="Nova senha"),
        CampoDeFormulario(controle="confirmacao_senha", rotulo="Confirmar senha"),
    )
)

ler_definicao_senha = LeitorDeFormulario(DefinicaoSenhaInput, FORMULARIO_SENHA)
ler_redefinicao_senha = LeitorDeFormulario(RedefinicaoSenhaInput, FORMULARIO_SENHA)
traduzir_recusa_senha = TradutorDeRecusa(FORMULARIO_SENHA)
