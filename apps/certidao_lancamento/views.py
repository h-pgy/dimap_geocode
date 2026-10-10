from collections.abc import Callable, Iterable, Mapping
from functools import partial
from typing import Any, cast

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from pydantic import BaseModel, ConfigDict

from apps.competencias.protecao import acao_protegida, registrar_ato
from apps.lotes_mais_proximos.sessao import conjunto_vigente
from apps.user_admin.models import Perfil
from services.domain.certidao_lancamento import (
    SentidoDespacho,
    SugerirTipoDespacho,
    SugestaoDespachoInput,
    TipoDespacho,
    abertura_do_despacho,
    corpo_do_despacho,
    corpo_do_despacho_conjunto,
    ressalva_padrao,
)
from services.domain.geometry import para_geos
from services.domain.lote_geocod import LoteAttributes
from services.domain.lotes_mais_proximos import ConjuntoDeLotes
from services.utils.erros_formulario import RecusaDeFormulario
from .acoes_declaradas import ACAO_EMITIR_CERTIDAO_LANCAMENTO
from .emissao import (
    ConjuntoAlteradoError,
    LoteLido,
    conferir_confirmados,
    emitir_certidao_do_conjunto,
    emitir_certidao_lancamento,
    geometrias_metricas,
    ler_lote,
    reler_conjunto,
)
from .formularios import ler_pedido_certidao

LOTE_FRACAO_MINIMA_CONTIDA: float = settings.LOTE_FRACAO_MINIMA_CONTIDA
MAP_INTERPOLATION_CRS: int = settings.MAP_INTERPOLATION_CRS
MAP_OUTPUT_CRS: int = settings.MAP_OUTPUT_CRS

TEMPLATE_MODAL = "certidao_lancamento/_modal.html"
TEMPLATE_MODAL_CONJUNTO = "certidao_lancamento/partials/_modal_conjunto.html"
TEMPLATE_CONJUNTO_ALTERADO = "certidao_lancamento/partials/_conjunto_alterado.html"
TEMPLATE_CERTIDAO_EMITIDA = "certidao_lancamento/_certidao_emitida.html"

MOTIVO_LOTE_AUSENTE = "O imóvel não foi localizado no cadastro oficial do GeoSampa."
MOTIVO_CONDOMINIO = "Lote condominial: a certidão ainda não é emitida pelo sistema."
MOTIVO_SEM_LANCAMENTO = "O lote não possui lançamento ativo no cadastro."

MOTIVO_CONJUNTO_SUBSTITUIDO = (
    "Este resultado foi substituído por outra consulta ou já foi descartado. "
    "Refaça a consulta a partir do desenho."
)
MOTIVO_CONJUNTO_ESVAZIADO = "Todos os lotes foram tirados do conjunto."
MOTIVO_DESENHO_SEM_LOTE = "O polígono não cruza nenhum lote cadastrado."
MOTIVO_LOTE_TIRADO = "{lote} foi tirado da tabela depois que o modal abriu."
MOTIVO_LOTE_FORA_DA_CAMADA = "{lote} saiu da camada de lotes do GeoSampa."
MOTIVO_LOTE_NAO_CONFIRMADO = "{lote} está no conjunto, mas não constava da lista confirmada."
MOTIVO_LOTE_DE_FORA = "A lista enviada traz lote que não faz parte do conjunto consultado."

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


def valores_iniciais_do_conjunto(conjunto: ConjuntoDeLotes) -> dict[str, Any]:
    geometrias = geometrias_metricas(conjunto, MAP_OUTPUT_CRS, MAP_INTERPOLATION_CRS)
    sugerir_tipo = SugerirTipoDespacho()
    sugerido = sugerir_tipo(
        SugestaoDespachoInput(
            desenho=para_geos(geometrias.desenho, MAP_INTERPOLATION_CRS),
            lotes=tuple(para_geos(lote, MAP_INTERPOLATION_CRS) for lote in geometrias.lotes),
            fracao_minima_contida=LOTE_FRACAO_MINIMA_CONTIDA,
        )
    )
    return {**VALORES_INICIAIS, "tipo_despacho": sugerido}


def sqls_do_conjunto(conjunto: ConjuntoDeLotes | None) -> tuple[str, ...]:
    if conjunto is None:
        return ()
    return tuple(lote.attributes.sql or "" for lote in conjunto.lotes)


def grupos_de_despacho_do_conjunto(sqls: tuple[str, ...]) -> tuple[GrupoDeSentido, ...]:
    # Sem lotes o modal abre o aviso, sem formulário: não há rol para a prévia citar.
    if not sqls:
        return ()
    return grupos_de_despacho(TipoDespacho, partial(corpo_do_despacho_conjunto, sqls=sqls))


def _rotulo_do_lote(lote: LoteAttributes) -> str:
    sql = lote.sql or "sem contribuinte"
    endereco = lote.endereco or "endereço não informado"
    return f"{sql} · {endereco}"


def _motivo_do_impeditivo(lote: LoteAttributes) -> str:
    impedimento = "condominial" if lote.is_condominio else "sem lançamento ativo"
    return f"{_rotulo_do_lote(lote)} — {impedimento}"


def motivos_recusa_conjunto(conjunto: ConjuntoDeLotes | None) -> tuple[str, ...]:
    """Por que o conjunto não pode ser certificado: substituído, vazio ou com lotes impeditivos."""
    if conjunto is None:
        return (MOTIVO_CONJUNTO_SUBSTITUIDO,)
    if not conjunto.apurado.lotes:
        return (MOTIVO_DESENHO_SEM_LOTE,)
    if not conjunto.lotes:
        return (MOTIVO_CONJUNTO_ESVAZIADO,)
    return tuple(
        _motivo_do_impeditivo(lote.attributes)
        for lote in conjunto.lotes
        if lote.attributes.is_condominio or not lote.attributes.possui_lancamento
    )


def certificaveis(conjunto: ConjuntoDeLotes) -> bool:
    return not motivos_recusa_conjunto(conjunto)


def contexto_modal_conjunto(
    conjunto: ConjuntoDeLotes | None,
    chave: str,
    valores: Mapping[str, Any] | None = None,
    recusa: RecusaDeFormulario | None = None,
) -> dict[str, Any]:
    # A sugestão só existe com lotes: conjunto vazio ou substituído abre o aviso, sem formulário.
    if valores is None and conjunto is not None and conjunto.lotes:
        valores = valores_iniciais_do_conjunto(conjunto)
    return {
        "conjunto": conjunto,
        "chave": chave,
        "valores": valores or {},
        "recusa": recusa,
        "motivos_recusa_conjunto": motivos_recusa_conjunto(conjunto),
        "grupos_despacho": grupos_de_despacho_do_conjunto(sqls_do_conjunto(conjunto)),
        "ressalva_padrao": ressalva_padrao(),
    }


def contexto_conjunto_substituido() -> dict[str, Any]:
    return {"conjunto": None, "motivos": (MOTIVO_CONJUNTO_SUBSTITUIDO,)}


def _motivo_da_saida(conjunto: ConjuntoDeLotes, id_poligono: str) -> str:
    consultados = {lote.attributes.id_poligono: lote.attributes for lote in conjunto.apurado.lotes}
    lote = consultados.get(id_poligono)
    # Id que a consulta nunca apurou veio forjado: não se devolve o que o cliente mandou.
    if lote is None:
        return MOTIVO_LOTE_DE_FORA
    if id_poligono in conjunto.removidos:
        return MOTIVO_LOTE_TIRADO.format(lote=_rotulo_do_lote(lote))
    return MOTIVO_LOTE_FORA_DA_CAMADA.format(lote=_rotulo_do_lote(lote))


def contexto_conjunto_alterado(
    conjunto: ConjuntoDeLotes,
    erro: ConjuntoAlteradoError,
) -> dict[str, Any]:
    """`conjunto` é o da sessão: é ele que sabe o que a pessoa tirou e o que a camada deixou de ter."""
    sairam = tuple(_motivo_da_saida(conjunto, id_poligono) for id_poligono in sorted(erro.sairam))
    entraram = tuple(
        MOTIVO_LOTE_NAO_CONFIRMADO.format(lote=_rotulo_do_lote(lote.attributes))
        for lote in conjunto.lotes
        if lote.attributes.id_poligono in erro.entraram
    )
    # `dict.fromkeys`: vários ids forjados dão o mesmo motivo, e ele sai uma vez só.
    return {"conjunto": conjunto, "motivos": tuple(dict.fromkeys(sairam + entraram))}


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


@acao_protegida(ACAO_EMITIR_CERTIDAO_LANCAMENTO)
@require_GET
def modal_conjunto(request: HttpRequest) -> HttpResponse:
    # Abrir o modal é leitura: sai da sessão, sem GeoServer e sem linha no registro.
    chave = request.GET.get("id", "")
    conjunto = conjunto_vigente(request.session, chave)
    return render(request, TEMPLATE_MODAL_CONJUNTO, contexto_modal_conjunto(conjunto, chave))


@acao_protegida(ACAO_EMITIR_CERTIDAO_LANCAMENTO)
@require_POST
def emitir_conjunto(request: HttpRequest) -> HttpResponse:
    leitura = ler_pedido_certidao(request.POST)
    chave = request.POST.get("chave", "")
    conjunto = conjunto_vigente(request.session, chave)
    if conjunto is None:
        return render(request, TEMPLATE_CONJUNTO_ALTERADO, contexto_conjunto_substituido(), status=409)
    if leitura.dto is None:
        contexto = contexto_modal_conjunto(conjunto, chave, valores=request.POST, recusa=leitura.recusa)
        return render(request, TEMPLATE_MODAL_CONJUNTO, contexto, status=422)
    lido = reler_conjunto(conjunto)
    try:
        conferir_confirmados(lido, frozenset(request.POST.getlist("confirmados")))
    except ConjuntoAlteradoError as erro:
        contexto = contexto_conjunto_alterado(conjunto, erro)
        return render(request, TEMPLATE_CONJUNTO_ALTERADO, contexto, status=409)
    if not certificaveis(lido.conjunto):
        # O lançamento pode ter caído depois do modal: o aviso volta com os dados relidos.
        contexto = contexto_modal_conjunto(lido.conjunto, chave)
        return render(request, TEMPLATE_MODAL_CONJUNTO, contexto, status=422)
    desfecho = emitir_certidao_do_conjunto(
        autor=_perfil(request),
        pedido=leitura.dto,
        lido=lido,
        base_url=request.build_absolute_uri("/"),
    )
    if desfecho.documento is None:
        contexto = contexto_modal_conjunto(conjunto, chave, valores=request.POST, recusa=desfecho.recusa)
        return render(request, TEMPLATE_MODAL_CONJUNTO, contexto, status=422)
    registrar_ato(
        request,
        operacao="emitir_conjunto",
        alvo_tipo="documento",
        alvo_identificador=desfecho.documento.codigo,
    )
    return render(request, TEMPLATE_CERTIDAO_EMITIDA, {"codigo": desfecho.documento.codigo})
