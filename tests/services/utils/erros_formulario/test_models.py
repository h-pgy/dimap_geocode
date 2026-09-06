from services.utils.erros_formulario import CampoRecusado, RecusaDeFormulario, TomDeRealce


def _campo_recusado(controle: str, tom: TomDeRealce = TomDeRealce.ERRO) -> CampoRecusado:
    return CampoRecusado(controle=controle, mensagem="mensagem qualquer", tom=tom)


# ---------------------------------------------------------------------------
# realce — a classe do tom por controle recusado, nada para os demais
# ---------------------------------------------------------------------------


def test_realce_traz_a_classe_por_controle() -> None:
    recusa = RecusaDeFormulario(campos=(_campo_recusado("email", tom=TomDeRealce.ALERTA),))

    assert recusa.realce["email"] == TomDeRealce.ALERTA.value
    # controle que não foi recusado: chave ausente, o Django renderiza string vazia sozinho.
    assert "rf" not in recusa.realce
