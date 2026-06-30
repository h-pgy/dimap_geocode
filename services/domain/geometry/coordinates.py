from typing import Any


def eh_ponto(coords: Any) -> bool:
    """Um PONTO é uma posição GeoJSON 2D: sequência com exatamente 2 números [lon, lat].
    Trabalhamos só com dados 2D — posições 3D (com z) são rejeitadas de propósito."""
    # `bool` é subclasse de `int` em Python (isinstance(True, int) é True); o `not isinstance`
    # impede que True/False passem como coordenada.
    return (
        isinstance(coords, (list, tuple))
        and len(coords) == 2
        and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in coords)
    )


def eh_linha(coords: Any) -> bool:
    """Uma LINHA (aberta) é uma lista de >= 2 pontos. Compõe `eh_ponto`."""
    return isinstance(coords, list) and len(coords) >= 2 and eh_ponto(coords[0])


def eh_multilinha(coords: Any) -> bool:
    """Uma MULTILINHA é uma lista de >= 1 linha (aberta). Compõe `eh_linha`."""
    return isinstance(coords, list) and len(coords) >= 1 and eh_linha(coords[0])


def eh_anel(coords: Any) -> bool:
    """Um ANEL é uma linha FECHADA: >= 4 pontos e primeiro == último. Compõe `eh_linha`.
    A igualdade é exata (a RFC manda repetir a posição idêntica, não 'aproximadamente igual');
    comparar duas listas [lon, lat] com == já compara coordenada a coordenada."""
    return eh_linha(coords) and len(coords) >= 4 and coords[0] == coords[-1]


def eh_poligono(coords: Any) -> bool:
    """Um POLÍGONO é uma lista de >= 1 anel. Compõe `eh_anel` (valida o fechamento do 1º anel).
    Checagem rasa: só o anel-amostra (exterior) é verificado; anéis internos (buracos) não."""
    return isinstance(coords, list) and len(coords) >= 1 and eh_anel(coords[0])


def eh_multipoligono(coords: Any) -> bool:
    """Um MULTIPOLÍGONO é uma lista de >= 1 polígono. Compõe `eh_poligono`."""
    return isinstance(coords, list) and len(coords) >= 1 and eh_poligono(coords[0])
