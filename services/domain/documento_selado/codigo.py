import secrets

from .constants import ALFABETO_CODIGO, TAMANHO_CODIGO


def gerar_codigo() -> str:
    """O identificador que vai no QR, no endereço impresso e no acervo. Aleatório, nunca sequencial."""
    return "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(TAMANHO_CODIGO))
