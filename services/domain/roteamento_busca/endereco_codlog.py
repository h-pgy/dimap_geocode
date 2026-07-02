from services.domain.address_match import parse_numero_imovel

from .codlog import CodlogIdentifier
from .models import EnderecoCodlogParse
from .split_localizadores import separar_numero_codlog


class CodlogNumeroIdentifier:
    def __init__(self, codlog_identifier: CodlogIdentifier | None = None) -> None:
        self._codlog = codlog_identifier or CodlogIdentifier()

    def __call__(self, texto: str, finished_typing: bool) -> EnderecoCodlogParse | None:
        partes = separar_numero_codlog(texto)
        if partes is None:
            return None
        codlog_txt, token = partes
        numero = parse_numero_imovel(token)  # estrito: int ou None — MESMO parser de hoje
        if numero is None:
            return None
        codlog = self._codlog(codlog_txt, finished_typing)
        if codlog is None:
            return None
        return EnderecoCodlogParse(codlog=codlog, numero=numero, numero_bruto=token)
