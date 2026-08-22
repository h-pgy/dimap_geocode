from services.utils.erros_formulario import (
    CampoDeFormulario,
    ErroBruto,
    Formulario,
    RegraDeErro,
    TomDeRealce,
    TradutorDeRecusa,
)


def _campo(controle: str, rotulo: str, regras: dict[str, RegraDeErro] | None = None) -> CampoDeFormulario:
    return CampoDeFormulario(controle=controle, rotulo=rotulo, regras=regras or {})


def _formulario(*campos: CampoDeFormulario) -> Formulario:
    return Formulario(campos=campos)


# ---------------------------------------------------------------------------
# Regra declarada no catálogo vence a regra padrão do tipo
# ---------------------------------------------------------------------------


def test_regra_declarada_vence_a_padrao() -> None:
    email = _campo(
        "email",
        "E-mail",
        regras={"value_error": RegraDeErro(mensagem="E-mail inválido: confira o endereço.", tom=TomDeRealce.ALERTA)},
    )
    tradutor = TradutorDeRecusa(_formulario(email))

    recusa = tradutor(
        (
            ErroBruto(controle="email", tipo="value_error"),
            ErroBruto(controle="email", tipo="missing"),
        )
    )

    declarado, padrao = recusa.campos
    assert declarado.mensagem == "E-mail inválido: confira o endereço."
    assert declarado.tom == TomDeRealce.ALERTA
    # "missing" não é declarado por este campo: cai na REGRA_PADRAO do tipo, com o tom padrão.
    assert padrao.mensagem == "Preencha o campo E-mail."
    assert padrao.tom == TomDeRealce.ERRO


# ---------------------------------------------------------------------------
# Tipo fora do catálogo e fora das regras padrão não quebra a tradução
# ---------------------------------------------------------------------------


def test_tipo_desconhecido_nao_quebra_a_traducao() -> None:
    tradutor = TradutorDeRecusa(_formulario(_campo("email", "E-mail")))

    recusa = tradutor((ErroBruto(controle="email", tipo="tipo_nunca_visto"),))

    assert recusa.campos[0].mensagem == "E-mail: valor inválido."


# ---------------------------------------------------------------------------
# Mensagem que a fonte já entrega em português vence a do catálogo
# ---------------------------------------------------------------------------


def test_mensagem_da_fonte_e_preservada() -> None:
    tradutor = TradutorDeRecusa(_formulario(_campo("email", "E-mail")))

    recusa = tradutor(
        (ErroBruto(controle="email", tipo="unique", mensagem="Já existe servidor com este e-mail."),)
    )

    assert recusa.campos[0].mensagem == "Já existe servidor com este e-mail."


# ---------------------------------------------------------------------------
# Erro sem controle correspondente vai para a tarja, sem realçar nada
# ---------------------------------------------------------------------------


def test_erro_sem_controle_vai_para_a_tarja_sem_realce() -> None:
    tradutor = TradutorDeRecusa(_formulario(_campo("email", "E-mail")))

    recusa = tradutor((ErroBruto(controle="__all__", tipo="value_error", mensagem="Regra cruza dois campos."),))

    assert recusa.gerais == ("Regra cruza dois campos.",)
    assert recusa.campos == ()
    assert recusa.realce == {}
