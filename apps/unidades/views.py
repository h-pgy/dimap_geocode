"""
Páginas de unidade: o formulário de cadastro (SPEC user_admin/012), a página própria
(SPEC user_admin/016), o organograma (SPEC user_admin/018) e os três atos que mantêm o organograma
(SPEC user_admin/020) — criar, editar e criar raiz.

As rotas de LEITURA seguem ABERTAS (exceção declarada nas SPECs 016 e 018, §3.5); as de ESCRITA e
as duas de abertura de formulário de ato (`criar_unidade`, `criar_unidade_raiz`, `editar_unidade`)
são protegidas.
"""

from typing import cast

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.competencias.consulta import alcance_do_perfil
from apps.competencias.protecao import acao_protegida, pode_executar, registrar_ato
from apps.unidades.acoes_declaradas import (
    ACAO_CRIAR_UNIDADE,
    ACAO_CRIAR_UNIDADE_RAIZ,
    ACAO_EDITAR_UNIDADE,
)
from apps.unidades.cadastro import alterar_unidade, cadastrar_unidade
from apps.unidades.context import (
    contexto_cor_sugerida,
    contexto_criacao_recusada,
    contexto_criar_unidade,
    contexto_edicao_recusada,
    contexto_modal_unidade,
    contexto_organograma,
    contexto_unidade,
    contexto_unidade_selecionada,
)
from apps.unidades.models import Unidade
from apps.unidades.schemas import SelecaoUnidadePai
from apps.user_admin.models import Perfil

TEMPLATE_UNIDADE = "unidades/unidade_form.html"
TEMPLATE_UNIDADE_FORM = "unidades/partials/_formulario_unidade.html"
TEMPLATE_UNIDADE_CRIADA = "unidades/partials/_unidade_criada.html"
TEMPLATE_CAMPOS_UNIDADE = "unidades/partials/_campos_unidade.html"
TEMPLATE_UNIDADE_SELECIONADA = "unidades/partials/_unidade_criada_e_selecionada.html"
TEMPLATE_MODAL_UNIDADE = "unidades/partials/_modal_editar_unidade.html"
TEMPLATE_EDICAO_CONCLUIDA = "unidades/partials/_edicao_unidade_concluida.html"
TEMPLATE_PAGINA_UNIDADE = "unidades/unidade.html"
TEMPLATE_CAMPO_COR = "unidades/partials/_campo_cor_unidade.html"
TEMPLATE_ARVORE = "unidades/arvore_unidades.html"


@acao_protegida(ACAO_CRIAR_UNIDADE)
def criar_unidade(request: HttpRequest) -> HttpResponse:
    # Oferecer o que o decorator vai recusar no POST é convidar ao 403: a lista de unidades
    # superiores sai do mesmo alcance que a barreira confere.
    autor = _autor(request)
    return render(request, TEMPLATE_UNIDADE, contexto_criar_unidade(alcance_do_perfil(autor)))


@acao_protegida(ACAO_CRIAR_UNIDADE_RAIZ)
def criar_unidade_raiz(request: HttpRequest) -> HttpResponse:
    """A mesma tela, com o campo de unidade superior gravado. Sem recorte de alcance: só o
    superusuário chega aqui, e ele alcança tudo."""
    return render(request, TEMPLATE_UNIDADE, contexto_criar_unidade(raiz=True))


@acao_protegida(ACAO_CRIAR_UNIDADE_RAIZ)
@require_POST
def gravar_unidade_raiz(request: HttpRequest) -> HttpResponse:
    # `pai_id` imposto, não lido: o campo vem `disabled` e não posta nada, mas quem define o que
    # esta porta faz é a rota — POST forjado com `pai` não vira criação comum numa ação sem alcance.
    valores = dict(_valores_da_unidade(request)) | {"pai_id": None}
    desfecho = cadastrar_unidade(valores, raiz_permitida=True)
    if desfecho.unidade is None:
        return render(
            request,
            TEMPLATE_UNIDADE_FORM,
            contexto_criacao_recusada(valores, desfecho.recusa, raiz=True),
            status=422,
        )
    # Operação própria: no histórico, criar uma raiz não se confunde com criar uma subordinada.
    registrar_ato(
        request,
        operacao="criar_raiz",
        alvo_tipo="unidade",
        alvo_identificador=desfecho.unidade.sigla,
    )
    return render(request, TEMPLATE_UNIDADE_CRIADA, {"unidade": desfecho.unidade})


@acao_protegida(ACAO_CRIAR_UNIDADE)
@require_POST
def gravar_unidade(request: HttpRequest) -> HttpResponse:
    autor = _autor(request)
    valores = _valores_da_unidade(request)
    desfecho = cadastrar_unidade(valores, raiz_permitida=autor.is_superuser)
    if desfecho.unidade is None:
        return render(
            request,
            TEMPLATE_UNIDADE_FORM,
            contexto_criacao_recusada(valores, desfecho.recusa, alcance_do_perfil(autor)),
            status=422,
        )
    registrar_ato(
        request, operacao="criar", alvo_tipo="unidade", alvo_identificador=desfecho.unidade.sigla
    )
    return render(request, TEMPLATE_UNIDADE_CRIADA, {"unidade": desfecho.unidade})


@acao_protegida(ACAO_CRIAR_UNIDADE)
@require_POST
def gravar_unidade_e_selecionar(request: HttpRequest) -> HttpResponse:
    """Mesmo ato, outra resposta — e o nome diz qual: grava e devolve a unidade já escolhida. O
    alvo é o bloco de campos do painel, e o campo de lotação volta por swap fora de banda."""
    autor = _autor(request)
    valores = _valores_da_unidade(request)
    desfecho = cadastrar_unidade(valores)
    if desfecho.unidade is None:
        return render(
            request,
            TEMPLATE_CAMPOS_UNIDADE,
            contexto_criacao_recusada(valores, desfecho.recusa, alcance_do_perfil(autor)),
            status=422,
        )
    registrar_ato(
        request, operacao="criar", alvo_tipo="unidade", alvo_identificador=desfecho.unidade.sigla
    )
    return render(
        request,
        TEMPLATE_UNIDADE_SELECIONADA,
        contexto_unidade_selecionada(desfecho.unidade, alcance_do_perfil(autor)),
    )


def cor_sugerida_unidade(request: HttpRequest) -> HttpResponse:
    selecao = SelecaoUnidadePai.model_validate(request.GET.dict())
    return render(request, TEMPLATE_CAMPO_COR, contexto_cor_sugerida(selecao.pai))


def pagina_unidade(request: HttpRequest, pk: int) -> HttpResponse:
    unidade = get_object_or_404(Unidade.objects.select_related("tipo", "pai"), pk=pk)
    return render(
        request,
        TEMPLATE_PAGINA_UNIDADE,
        contexto_unidade(unidade)
        | {"pode_editar": pode_executar(request.user, ACAO_EDITAR_UNIDADE, unidade.pk)},
    )


@acao_protegida(ACAO_EDITAR_UNIDADE)
def editar_unidade(request: HttpRequest, unidade: int) -> HttpResponse:
    return render(request, TEMPLATE_MODAL_UNIDADE, contexto_modal_unidade(_unidade(unidade)))


@acao_protegida(ACAO_EDITAR_UNIDADE)
@require_POST
def gravar_edicao_unidade(request: HttpRequest, unidade: int) -> HttpResponse:
    valores = {
        # Do caminho da rota, nunca do corpo: é o mesmo id que o decorator conferiu.
        "unidade_id": unidade,
        "nome": request.POST.get("nome", ""),
        "sigla": request.POST.get("sigla", ""),
        "tipo_id": request.POST.get("tipo", ""),
        "pai_id": request.POST.get("pai", ""),
        "cor": request.POST.get("cor", ""),
    }
    # Presença é a confirmação: o hidden só existe no modal que já mostrou o aviso.
    desfecho = alterar_unidade(
        valores,
        transferencia_confirmada="confirmar_transferencia" in request.POST,
    )
    if desfecho.unidade is None:
        # `_unidade(unidade)` relido do banco: `alterar_unidade` já alterou a instância dele em
        # memória, e reaproveitá-la mostraria no lado lido o valor que ainda não vale.
        return render(
            request,
            TEMPLATE_MODAL_UNIDADE,
            contexto_edicao_recusada(
                _unidade(unidade),
                valores,
                desfecho.recusa,
                exige_confirmacao=desfecho.exige_confirmacao,
            ),
            # Falta confirmar não é recusa: 200 com o modal em estado de confirmação, 422 quando a
            # validação recusou de verdade.
            status=200 if desfecho.exige_confirmacao else 422,
        )
    registrar_ato(
        request,
        # O token só existe no modal que já mostrou o aviso, e transferência alguma grava sem
        # ele: é ele que distingue, no histórico, uma correção de nome de uma transferência.
        operacao="transferir" if "confirmar_transferencia" in request.POST else "editar",
        alvo_tipo="unidade",
        alvo_identificador=desfecho.unidade.sigla,
    )
    return render(request, TEMPLATE_EDICAO_CONCLUIDA, contexto_unidade(desfecho.unidade))


def arvore_de_unidades(request: HttpRequest) -> HttpResponse:
    """Rota de leitura, como a página da unidade. Sem unidade em foco: a página do organograma
    abre no topo."""
    return render(request, TEMPLATE_ARVORE, contexto_organograma(None))


def _unidade(pk: int) -> Unidade:
    return get_object_or_404(Unidade.objects.select_related("tipo", "pai"), pk=pk)


def _valores_da_unidade(request: HttpRequest) -> dict[str, str]:
    return {
        "nome": request.POST.get("nome", ""),
        "sigla": request.POST.get("sigla", ""),
        "tipo_id": request.POST.get("tipo", ""),
        "pai_id": request.POST.get("pai", ""),
        "cor": request.POST.get("cor", ""),
    }


def _autor(request: HttpRequest) -> Perfil:
    # AUTH_USER_MODEL é Perfil: autenticado aqui É um Perfil — o decorator já barrou o anônimo.
    return cast(Perfil, request.user)
