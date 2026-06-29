import re

MARCADOR_NUMERO = r"(?:n(?:[º°o]|ro|[uú]m(?:ero)?)?\.?|#)"
SO_MARCADOR = re.compile(rf"^{MARCADOR_NUMERO}$", re.IGNORECASE)
NUMERO_IMOVEL = re.compile(rf"{MARCADOR_NUMERO}?\s*(\d+)", re.IGNORECASE)


def parse_numero_imovel(token: str) -> int | None:
    """Extrai o número de imóvel de um token, tolerando marcadores e sufixos de unidade."""
    m = NUMERO_IMOVEL.match(token.strip())
    return int(m.group(1)) if m else None


def eh_so_marcador(token: str) -> bool:
    """True se o token for exclusivamente um marcador de número (ex.: 'nº', 'nro')."""
    return SO_MARCADOR.fullmatch(token.strip()) is not None
