from collections.abc import Callable, Iterable, Mapping
from functools import partial
from typing import Any, cast

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from pydantic import BaseModel, ConfigDict

from apps.competencias.protecao import acao_protegida, registrar_ato
from apps.user_admin.models import Perfil
from services.domain.certidao_lancamento import (
    SentidoDespacho,
    TipoDespacho,
    abertura_do_despacho,
    corpo_do_despacho,
    ressalva_padrao,
)
from services.utils.erros_formulario import RecusaDeFormulario
from .acoes_declaradas import ACAO_EMITIR_CERTIDAO_LANCAMENTO
from .emissao import LoteLido, emitir_certidao_lancamento, ler_lote
from .formularios import ler_pedido_certidao

TEMPLATE_MODAL = "certidao_lancamento/_modal.html"
TEMPLATE_CERTIDAO_EMITIDA = "certidao_lancamento/_certidao_emitida.html"

MOTIVO_LOTE_AUSENTE = "O imóvel não foi localizado no cadastro oficial do GeoSampa."
MOTIVO_CONDOMINIO = "Lote condominial: a certidão ainda não é emitida pelo sistema."
MOTIVO_SEM_LANCAMENTO = "O lote não possui lançamento ativo no cadastro."

VALORES_INICIAIS: dict[str, Any] = {
    "sentido": SentidoDespacho.DEFERIDO,
    "tipo_despacho": TipoDespacho.POSSUI_LANCAMENTO,
    "incluir_ressalva": True,
    "incluir_planta": True,
}


class OpcaoTipoDespacho(BaseModel):
    """Um cartão da lista: o valor que o formulário envia, o nome do tipo e o texto como sai no PDF."""

    model_config = ConfigDict(frozen=True)

    valor: TipoDespacho
    rotulo: str
    texto: str


class GrupoDeSentido(BaseModel):
    """Os textos de um sentido, sob a abertura que todos eles compartilham."""

    model_config = ConfigDict(frozen=True)

    sentido: SentidoDespacho
    abertura: str
    opcoes: tuple[OpcaoTipoDespacho, ...]


def motivos_recusa_lote(lote: LoteLido | None) -> tuple[str, ...]:
    """Tupla e não string: é o formato que a tarja de recusa lê, o mesmo de `recusa.mensagens`."""
    if lote is None:
        return (MOTIVO_LOTE_AUSENTE,)
    if lote.feature.attributes.is_condominio:
        return (MOTIVO_CONDOMINIO,)
    if not lote.feature.attributes.possui_lancamento:
        return (MOTIVO_SEM_LANCAMENTO,)
    return ()


def grupos_de_despacho(
    tipos: Iterable[TipoDespacho],
    corpo: Callable[[TipoDespacho], str],
) -> tuple[GrupoDeSentido, ...]:
    # O recorte e o texto descem como dado: o conjunto de lotes oferece outros tipos e o corpo no plural.
    oferecidos = tuple(tipos)
    return tuple(
        GrupoDeSentido(
            sentido=sentido,
            abertura=abertura_do_despacho(sentido),
            opcoes=tuple(
                OpcaoTipoDespacho(valor=tipo, rotulo=tipo.descricao, texto=corpo(tipo))
                for tipo in oferecidos
                if tipo.sentido is sentido
            ),
        )
        for sentido in SentidoDespacho
    )


def contexto_modal(
    lote: LoteLido | None,
    valores: Mapping[str, Any] | None = None,
    recusa: RecusaDeFormulario | None = None,
) -> dict[str, Any]:
    sql = lote.feature.attributes.sql if lote else None
    return {
        "lote": lote,
        # `is None`, e não `or`: o POST de uma recusa pode vir vazio, e vazio não é "abrir de novo".
        # Na recusa, checkbox desmarcado não vem no POST, e é por isso que ele volta desmarcado.
        "valores": VALORES_INICIAIS if valores is None else valores,
        "recusa": recusa,
        "motivos_recusa_lote": motivos_recusa_lote(lote),
        "grupos_despacho": grupos_de_despacho(TipoDespacho, partial(corpo_do_despacho, sql=sql)),
        "ressalva_padrao": ressalva_padrao(),
    }


def _perfil(request: HttpRequest) -> Perfil:
    # AUTH_USER_MODEL é Perfil: autenticado aqui É um Perfil — o decorator já barrou o anônimo.
    return cast(Perfil, request.user)


def _modal_recusado(
    request: HttpRequest,
    lote: LoteLido | None,
    valores: Mapping[str, Any],
    recusa: RecusaDeFormulario | None,
) -> HttpResponse:
    contexto = contexto_modal(lote, valores=valores, recusa=recusa)
    return render(request, TEMPLATE_MODAL, contexto, status=422)


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
    if leitura.dto is None or lote is None or not lote.pode_certificar:
        return _modal_recusado(request, lote, request.POST, leitura.recusa)
    desfecho = emitir_certidao_lancamento(
        autor=_perfil(request),
        pedido=leitura.dto,
        lote=lote,
        base_url=request.build_absolute_uri("/"),
    )
    if desfecho.documento is None:
        return _modal_recusado(request, lote, request.POST, desfecho.recusa)
    registrar_ato(
        request,
        operacao="emitir",
        alvo_tipo="documento",
        alvo_identificador=desfecho.documento.codigo,
    )
    return render(request, TEMPLATE_CERTIDAO_EMITIDA, {"codigo": desfecho.documento.codigo})
