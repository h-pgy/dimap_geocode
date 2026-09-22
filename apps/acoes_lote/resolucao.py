from .declaradas import ACOES_LOTE
from .estrutura import AcaoDeLote


def acoes_liberadas(slugs: frozenset[str]) -> tuple[AcaoDeLote, ...]:
    return tuple(item for item in ACOES_LOTE.itens if item.acao.acao.slug in slugs)
