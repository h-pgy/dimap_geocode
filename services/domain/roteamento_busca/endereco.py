from .models import EnderecoParse, LogradouroParse
from .parsing import separar_numero, split_tipo_nome


class EnderecoIdentifier:
    def __call__(self, texto: str, finished_typing: bool) -> EnderecoParse | None:
        partes = separar_numero(texto)
        if partes is None:
            return None
        logradouro_txt, numero = partes
        tipo, nome = split_tipo_nome(logradouro_txt)
        return EnderecoParse(
            logradouro=LogradouroParse(
                tipo_logradouro=tipo,
                nome=nome,
                entrada_finalizada=finished_typing,
            ),
            numero=numero,
        )
