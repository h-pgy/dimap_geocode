"""
A política de senha forte da credencial definitiva do servidor (SPEC autenticacao/002): as regras
de complexidade e as frases de recusa que a definição e a redefinição de senha compartilham.
"""

from pydantic import BaseModel, ConfigDict

CARACTERES_ESPECIAIS = "!@#$%^&*()_+-=[]{}|;:,.<>?"

ERRO_SENHAS_DIVERGENTES = "As senhas digitadas não coincidem: confira a confirmação."
ERRO_SENHA_FRACA_COMPRIMENTO = "A nova senha deve ter no mínimo 8 caracteres."
ERRO_SENHA_FRACA_MAIUSCULA = "A nova senha deve conter pelo menos uma letra maiúscula."
ERRO_SENHA_FRACA_ESPECIAL = "A nova senha deve conter pelo menos um caractere especial (!@#$%...)."
ERRO_SENHA_ATUAL_INCORRETA = "A senha atual informada está incorreta."


class PoliticaSenhaForte(BaseModel):
    """As regras de complexidade exigidas para a senha definitiva do servidor."""

    model_config = ConfigDict(frozen=True)

    comprimento_minimo: int = 8
    exige_maiuscula: bool = True
    exige_especial: bool = True


def validar_complexidade_senha(senha: str, politica: PoliticaSenhaForte | None = None) -> list[str]:
    """Retorna a lista de motivos caso a senha não atenda à política forte."""
    politica_aplicada = politica or PoliticaSenhaForte()
    erros = []
    if len(senha) < politica_aplicada.comprimento_minimo:
        erros.append(ERRO_SENHA_FRACA_COMPRIMENTO)
    if politica_aplicada.exige_maiuscula and not any(c.isupper() for c in senha):
        erros.append(ERRO_SENHA_FRACA_MAIUSCULA)
    if politica_aplicada.exige_especial and not any(c in CARACTERES_ESPECIAIS for c in senha):
        erros.append(ERRO_SENHA_FRACA_ESPECIAL)
    return erros
