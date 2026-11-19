from django.db.models import Count
from django.db.models.functions import Lower
from pydantic import BaseModel

from apps.faq.models import PalavraChave as PalavraChaveModel
from services.domain.faq import PROFUNDIDADE_PALAVRA_CHAVE

SEPARADOR_CAMINHO = " › "
ROTULO_RAIZES = "Palavras-chave"


class OpcaoPalavraChave(BaseModel):
    pk: int
    nome: str
    marcada: bool
    tem_filhas: bool


class ColunaArvore(BaseModel):
    """Uma coluna da árvore horizontal: as filhas de `pai_id`, no `nivel` (0 = raízes)."""

    nivel: int
    pai_id: int | None
    caminho: str
    opcoes: list[OpcaoPalavraChave]
    aberta_id: int | None = None


class PalavraMarcada(BaseModel):
    pk: int
    caminho: str


def coluna_de_palavras_chave(
    pai_id: int | None, marcadas: set[int]
) -> list[OpcaoPalavraChave]:
    # As marcadas entram para o checkbox de cada filha já nascer no estado certo.
    filhas = PalavraChaveModel.objects.filter(pai_id=pai_id).annotate(
        qtd_filhas=Count("filhas")
    )
    return [
        OpcaoPalavraChave(
            pk=f.pk,
            nome=f.nome,
            marcada=f.pk in marcadas,
            tem_filhas=f.qtd_filhas > 0,
        )
        for f in filhas.order_by(Lower("nome"))
    ]


def colunas_ate(pai_id: int | None, marcadas: set[int]) -> list[ColunaArvore]:
    """As colunas do ramo aberto até as filhas de `pai_id`: cada uma com o seu escolhido marcado."""
    ramo = ancestrais(pai_id)
    pais: list[PalavraChaveModel | None] = [None, *ramo]
    colunas = []
    for nivel, pai in enumerate(pais[:PROFUNDIDADE_PALAVRA_CHAVE]):
        aberta = pais[nivel + 1] if nivel + 1 < len(pais) else None
        colunas.append(
            ColunaArvore(
                nivel=nivel,
                pai_id=pai.pk if pai is not None else None,
                caminho=caminho_de(pai) if pai is not None else ROTULO_RAIZES,
                opcoes=coluna_de_palavras_chave(
                    pai.pk if pai is not None else None, marcadas
                ),
                aberta_id=aberta.pk if aberta is not None else None,
            ),
        )
    return colunas


def ancestrais(palavra_id: int | None) -> list[PalavraChaveModel]:
    """Da raiz até a própria palavra, inclusive."""
    if palavra_id is None:
        return []
    palavra = (
        PalavraChaveModel.objects.select_related("pai__pai")
        .filter(pk=palavra_id)
        .first()
    )
    ramo: list[PalavraChaveModel] = []
    while palavra is not None:
        ramo.insert(0, palavra)
        palavra = palavra.pai
    return ramo


def caminho_de(palavra: PalavraChaveModel) -> str:
    nomes: list[str] = []
    atual: PalavraChaveModel | None = palavra
    while atual is not None:
        nomes.insert(0, atual.nome)
        atual = atual.pai
    return SEPARADOR_CAMINHO.join(nomes)


def marcadas_do_formulario(ids: set[int]) -> list[PalavraMarcada]:
    registros = PalavraChaveModel.objects.filter(pk__in=ids).select_related("pai__pai")
    marcadas = [PalavraMarcada(pk=r.pk, caminho=caminho_de(r)) for r in registros]
    return sorted(marcadas, key=lambda m: m.caminho.casefold())


def opcoes_de_pai() -> list[tuple[int, str]]:
    """As palavras que ainda aceitam filha: as dos dois primeiros níveis."""
    registros = PalavraChaveModel.objects.select_related("pai__pai")
    opcoes = [
        (r.pk, caminho_de(r)) for r in registros if r.pai is None or r.pai.pai is None
    ]
    return sorted(opcoes, key=lambda opcao: opcao[1].casefold())


def opcoes_de_palavra() -> list[tuple[int, str]]:
    registros = PalavraChaveModel.objects.select_related("pai__pai")
    return sorted(
        ((r.pk, caminho_de(r)) for r in registros),
        key=lambda opcao: opcao[1].casefold(),
    )
