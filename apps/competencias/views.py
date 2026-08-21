"""A tela de atribuições da unidade (SPEC autorizacao/007): a competência responde pela unidade em
que o perfil exerce a estrutural, o alcance por sobre qual unidade ele pode incidir — as duas
conferências vivem no decorator, e nenhuma view repete qualquer uma delas."""

from typing import cast

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.competencias.acoes_declaradas import ACAO_DEFINIR_ATRIBUICAO
from apps.competencias.atribuicao import atribuir as atribuir_acao
from apps.competencias.atribuicao import remover as remover_acao
from apps.competencias.comandos import ComandoAtribuicao
from apps.competencias.context import (
    contexto_catalogo,
    contexto_confirmar_remocao,
    contexto_da_tela,
    contexto_painel,
    contexto_poco,
)
from apps.competencias.models import Acao
from apps.competencias.protecao import acao_protegida, registrar_ato
from apps.user_admin.models import Perfil, Unidade

TEMPLATE_TELA = "competencias/definir_atribuicao.html"
TEMPLATE_PAINEL = "competencias/partials/_painel_atribuicoes.html"
TEMPLATE_CATALOGO = "competencias/partials/_modal_catalogo.html"
TEMPLATE_POCO = "competencias/partials/_poco_atribuicoes.html"
TEMPLATE_MODAL_REMOVER = "competencias/partials/_modal_remover.html"


@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
def definir_atribuicao(request: HttpRequest) -> HttpResponse:
    # Nenhuma conferência de alcance escrita aqui: o POST forjado com unidade de outro ramo já foi
    # recusado pelo decorator, que leu o alcance do contrato da ação.
    return render(request, TEMPLATE_TELA, contexto_da_tela(_perfil(request)))


@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
def painel_atribuicoes(request: HttpRequest) -> HttpResponse:
    """Alvo do hx-get ao trocar de unidade na árvore — a árvore em si não é reenviada."""
    return render(request, TEMPLATE_PAINEL, contexto_painel(_unidade_do_request(request)))


@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
def catalogo(request: HttpRequest) -> HttpResponse:
    return render(request, TEMPLATE_CATALOGO, contexto_catalogo(_unidade_do_request(request)))


@acao_protegida(ACAO_DEFINIR_ATRIBUICAO)
@require_POST
def atribuir(request: HttpRequest) -> HttpResponse:
    comando = ComandoAtribuicao(
        unidade_alvo_id=request.POST["unidade"],  # type: ignore[arg-type]
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
    return render(request, TEMPLATE_POCO, contexto_poco(atribuicao.unidade))


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
    return render(request, TEMPLATE_POCO, contexto_poco(unidade))


def _perfil(request: HttpRequest) -> Perfil:
    # AUTH_USER_MODEL é Perfil: autenticado aqui É um Perfil — o decorator já barrou o anônimo.
    return cast(Perfil, request.user)


def _unidade_do_request(request: HttpRequest) -> Unidade:
    # POST antes de GET, como a conferência do decorator (protecao.py): a mesma leitura, duas vezes.
    id_bruto = request.POST.get("unidade") or request.GET.get("unidade")
    return get_object_or_404(Unidade, pk=id_bruto)
