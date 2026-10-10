import hashlib
import hmac

from pydantic import SecretStr

from .constants import TAMANHO_TAG


def calcular_tag(pdf: bytes, segredo: SecretStr) -> str:
    # HMAC, e não `sha256(segredo + bytes)`: SHA-256 é Merkle–Damgård e o hash com prefixo secreto
    # admite extensão de mensagem sem conhecer o segredo.
    return hmac.new(
        segredo.get_secret_value().encode(),
        pdf,
        hashlib.sha256,
    ).hexdigest()


def localizar(pdf: bytes, agulha: str) -> int | None:
    """Onde estão, no arquivo, os 64 caracteres da marca — e `None` se não estiverem lá exatamente
    uma vez. Procurar os bytes, em vez de gravar o deslocamento: gravá-lo mudaria o arquivo e, com
    ele, o próprio deslocamento."""
    bytes_agulha = agulha.encode()
    if pdf.count(bytes_agulha) != 1:
        return None
    return pdf.find(bytes_agulha)


def localizar_unica(pdf: bytes, agulha: str) -> int:
    """A mesma busca para quem não pode seguir sem ela. A emissão trabalha sobre arquivo NOSSO,
    recém-gerado: zero ou duas ocorrências ali é defeito de emissão, e vira erro AQUI — não um selo
    que só deixa de conferir meses depois, na mão de quem recebeu o documento."""
    posicao = localizar(pdf, agulha)
    if posicao is None:
        ocorrencias = pdf.count(agulha.encode())
        raise ValueError(
            f"Esperava 1 ocorrência da marca do selo no arquivo, encontrei {ocorrencias}."
        )
    return posicao


def trocar(pdf: bytes, posicao: int, conteudo: str) -> bytes:
    return pdf[:posicao] + conteudo.encode() + pdf[posicao + TAMANHO_TAG :]
