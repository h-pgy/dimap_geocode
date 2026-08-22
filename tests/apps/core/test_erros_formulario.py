from django.core.exceptions import ValidationError

from apps.core.erros_formulario import de_validation_error


# ---------------------------------------------------------------------------
# de_validation_error — error_dict preserva o code; a mensagem é a do model
# ---------------------------------------------------------------------------


def test_ponte_do_django_preserva_o_codigo() -> None:
    recusa = ValidationError(
        {"email": ValidationError("Já existe servidor com este e-mail.", code="unique")}
    )

    erros = de_validation_error(recusa)

    assert len(erros) == 1
    erro = erros[0]
    assert erro.controle == "email"
    assert erro.tipo == "unique"
    assert erro.mensagem == "Já existe servidor com este e-mail."
