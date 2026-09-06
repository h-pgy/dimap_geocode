from django.core.exceptions import ValidationError

from services.utils.erros_formulario import ErroBruto, controle_do_campo

TIPO_SEM_CODIGO = "sem_codigo"


def de_validation_error(recusa: ValidationError) -> tuple[ErroBruto, ...]:
    """`error_dict`, e não `message_dict`: só ele preserva o `code` de cada recusa, que é o tipo do
    erro. A mensagem vem junto porque o Django já a escreve em português — e, no caso da unicidade,
    é o próprio model quem a define."""
    return tuple(
        ErroBruto(
            controle=controle_do_campo(campo),
            tipo=erro.code or TIPO_SEM_CODIGO,
            mensagem=mensagem,
        )
        for campo, erros in recusa.error_dict.items()
        for erro in erros
        for mensagem in erro.messages
    )
