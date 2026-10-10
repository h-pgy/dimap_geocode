from typing import Self

from pydantic import BaseModel, model_validator

from services.utils.erros_formulario import (
    CampoDeFormulario,
    Formulario,
    LeitorDeFormulario,
    controle_do_campo,
)


class _NovoServidorFake(BaseModel):
    rf: str
    unidade_id: int


class _PedidoComRegraCruzadaFake(BaseModel):
    de: int
    ate: int

    @model_validator(mode="after")
    def _de_antes_de_ate(self) -> Self:
        if self.de > self.ate:
            raise ValueError("O início não pode vir depois do fim.")
        return self


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


def test_regra_que_cruza_campos_vira_recusa_geral_sem_realce() -> None:
    formulario = Formulario(
        campos=(
            CampoDeFormulario(controle="de", rotulo="De"),
            CampoDeFormulario(controle="ate", rotulo="Até"),
        )
    )
    ler = LeitorDeFormulario(_PedidoComRegraCruzadaFake, formulario)

    leitura = ler({"de": 5, "ate": 2})

    assert leitura.dto is None
    assert leitura.recusa is not None
    # A mensagem é a do próprio validator: sem controle para realçar, ela sai na tarja.
    assert leitura.recusa.gerais == ("O início não pode vir depois do fim.",)
    assert leitura.recusa.realce == {}
