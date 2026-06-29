import re

from services.domain.address_match import eh_so_marcador, parse_numero_imovel

COMECA_COM_LETRA = re.compile(r"[^\W\d_]", re.UNICODE)


def separar_numero(texto: str) -> tuple[str, int] | None:
    """(logradouro, numero) onde numero é int, ou None se não há número de imóvel.

    Tolerante: absorve marcadores ('nº', 'n.', 'nro', '#' ...) e sufixos de unidade ('1a' → 1).
    Marcador separado do dígito ('Paulista nº 1') é descartado do texto do logradouro.
    """
    limpo = texto.strip()
    if not COMECA_COM_LETRA.match(limpo):
        return None

    head, sep, resto = limpo.partition(",")

    if sep and resto.strip():
        numero = parse_numero_imovel(resto.strip())
        if numero is not None:
            return head.strip(), numero

    # Sem vírgula (ou vírgula sem número parseável depois): verifica último(s) token(s)
    tokens = (head if sep else limpo).split()
    if len(tokens) < 2:
        return None

    numero = parse_numero_imovel(tokens[-1])
    if numero is None:
        return None

    penultimo = tokens[-2]
    if eh_so_marcador(penultimo):
        logradouro_txt = " ".join(tokens[:-2])
    else:
        logradouro_txt = " ".join(tokens[:-1])

    if not logradouro_txt:
        return None

    return logradouro_txt, numero


def separar_numero_codlog(texto: str) -> tuple[str, int] | None:
    """(codlog_txt, numero) onde numero é int, ou None se não há número de imóvel.

    Ancorado em dígito (codlog começa com dígito). Rejeita entradas com ponto
    (formato de contribuinte). Exige separador explícito entre codlog e número.
    """
    limpo = texto.strip()
    if not limpo or not limpo[0].isdigit():
        return None
    if "." in limpo:
        return None

    head, sep, resto = limpo.partition(",")

    if sep and resto.strip():
        numero = parse_numero_imovel(resto.strip())
        if numero is not None:
            return head.strip(), numero

    tokens = (head if sep else limpo).split()
    if len(tokens) < 2:
        return None

    numero = parse_numero_imovel(tokens[-1])
    if numero is None:
        return None

    penultimo = tokens[-2]
    if eh_so_marcador(penultimo):
        codlog_txt = " ".join(tokens[:-2])
    else:
        codlog_txt = " ".join(tokens[:-1])

    if not codlog_txt:
        return None

    return codlog_txt, numero


def split_tipo_nome(texto: str) -> tuple[str, str]:
    """Quebra no 1º espaço: (tipo_logradouro, nome). Token único -> ('', nome). Sem normalizar."""
    partes = texto.strip().split(" ", 1)
    if len(partes) < 2:
        return "", (partes[0] if partes else "")
    return partes[0], partes[1]
