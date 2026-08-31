"""A tela de atribuições da unidade (SPEC autorizacao/007) e a de conceder competência (SPEC
autorizacao/008): a competência responde pela unidade em que o perfil exerce a estrutural, o
alcance por sobre qual unidade ele pode incidir — as duas conferências vivem no decorator, e
nenhuma view repete qualquer uma delas. Exceção: a atribuição-alvo da 008, que o decorator não
tem como conhecer (Caveats da SPEC 008) — só ela é conferida aqui dentro."""

from typing import cast

from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.competencias.acoes_declaradas import ACAO_CONCEDER, ACAO_DEFINIR_ATRIBUICAO
from apps.competencias.atribuicao import atribuir as atribuir_acao
from apps.competencias.atribuicao import remover as remover_acao
from apps.competencias.comandos import ComandoAtribuicao, ComandoConcessao, ComandoRevogacao
from apps.competencias.concessao import conceder as conceder_cargo_dominio
from apps.competencias.concessao import identificador_cargo
from apps.competencias.concessao import revogar as revogar_concessao
from apps.competencias.consulta import alcance_do_perfil, dirige
from apps.competencias.context import (
    contexto_catalogo,
    contexto_confirmar_remocao,
    contexto_da_tela,
    contexto_da_tela_conceder,
    contexto_modal_conceder,
    contexto_modal_delegar,
    contexto_painel,
    contexto_painel_concessoes,
    contexto_poco,
    contexto_poco_concessoes,
)
from apps.competencias.delegacao import delegar_competencia, encerrar_delegacao
from apps.competencias.formularios import ler_nova_delegacao
from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao, Delegacao
from apps.competencias.protecao import acao_protegida, registrar_ato
from apps.unidades.models import Unidade
from apps.user_admin.models import Perfil
from services.utils.erros_formulario import RecusaDeFormulario

TEMPLATE_TELA = "competencias/definir_atribuicao.html"
TEMPLATE_PAINEL = "competencias/partials/_painel_atribuicoes.html"
TEMPLATE_CATALOGO = "competencias/partials/_modal_catalogo.html"
TEMPLATE_POCO = "competencias/partials/_poco_atribuicoes.html"
TEMPLATE_MODAL_REMOVER = "competencias/partials/_modal_remover.html"
TEMPLATE_TELA_CONCEDER = "competencias/conceder_competencia.html"
TEMPLATE_PAINEL_CONCESSOES = "competencias/partials/_painel_concessoes.html"
TEMPLATE_MODAL_CONCEDER = "competencias/partials/_modal_conceder.html"
TEMPLATE_MODAL_DELEGAR = "competencias/partials/_modal_delegar.html"
TEMPLATE_POCO_CONCESSOES = "competencias/partials/_poco_concessoes.html"


@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
def definir_atribuicao(request: HttpRequest) -> HttpResponse:
    # Nenhuma conferência de alcance escrita aqui: o POST forjado com unidade de outro ramo já foi
    # recusado pelo decorator, que leu o alcance do contrato da ação.
    return render(request, TEMPLATE_TELA, contexto_da_tela(_perfil(request)))


@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
def painel_atribuicoes(request: HttpRequest) -> HttpResponse:
    """Alvo do hx-get ao trocar de unidade na árvore — a árvore em si não é reenviada.
    `fechar_modal=True`: um modal aberto referia a unidade anterior."""
    return render(
        request,
        TEMPLATE_PAINEL,
        contexto_painel(_unidade_do_request(request), fechar_modal=True),
    )


@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
def catalogo(request: HttpRequest) -> HttpResponse:
    return render(request, TEMPLATE_CATALOGO, contexto_catalogo(_unidade_do_request(request)))


@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
@require_POST
def atribuir(request: HttpRequest) -> HttpResponse:
    # A unidade passa a ser LIDA, e não repassada como id cru (SPEC user_admin/025). `Unidade` sem
    # gerente nomeado resolve pelo `_default_manager` — as vigentes —, então a extinta vira 404 pelo
    # mesmo caminho que `remover` e `confirmar_remocao` já usavam.
    unidade = _unidade_do_request(request)
    comando = ComandoAtribuicao(
        unidade_alvo_id=unidade.pk,
        acao_slug=request.POST["acao"],
    )
    atribuicao = atribuir_acao(comando)
    # A view NUNCA grava a execução: deixa o recado e quem persiste é o decorator, depois do return.
    registrar_ato(
        request,
        operacao="atribuir",
        alvo_tipo="unidade_acao",
        alvo_identificador=f"{atribuicao.unidade.sigla}:{atribuicao.acao.slug}",
    )
    return render(
        request, TEMPLATE_POCO, contexto_poco(atribuicao.unidade, fechar_modal=True)
    )


@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
def confirmar_remocao(request: HttpRequest) -> HttpResponse:
    """GET: monta o modal com a contagem real. Não apaga — e é por não existir aqui nenhuma escrita
    que a confirmação é obrigatória, sem flag nenhuma no formulário."""
    comando = ComandoAtribuicao(
        unidade_alvo_id=_unidade_do_request(request).pk,
        acao_slug=request.GET["acao"],
    )
    return render(request, TEMPLATE_MODAL_REMOVER, contexto_confirmar_remocao(comando))


@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
@require_POST
def remover(request: HttpRequest) -> HttpResponse:
    comando = ComandoAtribuicao(
        unidade_alvo_id=request.POST["unidade"],  # type: ignore[arg-type]
        acao_slug=request.POST["acao"],
    )
    unidade = get_object_or_404(Unidade, pk=comando.unidade_alvo_id)
    acao = get_object_or_404(Acao, slug=comando.acao_slug)
    remover_acao(comando)
    registrar_ato(
        request,
        operacao="remover",
        alvo_tipo="unidade_acao",
        alvo_identificador=f"{unidade.sigla}:{acao.slug}",
    )
    return render(request, TEMPLATE_POCO, contexto_poco(unidade, fechar_modal=True))


@acao_protegida(ACAO_CONCEDER)
def conceder(request: HttpRequest) -> HttpResponse:
    return render(request, TEMPLATE_TELA_CONCEDER, contexto_da_tela_conceder(_perfil(request)))


@acao_protegida(ACAO_CONCEDER)
def painel_concessoes(request: HttpRequest) -> HttpResponse:
    """Alvo do hx-get ao trocar de unidade na árvore — a árvore em si não é reenviada.
    `fechar_modal=True`: um modal aberto referia a atribuição da unidade anterior."""
    return render(
        request,
        TEMPLATE_PAINEL_CONCESSOES,
        contexto_painel_concessoes(
            _unidade_do_request(request), _perfil(request), fechar_modal=True
        ),
    )


@acao_protegida(ACAO_CONCEDER)
def modal_conceder(request: HttpRequest) -> HttpResponse:
    atribuicao = get_object_or_404(AtribuicaoUnidade, pk=request.GET.get("atribuicao"))
    return render(request, TEMPLATE_MODAL_CONCEDER, contexto_modal_conceder(atribuicao))


@acao_protegida(ACAO_CONCEDER)
def modal_delegar(request: HttpRequest) -> HttpResponse:
    atribuicao = get_object_or_404(AtribuicaoUnidade, pk=request.GET.get("atribuicao"))
    _exigir_direcao_para_delegar(atribuicao.unidade, _perfil(request))
    return render(
        request,
        TEMPLATE_MODAL_DELEGAR,
        contexto_modal_delegar(atribuicao, _perfil(request)),
    )


@acao_protegida(ACAO_CONCEDER)
@require_POST
def conceder_cargo(request: HttpRequest) -> HttpResponse:
    comando = ComandoConcessao(
        unidade_alvo_id=request.POST["unidade"],  # type: ignore[arg-type]
        atribuicao_id=request.POST["atribuicao"],  # type: ignore[arg-type]
        cargo_base_id=request.POST.get("cargo_base") or None,  # type: ignore[arg-type]
        cargo_comissao_id=request.POST.get("cargo_comissao") or None,  # type: ignore[arg-type]
    )
    # A atribuição é entidade desta ação, e o decorator só confere a UNIDADE do alcance: sem esta
    # barreira, um id de atribuição de outro ramo passaria pela primeira conferência sem esbarrar
    # em nada (SPEC autorizacao/008, Caveats).
    atribuicao = _atribuicao_no_alvo(comando.atribuicao_id, comando.unidade_alvo_id)
    concessao = conceder_cargo_dominio(comando, concedida_por_id=_perfil(request).pk)
    registrar_ato(
        request,
        operacao="conceder",
        alvo_tipo="acao_cargo",
        alvo_identificador=f"{atribuicao.acao.slug}:{identificador_cargo(concessao)}",
    )
    return render(
        request,
        TEMPLATE_POCO_CONCESSOES,
        contexto_poco_concessoes(atribuicao.unidade, _perfil(request), fechar_modal=True),
    )


@acao_protegida(ACAO_CONCEDER)
@require_POST
def revogar_cargo(request: HttpRequest) -> HttpResponse:
    comando = ComandoRevogacao(
        unidade_alvo_id=request.POST["unidade"],  # type: ignore[arg-type]
        concessao_id=request.POST["concessao"],  # type: ignore[arg-type]
    )
    concessao = _concessao_no_alvo(comando.concessao_id, comando.unidade_alvo_id)
    unidade = concessao.atribuicao.unidade
    identificador = f"{concessao.atribuicao.acao.slug}:{identificador_cargo(concessao)}"
    revogar_concessao(comando)
    registrar_ato(
        request, operacao="revogar", alvo_tipo="acao_cargo", alvo_identificador=identificador
    )
    return render(
        request,
        TEMPLATE_POCO_CONCESSOES,
        contexto_poco_concessoes(unidade, _perfil(request), fechar_modal=True),
    )


@acao_protegida(ACAO_CONCEDER)
@require_POST
def delegar_servidor(request: HttpRequest) -> HttpResponse:
    unidade_id = int(request.POST["unidade"])
    atribuicao_id = int(request.POST["atribuicao"])
    atribuicao = _atribuicao_no_alvo(atribuicao_id, unidade_id)
    _exigir_direcao_para_delegar(atribuicao.unidade, _perfil(request))

    leitura = ler_nova_delegacao(request.POST)
    alcance = alcance_do_perfil(_perfil(request))
    if leitura.dto is None:
        return _delegacao_recusada(request, atribuicao, leitura.recusa or RecusaDeFormulario())

    desfecho = delegar_competencia(atribuicao, leitura.dto, _perfil(request), alcance)
    if desfecho.delegacao is None:
        return _delegacao_recusada(request, atribuicao, desfecho.recusa)

    registrar_ato(
        request,
        operacao="delegar",
        alvo_tipo="acao_servidor",
        alvo_identificador=f"{atribuicao.acao.slug}:{desfecho.delegacao.delegado.rf}",
    )
    return render(
        request,
        TEMPLATE_POCO_CONCESSOES,
        contexto_poco_concessoes(atribuicao.unidade, _perfil(request), fechar_modal=True),
    )


@acao_protegida(ACAO_CONCEDER)
@require_POST
def revogar_delegacao(request: HttpRequest) -> HttpResponse:
    unidade_id = int(request.POST["unidade"])
    delegacao_id = int(request.POST["delegacao"])
    delegacao = get_object_or_404(
        Delegacao.objects.select_related("acao", "unidade", "delegado"), pk=delegacao_id
    )
    if delegacao.unidade_id != unidade_id:
        raise PermissionDenied
    _exigir_direcao_para_delegar(delegacao.unidade, _perfil(request))

    encerrar_delegacao(delegacao)
    registrar_ato(
        request,
        operacao="revogar",
        alvo_tipo="acao_servidor",
        alvo_identificador=f"{delegacao.acao.slug}:{delegacao.delegado.rf}",
    )
    return render(
        request,
        TEMPLATE_POCO_CONCESSOES,
        contexto_poco_concessoes(delegacao.unidade, _perfil(request), fechar_modal=True),
    )


def _exigir_direcao_para_delegar(unidade: Unidade, perfil: Perfil) -> None:
    if not (perfil.is_superuser or dirige(perfil, unidade)):
        raise PermissionDenied


def _delegacao_recusada(
    request: HttpRequest,
    atribuicao: AtribuicaoUnidade,
    recusa: RecusaDeFormulario,
) -> HttpResponse:
    return render(
        request,
        TEMPLATE_MODAL_DELEGAR,
        contexto_modal_delegar(
            atribuicao,
            _perfil(request),
            valores=request.POST.dict(),
            recusa=recusa,
        ),
        status=422,
    )


def _perfil(request: HttpRequest) -> Perfil:
    # AUTH_USER_MODEL é Perfil: autenticado aqui É um Perfil — o decorator já barrou o anônimo.
    return cast(Perfil, request.user)


def _unidade_do_request(request: HttpRequest) -> Unidade:
    # POST antes de GET, como a conferência do decorator (protecao.py): a mesma leitura, duas vezes.
    id_bruto = request.POST.get("unidade") or request.GET.get("unidade")
    return get_object_or_404(Unidade, pk=id_bruto)


def _atribuicao_no_alvo(atribuicao_id: int, unidade_alvo_id: int) -> AtribuicaoUnidade:
    atribuicao = get_object_or_404(
        AtribuicaoUnidade.objects.select_related("acao", "unidade"), pk=atribuicao_id
    )
    if atribuicao.unidade_id != unidade_alvo_id:
        raise PermissionDenied
    # O segundo nível, na mesma porta em que o alvo já é conferido (SPEC user_admin/025).
    # Atribuição extinta não recebe concessão — revogar continua livre, porque tirar não recria
    # nada.
    if atribuicao.extinta_em is not None:
        raise Http404
    return atribuicao


def _concessao_no_alvo(concessao_id: int, unidade_alvo_id: int) -> Concessao:
    concessao = get_object_or_404(
        Concessao.objects.select_related(
            "atribuicao__acao", "atribuicao__unidade", "cargo_base", "cargo_comissao"
        ),
        pk=concessao_id,
    )
    if concessao.atribuicao.unidade_id != unidade_alvo_id:
        raise PermissionDenied
    return concessao
