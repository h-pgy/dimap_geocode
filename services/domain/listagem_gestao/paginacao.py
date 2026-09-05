from collections.abc import Sequence
from math import ceil

from services.domain.listagem_gestao.models.consulta import LinhaT, Pagina


def paginar(linhas: Sequence[LinhaT], numero: int, tamanho: int) -> Pagina[LinhaT]:
    """Pagina DEPOIS do filtro do cabeçalho, nunca antes: paginar o conjunto cru faria a página 2 de
    um resultado filtrado mostrar linhas que o filtro já tinha descartado.

    O número é preso entre 1 e a última página em vez de recusado — `?pagina=999` é dedo torto ou
    link velho, não tentativa de nada, e devolver erro para isso troca uma tela por uma falha.
    Lista vazia tem UMA página, não zero: "página 1 de 0" não é frase que se escreva na tela.
    """
    total_paginas = max(1, ceil(len(linhas) / tamanho))
    atual = min(max(numero, 1), total_paginas)
    inicio = (atual - 1) * tamanho
    return Pagina(
        linhas=tuple(linhas[inicio : inicio + tamanho]),
        numero=atual,
        total_paginas=total_paginas,
        total_linhas=len(linhas),
    )
