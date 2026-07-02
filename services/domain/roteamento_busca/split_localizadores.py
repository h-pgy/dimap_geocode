import re
from collections.abc import Callable

from services.domain.address_match import eh_so_marcador, parse_numero_porta

COMECA_COM_LETRA = re.compile(r"[^\W\d_]", re.UNICODE)

LeitorNumero = Callable[[str], str | None]


def _separar_token_numero(texto: str, leitor: LeitorNumero) -> tuple[str, str] | None:
    """Esqueleto comum aos dois localizadores — hoje duplicado, passa a existir uma vez.

    `leitor` é o critério de split (o que conta como "token de número"); o retorno é
    sempre o token BRUTO — quem parseia (estrito ou permissivo) é o identifier consumidor.
    """
    head, sep, resto = texto.partition(",")

    if sep and resto.strip():
        token = resto.strip()
        if leitor(token) is not None:
            return head.strip(), token

    # Sem vírgula (ou vírgula sem número parseável depois): verifica último(s) token(s)
    tokens = (head if sep else texto).split()
    if len(tokens) < 2:
        return None

    token = tokens[-1]
    if leitor(token) is None:
        return None

    penultimo = tokens[-2]
    prefixo = " ".join(tokens[:-2] if eh_so_marcador(penultimo) else tokens[:-1])
    if not prefixo:
        return None
    return prefixo, token


def separar_numero(texto: str) -> tuple[str, str] | None:
    """(logradouro, token bruto) ou None. Split pelo leitor permissivo (superconjunto).

    O token devolvido é BRUTO (str) — o identifier consumidor aplica seu próprio parser
    (estrito, exigindo int, ou o permissivo do endereço-lote).
    """
    limpo = texto.strip()
    if not COMECA_COM_LETRA.match(limpo):
        return None
    return _separar_token_numero(limpo, parse_numero_porta)


def separar_numero_codlog(texto: str) -> tuple[str, str] | None:
    """(codlog_txt, token bruto) ou None. Âncora em dígito e rejeição de ponto intactas.

    Obs.: a rejeição de ponto (formato de contribuinte) vale para a ENTRADA inteira,
    então "12345, s.n." fica fora deste caminho — "12345, s/n" e "12345, sn" funcionam.
    """
    limpo = texto.strip()
    if not limpo or not limpo[0].isdigit():
        return None
    if "." in limpo:
        return None
    return _separar_token_numero(limpo, parse_numero_porta)


def split_tipo_nome(texto: str) -> tuple[str, str]:
    """Quebra no 1º espaço: (tipo_logradouro, nome). Token único -> ('', nome). Sem normalizar."""
    partes = texto.strip().split(" ", 1)
    if len(partes) < 2:
        return "", (partes[0] if partes else "")
    return partes[0], partes[1]
