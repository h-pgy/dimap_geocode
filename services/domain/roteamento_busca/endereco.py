from services.domain.address_match import parse_numero_imovel

from .models import EnderecoParse, LogradouroParse
from .split_localizadores import separar_numero, split_tipo_nome


class EnderecoIdentifier:
    def __call__(self, texto: str, finished_typing: bool) -> EnderecoParse | None:
        partes = separar_numero(texto)
        if partes is None:
            return None
        logradouro_txt, token = partes
        numero = parse_numero_imovel(token)  # estrito: int ou None — MESMO parser de hoje
        if numero is None:
            return None  # "s/n" não vira ENDERECO — só ENDERECO_LOTE
        tipo, nome = split_tipo_nome(logradouro_txt)
        return EnderecoParse(
            logradouro=LogradouroParse(
                tipo_logradouro=tipo, nome=nome, entrada_finalizada=finished_typing
            ),
            numero=numero,
            numero_bruto=token,
        )
