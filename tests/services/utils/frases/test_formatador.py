import pytest

from services.utils.frases import FormatadorDeFrases, formatar_frases


@pytest.mark.parametrize(
    "texto, esperado",
    [
        (
            "como pago o IPTU. posso parcelar? sim!  e depois",
            "Como pago o IPTU. Posso parcelar? Sim! E depois",
        ),
        ("  2ª via   do carnê ", "2ª via do carnê"),
        ('"isenção" vale?', '"Isenção" vale?'),
        ("o valor é R$ 1.000,00", "O valor é R$ 1.000,00"),
        ("", ""),
    ],
)
def test_capitaliza_cada_frase_e_colapsa_espacos(texto: str, esperado: str) -> None:
    assert formatar_frases(texto) == esperado


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("como pago o IPTU", "Como pago o IPTU?"),
        ("como pago o IPTU.", "Como pago o IPTU?"),
        ("como pago o IPTU ?!", "Como pago o IPTU?"),
        ("como pago o IPTU?", "Como pago o IPTU?"),
        ("tenho imóvel. quem paga", "Tenho imóvel. Quem paga?"),
    ],
)
def test_ultimo_caractere_vale_para_a_sequencia(texto: str, esperado: str) -> None:
    assert FormatadorDeFrases(ultimo="?")(texto) == esperado


def test_primeiro_caractere_vale_para_a_sequencia_sem_duplicar() -> None:
    formatar = FormatadorDeFrases(primeiro="¿", ultimo="?")
    assert formatar("cómo estás") == "¿Cómo estás?"
    assert formatar("¿cómo estás?") == "¿Cómo estás?"


def test_inicio_e_fim_por_frase_convivem_com_os_da_sequencia() -> None:
    formatar = FormatadorDeFrases(
        primeiro="— ",
        ultimo="!",
        inicio_de_frase="¿",
        fim_de_frase="?",
    )
    assert formatar("tenho imóvel. quem paga.  posso parcelar") == (
        "— ¿Tenho imóvel? ¿Quem paga? ¿Posso parcelar!"
    )
