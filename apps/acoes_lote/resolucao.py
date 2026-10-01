from .estrutura import AcaoDeLote, ContratoAcoesLote


def acoes_liberadas(
    contrato: ContratoAcoesLote,
    slugs: frozenset[str],
) -> tuple[AcaoDeLote, ...]:
    return tuple(item for item in contrato.itens if item.acao.acao.slug in slugs)
