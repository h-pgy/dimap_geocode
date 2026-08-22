"""
A senha temporária emitida no cadastro de servidor (SPEC criacao_usuarios/004): curta, numérica e
de uso único — vale enquanto ninguém a derruba (SPEC de login, sem dono ainda).
"""

# `secrets` é da biblioteca padrão: nada a instalar. É o módulo do CPython para material
# criptográfico — senha, token, identificador — e o único correto aqui: o gerador do `random` é
# previsível, e uma senha emitida deixaria as seguintes adivinháveis.
import secrets

from pydantic import BaseModel, ConfigDict, Field, SecretStr

# Só dígito: o alfabeto misto obriga a distinguir caixa e pares ambíguos (O/0, l/1) numa senha que
# alguém vai copiar de um e-mail, às vezes do celular.
DIGITOS = "0123456789"


class PoliticaSenhaTemporaria(BaseModel):
    """O que a senha emitida tem que ser."""

    model_config = ConfigDict(frozen=True)

    comprimento: int = Field(default=8, ge=6)
    alfabeto: str = DIGITOS


class GeradorSenhaTemporaria:
    """Callable: sorteia a senha segundo a política."""

    def __call__(self, politica: PoliticaSenhaTemporaria | None = None) -> SecretStr:
        escolhida = politica or PoliticaSenhaTemporaria()
        return SecretStr(
            "".join(secrets.choice(escolhida.alfabeto) for _ in range(escolhida.comprimento))
        )


gerar_senha_temporaria = GeradorSenhaTemporaria()
