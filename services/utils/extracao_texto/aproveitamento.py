from .erros import ExtracaoImpossivel
from .models import MINIMO_CARACTERES_UTEIS, OrigemTexto, TextoExtraido

MENSAGEM_RECUSA = (
    "Só são aceitos documentos cujo texto possa ser extraído (inclusive por OCR)."
)


def tem_texto_util(texto: str) -> bool:
    return sum(caractere.isalnum() for caractere in texto) >= MINIMO_CARACTERES_UTEIS


def texto_aproveitavel(texto: str, origem: OrigemTexto) -> TextoExtraido:
    if not tem_texto_util(texto):
        raise ExtracaoImpossivel(MENSAGEM_RECUSA)
    return TextoExtraido(conteudo=texto, origem=origem)
