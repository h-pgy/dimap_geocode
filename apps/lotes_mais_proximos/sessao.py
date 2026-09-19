from django.contrib.sessions.backends.base import SessionBase
from pydantic import BaseModel

from services.domain.lotes_mais_proximos import ConjuntoDeLotes

CHAVE_SESSAO = "lotes_mais_proximos.conjunto"


class ConjuntoNaSessao(BaseModel):
    chave: str  # uuid4().hex, gerado a cada consulta
    conjunto: ConjuntoDeLotes


def guardar_conjunto(sessao: SessionBase, guardado: ConjuntoNaSessao) -> None:
    sessao[CHAVE_SESSAO] = guardado.model_dump(mode="json")


def conjunto_vigente(sessao: SessionBase, chave: str) -> ConjuntoDeLotes | None:
    bruto = sessao.get(CHAVE_SESSAO)
    if bruto is None:
        return None
    guardado = ConjuntoNaSessao.model_validate(bruto)
    return guardado.conjunto if guardado.chave == chave else None


def descartar_conjunto(sessao: SessionBase, chave: str) -> None:
    # Só o vigente sai: fechar a gaveta de uma aba antiga não apaga o conjunto da aba nova.
    if conjunto_vigente(sessao, chave) is not None:
        del sessao[CHAVE_SESSAO]
