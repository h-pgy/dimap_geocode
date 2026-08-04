import re
from collections.abc import Iterable
from pathlib import Path

from .models import EscopoCarga


def anos_do_escopo(anos: Iterable[int], escopo: EscopoCarga) -> set[int]:
    """O recorte do escopo sobre o que UMA etapa enxerga — nunca sobre o que a outra fez.

    Existe uma vez porque é a mesma regra para a coleta e para o parse; o input é que difere.
    """
    vistos = set(anos)
    if escopo is EscopoCarga.COMPLETO or not vistos:
        return vistos
    return {max(vistos)}


def anos_em_disco(pasta: Path, padrao: re.Pattern[str]) -> dict[int, Path]:
    """Os anos que a pasta tem — arquivo fora do padrão do nome é ignorado.

    É por aqui que cada etapa lê o que a anterior deixou sem saber o que ela fez.
    """
    if not pasta.exists():
        return {}
    return {
        int(encontrado.group(1)): caminho
        for caminho in pasta.iterdir()
        if (encontrado := padrao.match(caminho.name))
    }
