from .normalizer import TextNormalizer
from .sem_numero import SemNumeroNormalizer

normalize_text = TextNormalizer()
normalize_sem_numero = SemNumeroNormalizer()


def chave_numero_porta(valor: str) -> str:
    """Chave única de match do número de porta — COMPÕE, sem normalização própria.

    1) normalize_text (§7.1): normalização padrão do projeto;
    2) normalize_sem_numero: canoniza as grafias de "sem número" (números comuns passam intactos);
    3) remove espaços residuais (ex.: '10 A' -> '10A'; o token canônico já é sem espaço).

    Fonte ÚNICA da chave: usada no computed_field numero_padronizado (input) E na
    coluna do catalog (base) — nunca duplicar. Ex.: 's/n' -> 'SN'; '10-A' -> '10A'.
    """
    return normalize_sem_numero(normalize_text(valor)).replace(" ", "")
