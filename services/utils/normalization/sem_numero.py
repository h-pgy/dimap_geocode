import re

# Token canônico único para qualquer grafia de "sem número".
CANONICO_SEM_NUMERO = "SN"

# Regex aplicada SOBRE O TEXTO JÁ NORMALIZADO (saída de normalize_text), nunca sobre o cru:
# reconhece as formas que "sem número" assume depois da normalização (comportamento REAL
# conferido da normalize_text) —
#   S N (s/n, s.n., s/n°)  |  SN (sn)  |  S NO (s/no)  |  S Nº (s/nº)  |  SEM NUMERO (sem número).
# O 'º' ordinal é letra Unicode (\w) e NÃO decompõe em NFD — sobrevive à normalize_text —,
# por isso a regex precisa aceitá-lo. Já o '°' (degree sign) é símbolo e vira espaço.
# Ancorada (fullmatch): números comuns (10, 10A) não casam e passam intactos.
SEM_NUMERO_NORMALIZADO = re.compile(r"^S\s*N(?:[ºO]|UMERO)?$|^SEM\s*NUMERO$")


class SemNumeroNormalizer:
    """Canoniza as grafias de 'sem número' num token único.

    ASSUME input JÁ normalizado por normalize_text (§7.1) — é o passo 2 da chave, o
    'regex de dois lados' que só faz sentido sobre a saída da normalização padrão.
    Entrada que não casa 'sem número' (número comum) volta INTACTA.
    """

    def __call__(self, texto_normalizado: str) -> str:
        if SEM_NUMERO_NORMALIZADO.fullmatch(texto_normalizado):
            return CANONICO_SEM_NUMERO
        return texto_normalizado
