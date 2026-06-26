from .constants import QWERTY_ABNT2_NEIGHBORS

def gerar_variacoes_nome(nome: str) -> set[str]:
    vizinhos = QWERTY_ABNT2_NEIGHBORS
    variacoes: set[str] = set()
    for i, ch in enumerate(nome):
        for vizinho in vizinhos.get(ch, ""):
            variacoes.add(nome[:i] + vizinho + nome[i + 1:])
    variacoes.discard(nome)
    return variacoes

def gerar_todas_as_variacoes(dados_aumentados_normalizados: dict[str, str]) -> list[tuple[str, str]]:
    
    variacoes_acumuladas: list[tuple[str, str]] = []
    chaves_originais: set[str] = set(dados_aumentados_normalizados.keys())

    for nome, codigo in dados_aumentados_normalizados.items():
        for variacao in gerar_variacoes_nome(nome):
            if variacao not in chaves_originais:
                variacoes_acumuladas.append((variacao, codigo))
    
    return variacoes_acumuladas