"""
Catálogo do formulário de delegação nominal (SPEC autorizacao/009).
"""

from apps.competencias.schemas import NovaDelegacao
from services.utils.erros_formulario import (
    CampoDeFormulario,
    Formulario,
    LeitorDeFormulario,
    RegraDeErro,
    TradutorDeRecusa,
)

FORMULARIO_DELEGACAO = Formulario(
    campos=(
        CampoDeFormulario(controle="delegado", rotulo="Servidor"),
        CampoDeFormulario(controle="data_inicio", rotulo="Início da vigência"),
        CampoDeFormulario(
            controle="data_fim",
            rotulo="Fim da vigência",
            regras={
                "fim_antes_do_inicio": RegraDeErro(
                    mensagem="Fim da delegação não pode anteceder o início."
                )
            },
        ),
    ),
)

ler_nova_delegacao = LeitorDeFormulario(NovaDelegacao, FORMULARIO_DELEGACAO)
traduzir_recusa_delegacao = TradutorDeRecusa(FORMULARIO_DELEGACAO)
