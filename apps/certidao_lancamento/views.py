from collections.abc import Mapping
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from pydantic import BaseModel

from apps.competencias.protecao import acao_protegida, registrar_ato
from apps.user_admin.models import Perfil
from services.utils.erros_formulario import RecusaDeFormulario
from .acoes_declaradas import ACAO_EMITIR_CERTIDAO_LANCAMENTO
from .emissao import LoteLido, emitir_certidao_lancamento, ler_lote
from .formularios import ler_pedido_certidao

TEMPLATE_MODAL = "certidao_lancamento/modal.html"
TEMPLATE_CERTIDAO_EMITIDA = "certidao_lancamento/certidao_emitida.html"


class RecusaModal(BaseModel):
    campo: str
    mensagem: str


def _adaptar_recusa(recusa: RecusaDeFormulario | None) -> RecusaModal | None:
    if recusa is None:
        return None
    if recusa.campos:
        return RecusaModal(
            campo=recusa.campos[0].controle,
            mensagem=recusa.campos[0].mensagem,
        )
    if recusa.gerais:
        return RecusaModal(campo="", mensagem=recusa.gerais[0])
    return None


def certificavel(lote: LoteLido | None) -> bool:
    return lote is not None and lote.pode_certificar


def motivo_recusa(lote: LoteLido | None) -> str:
    if lote is None:
        return "O imóvel não foi localizado no cadastro oficial do GeoSampa."
    attrs = lote.feature.attributes
    if attrs.is_condominio:
        return "Lote condominial: a certidão ainda não é emitida pelo sistema."
    if not attrs.possui_lancamento:
        return "O lote não possui lançamento ativo no cadastro."
    return ""


def contexto_modal(
    lote: LoteLido | None,
    valores: Mapping[str, Any] | None = None,
    recusa: RecusaDeFormulario | None = None,
) -> dict[str, Any]:
    return {
        "lote": lote,
        "valores": valores or {},
        "recusa": _adaptar_recusa(recusa),
        "motivo_recusa_lote": motivo_recusa(lote),
    }


def _perfil(request: HttpRequest) -> Perfil:
    return request.user  # type: ignore[return-value]


@acao_protegida(ACAO_EMITIR_CERTIDAO_LANCAMENTO)
@require_GET
def modal(request: HttpRequest) -> HttpResponse:
    lote = ler_lote(request.GET.get("id", ""))
    return render(request, TEMPLATE_MODAL, contexto_modal(lote))


@acao_protegida(ACAO_EMITIR_CERTIDAO_LANCAMENTO)
@require_POST
def emitir(request: HttpRequest) -> HttpResponse:
    leitura = ler_pedido_certidao(request.POST)
    lote = ler_lote(request.POST.get("id", ""))
    if leitura.recusa is not None or not certificavel(lote):
        contexto = contexto_modal(lote, valores=request.POST, recusa=leitura.recusa)
        return render(request, TEMPLATE_MODAL, contexto, status=422)
    documento = emitir_certidao_lancamento(
        autor=_perfil(request),
        pedido=leitura.dto,  # type: ignore[arg-type]
        lote=lote,  # type: ignore[arg-type]
        base_url=request.build_absolute_uri("/"),
    )
    registrar_ato(
        request,
        operacao="emitir",
        alvo_tipo="documento",
        alvo_identificador=documento.codigo,
    )
    return render(request, TEMPLATE_CERTIDAO_EMITIDA, {"codigo": documento.codigo})
