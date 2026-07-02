from services.domain.address_match import parse_numero_imovel

from .models import LogradouroParse
from .split_localizadores import COMECA_COM_LETRA, separar_numero, split_tipo_nome


class LogradouroIdentifier:
    def __call__(self, texto: str, finished_typing: bool) -> LogradouroParse | None:
        limpo = texto.strip()
        if not COMECA_COM_LETRA.match(limpo):
            return None
        # Guarda ESTRITA: o split (separar_numero) é permissivo, mas LOGRADOURO só é
        # suprimido quando o token parseia como número de imóvel (int) — preserva
        # LOGRADOURO em "Rua X, s/n" (o candidato ENDERECO_LOTE cobre esse caso).
        partes = separar_numero(limpo)
        if partes is not None and parse_numero_imovel(partes[1]) is not None:
            return None
        tipo, nome = split_tipo_nome(limpo.rstrip(","))
        if not tipo and not nome:
            return None
        return LogradouroParse(
            tipo_logradouro=tipo,
            nome=nome,
            entrada_finalizada=finished_typing,
        )
