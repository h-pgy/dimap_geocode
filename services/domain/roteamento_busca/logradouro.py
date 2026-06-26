from .models import LogradouroParse
from .parsing import COMECA_COM_LETRA, separar_numero, split_tipo_nome


class LogradouroIdentifier:
    def __call__(self, texto: str, finished_typing: bool) -> LogradouroParse | None:
        limpo = texto.strip()
        if not COMECA_COM_LETRA.match(limpo):
            return None
        if separar_numero(limpo) is not None:
            return None
        tipo, nome = split_tipo_nome(limpo.rstrip(","))
        if not tipo and not nome:
            return None
        return LogradouroParse(
            tipo_logradouro=tipo,
            nome=nome,
            entrada_finalizada=finished_typing,
        )
