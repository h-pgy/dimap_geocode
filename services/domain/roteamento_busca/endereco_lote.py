from services.domain.address_match import parse_numero_porta

from .codlog import CodlogIdentifier
from .models import EnderecoLoteParse, LogradouroParse
from .split_localizadores import separar_numero, separar_numero_codlog, split_tipo_nome


class EnderecoLoteIdentifier:
    """Emite ENDERECO_LOTE para entrada com cara de endereço, nas duas formas (nome/codlog)."""

    def __init__(self, codlog_identifier: CodlogIdentifier | None = None) -> None:
        self._codlog = codlog_identifier or CodlogIdentifier()

    def __call__(self, texto: str, finished_typing: bool) -> EnderecoLoteParse | None:
        return self._pipeline(texto, finished_typing)

    def _pipeline(self, texto: str, finished_typing: bool) -> EnderecoLoteParse | None:
        # exatamente uma das formas produz parse (o model_validator garante a exclusividade)
        return self._por_codlog(texto, finished_typing) or self._por_nome(texto, finished_typing)

    def _por_nome(self, texto: str, finished_typing: bool) -> EnderecoLoteParse | None:
        partes = separar_numero(texto)
        if partes is None:
            return None
        logradouro_txt, token = partes
        numero_bruto = parse_numero_porta(token)
        if numero_bruto is None:
            return None
        tipo, nome = split_tipo_nome(logradouro_txt)
        return EnderecoLoteParse(
            logradouro=LogradouroParse(
                tipo_logradouro=tipo, nome=nome, entrada_finalizada=finished_typing
            ),
            numero_bruto=numero_bruto,
        )

    def _por_codlog(self, texto: str, finished_typing: bool) -> EnderecoLoteParse | None:
        partes = separar_numero_codlog(texto)
        if partes is None:
            return None
        codlog_txt, token = partes
        numero_bruto = parse_numero_porta(token)
        if numero_bruto is None:
            return None
        codlog = self._codlog(codlog_txt, finished_typing)
        if codlog is None:
            return None
        return EnderecoLoteParse(codlog=codlog, numero_bruto=numero_bruto)
