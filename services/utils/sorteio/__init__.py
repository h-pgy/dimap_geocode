import random
from collections.abc import Sequence


def sortear_diferente(opcoes: Sequence[str], atual: str | None) -> str:
    """Sorteia entre as opções, evitando `atual`. Com uma única opção, devolve ela."""
    alternativas = [opcao for opcao in opcoes if opcao != atual] or list(opcoes)
    return random.choice(alternativas)
