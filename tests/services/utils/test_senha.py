"""
Testes de services/utils/senha.py (SPEC criacao_usuarios/004): a senha temporária que sai gravada
com marca de uso único e chega ao servidor por e-mail — curta, numérica e sorteada por
`secrets.choice`, nunca por `random`.
"""

from services.utils.senha import DIGITOS, PoliticaSenhaTemporaria, gerar_senha_temporaria


def test_senha_temporaria_respeita_a_politica() -> None:
    politica = PoliticaSenhaTemporaria()

    primeira = gerar_senha_temporaria(politica).get_secret_value()
    segunda = gerar_senha_temporaria(politica).get_secret_value()

    assert len(primeira) == politica.comprimento
    assert all(caractere in DIGITOS for caractere in primeira)
    assert primeira != segunda
