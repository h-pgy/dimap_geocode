import re
from pathlib import Path


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
