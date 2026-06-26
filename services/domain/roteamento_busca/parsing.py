import re

COMECA_COM_LETRA = re.compile(r"[^\W\d_]", re.UNICODE)
NUMERO = re.compile(r"\d+[A-Za-z]?")


def separar_numero(texto: str) -> tuple[str, str] | None:
    """(texto_do_logradouro, numero) como digitados, ou None se não há nº de imóvel."""
    limpo = texto.strip()
    if not COMECA_COM_LETRA.match(limpo):
        return None
    head, _, resto = limpo.partition(",")
    tokens = head.split()
    if len(tokens) > 1 and NUMERO.fullmatch(tokens[-1]):
        return " ".join(tokens[:-1]), tokens[-1]
    # primeiro token do resto pode ter vírgula residual: "3, bairro" → token "3,"
    if resto:
        primeiro = resto.strip().split(",")[0].strip()
        if primeiro and NUMERO.fullmatch(primeiro):
            return head.strip(), primeiro
    return None


def split_tipo_nome(texto: str) -> tuple[str, str]:
    """Quebra no 1º espaço: (tipo_logradouro, nome). Token único -> ('', nome). Sem normalizar."""
    partes = texto.strip().split(" ", 1)
    if len(partes) < 2:
        return "", (partes[0] if partes else "")
    return partes[0], partes[1]
