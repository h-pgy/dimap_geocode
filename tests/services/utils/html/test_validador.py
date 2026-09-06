from services.utils.html import validar_html


# ---------------------------------------------------------------------------
# Boa-formação: elementos vazios, com e sem forma autofechada
# ---------------------------------------------------------------------------


def test_html_bem_formado_passa_com_elementos_vazios() -> None:
    texto_puro = validar_html("texto sem nenhuma marcação")
    com_vazios_sem_fechamento = validar_html(
        '<p>quebra<br>de linha<img src="foto.png">fim</p>'
    )
    com_vazio_autofechado = validar_html("<p>quebra<br/>de linha</p>")

    assert texto_puro.valido
    assert com_vazios_sem_fechamento.valido
    assert com_vazio_autofechado.valido
    assert texto_puro.erros == ()
    assert com_vazios_sem_fechamento.erros == ()
    assert com_vazio_autofechado.erros == ()
