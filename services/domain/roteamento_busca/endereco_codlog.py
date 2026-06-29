from .codlog import CodlogIdentifier
from .models import EnderecoCodlogParse
from .parsing import separar_numero_codlog


class CodlogNumeroIdentifier:
    def __init__(self, codlog_identifier: CodlogIdentifier | None = None) -> None:
        self._codlog = codlog_identifier or CodlogIdentifier()

    def __call__(self, texto: str, finished_typing: bool) -> EnderecoCodlogParse | None:
        partes = separar_numero_codlog(texto)
        if partes is None:
            return None
        codlog_txt, numero = partes
        codlog = self._codlog(codlog_txt, finished_typing)
        if codlog is None:
            return None
        return EnderecoCodlogParse(codlog=codlog, numero=numero)
