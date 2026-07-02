from enum import Enum

from services.domain.logradouro_geocod import SegmentoLogradouroAttributes


class Paridade(Enum):
    IMPAR = 1
    PAR = 2


def intervalo_numeracao(
    attrs: SegmentoLogradouroAttributes, paridade: Paridade
) -> tuple[int | None, int | None]:
    """Par (inicial, final) da numeração do lado par/ímpar do segmento. Compartilhado pelo
    geocoder e pelo solver de orientação — evita duplicar a tradução paridade -> colunas."""
    if paridade is Paridade.PAR:
        return attrs.numero_inicial_par, attrs.numero_final_par
    return attrs.numero_inicial_impar, attrs.numero_final_impar


def limite_inicial(attrs: SegmentoLogradouroAttributes, paridade: Paridade) -> int:
    """Início do intervalo, já sem `None`. Só é chamada sobre segmentos que passaram por
    `_filtrar_com_numeracao` (ambos os lados garantidamente não-nulos para a paridade)."""
    inicio, _ = intervalo_numeracao(attrs, paridade)
    assert inicio is not None
    return inicio


def limite_final(attrs: SegmentoLogradouroAttributes, paridade: Paridade) -> int:
    """Fim do intervalo, já sem `None` — ver `limite_inicial`."""
    _, fim = intervalo_numeracao(attrs, paridade)
    assert fim is not None
    return fim
