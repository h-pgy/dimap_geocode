from pydantic import BaseModel

from services.utils.erros_formulario import (
    CampoDeFormulario,
    Formulario,
    LeitorDeFormulario,
    controle_do_campo,
)


class _NovoServidorFake(BaseModel):
    rf: str
    unidade_id: int


def _formulario() -> Formulario:
    return Formulario(
        campos=(
            CampoDeFormulario(controle="rf", rotulo="RF"),
            CampoDeFormulario(controle="unidade", rotulo="Unidade"),
        )
    )


# ---------------------------------------------------------------------------
# controle_do_campo — o sufixo _id do DTO cai para bater com o name= do template
# ---------------------------------------------------------------------------


def test_sufixo_id_vira_o_nome_do_controle() -> None:
    assert controle_do_campo("unidade_id") == "unidade"
    assert controle_do_campo("rf") == "rf"


# ---------------------------------------------------------------------------
# LeitorDeFormulario — ou o DTO, ou a recusa; nunca os dois, nunca nenhum
# ---------------------------------------------------------------------------


def test_leitor_devolve_o_dto_ou_a_recusa() -> None:
    ler = LeitorDeFormulario(_NovoServidorFake, _formulario())

    leitura_valida = ler({"rf": "123.456-7", "unidade_id": 1})
    leitura_invalida = ler({"rf": "123.456-7", "unidade_id": "não é número"})

    assert leitura_valida.dto is not None
    assert leitura_valida.recusa is None
    assert leitura_invalida.dto is None
    assert leitura_invalida.recusa is not None
    # unidade_id vira o controle "unidade": o mesmo nome que o <select> usa no template.
    assert leitura_invalida.recusa.realce["unidade"] != ""
