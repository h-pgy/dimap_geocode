from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from apps.competencias.resolucao import slugs_liberados
from .estrutura import PADRAO_SQL
from .resolucao import acoes_liberadas

TEMPLATE_POCO_ACOES = "acoes_lote/partials/_poco_acoes.html"


class ConsultaAcoesLote(BaseModel):
    """Enforcement: toda ação de lote exige o número de contribuinte (SQL) válido e o id do polígono."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    sql: str = Field(pattern=PADRAO_SQL)
    id: str = Field(pattern=r"^\d+$")


@require_GET
def acoes(request: HttpRequest) -> HttpResponse:
    try:
        consulta = ConsultaAcoesLote.model_validate(request.GET.dict())
    except ValidationError:
        return HttpResponse("")
    itens = acoes_liberadas(slugs_liberados(request.user))
    return render(
        request,
        TEMPLATE_POCO_ACOES,
        {"itens": itens, "id_entidade": consulta.id, "sql": consulta.sql},
    )
