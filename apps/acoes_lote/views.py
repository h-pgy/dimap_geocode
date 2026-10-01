from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from apps.competencias.resolucao import slugs_liberados
from .declaradas import ACOES_CONJUNTO, ACOES_LOTE
from .estrutura import PADRAO_SQL
from .resolucao import acoes_liberadas

TEMPLATE_POCO_ACOES = "acoes_lote/partials/_poco_acoes.html"
TEMPLATE_COLUNA_ACOES = "acoes_lote/partials/_coluna_acoes_conjunto.html"

ID_POCO_DO_LOTE = "poco-acoes-lote"


class ConsultaAcoesLote(BaseModel):
    """Enforcement: toda ação de lote exige o número de contribuinte (SQL) válido e o id do polígono."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    sql: str = Field(pattern=PADRAO_SQL)
    id: str = Field(pattern=r"^\d+$")


class ConsultaAcoesConjunto(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    chave: str = Field(min_length=1, max_length=64)


@require_GET
def acoes(request: HttpRequest) -> HttpResponse:
    try:
        consulta = ConsultaAcoesLote.model_validate(request.GET.dict())
    except ValidationError:
        return HttpResponse("")
    itens = acoes_liberadas(ACOES_LOTE, slugs_liberados(request.user))
    parametros = urlencode({"id": consulta.id, "sql": consulta.sql})
    contexto = {"itens": itens, "parametros": parametros, "id_poco": ID_POCO_DO_LOTE}
    return render(request, TEMPLATE_POCO_ACOES, contexto)


@require_GET
def acoes_conjunto(request: HttpRequest) -> HttpResponse:
    try:
        consulta = ConsultaAcoesConjunto.model_validate(request.GET.dict())
    except ValidationError:
        return HttpResponse("")
    itens = acoes_liberadas(ACOES_CONJUNTO, slugs_liberados(request.user))
    parametros = urlencode({"id": consulta.chave})
    # Sem item a coluna sai vazia, e a tabela fica com a largura toda.
    return render(request, TEMPLATE_COLUNA_ACOES, {"itens": itens, "parametros": parametros})
