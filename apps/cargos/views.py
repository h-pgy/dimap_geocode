"""
Páginas do catálogo de cargos em comissão (SPEC user_admin/029): a listagem é leitura aberta a
qualquer servidor autenticado — os quatro atos que a mantêm são exclusivos do administrador do
sistema, sem alcance (o catálogo é global).
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.cargos import cadastro, extincao
from apps.cargos.acoes_declaradas import (
    ACAO_CRIAR_CARGO,
    ACAO_EDITAR_CARGO,
    ACAO_EXTINGUIR_CARGO,
    ACAO_REATIVAR_CARGO,
)
from apps.cargos.context import (
    contexto_ato_extincao_recusado,
    contexto_ato_reativacao_recusado,
    contexto_corpo_cargos,
    contexto_criacao_recusada,
    contexto_edicao_recusada,
    contexto_listagem_cargos,
    contexto_modal_criar_cargo,
    contexto_modal_editar_cargo,
    contexto_modal_extinguir,
    contexto_modal_reativar,
)
from apps.cargos.models import CargoComissao
from apps.competencias.protecao import acao_protegida, registrar_ato
from apps.core.tabela import consulta_da_listagem
from services.domain.listagem_gestao import ColunaCargo

TEMPLATE_LISTAGEM_CARGOS = "cargos/cargos_list.html"
TEMPLATE_CORPO_CARGOS = "cargos/partials/_corpo_cargos.html"
# O swap fora de banda dos quatro atos usa este envelope, não o de cima: <tbody> não fica de pé
# sozinho fora de uma <table>, e o alvo do POST (#poco-modal) não tem tabela ao redor (Caveats).
TEMPLATE_CORPO_CARGOS_OOB = "cargos/partials/_corpo_cargos_oob.html"
TEMPLATE_MODAL_CRIAR_CARGO = "cargos/partials/_modal_criar_cargo.html"
TEMPLATE_MODAL_EDITAR_CARGO = "cargos/partials/_modal_editar_cargo.html"
TEMPLATE_MODAL_EXTINGUIR_CARGO = "cargos/partials/_modal_extinguir_cargo.html"
TEMPLATE_MODAL_REATIVAR_CARGO = "cargos/partials/_modal_reativar_cargo.html"


def listar_cargos(request: HttpRequest) -> HttpResponse:
    """Rota de leitura aberta: qualquer servidor autenticado (ou não) lê o catálogo. Os gestos de
    ato ficam a cargo do template (`perms.cargos.*`), que os oferece só a quem administra o
    sistema — a barreira de verdade segue nas rotas de ato."""
    consulta = consulta_da_listagem(request.GET.dict(), ColunaCargo)
    return render(request, TEMPLATE_LISTAGEM_CARGOS, contexto_listagem_cargos(consulta))


def corpo_cargos(request: HttpRequest) -> HttpResponse:
    """Alvo do swap do HTMX: só o <tbody>, disparado pelos filtros e pela ordenação do cabeçalho —
    nunca pelo toggle "Mostrar cargos extintos", que não fala com o servidor (Caveats)."""
    consulta = consulta_da_listagem(request.GET.dict(), ColunaCargo)
    return render(request, TEMPLATE_CORPO_CARGOS, contexto_corpo_cargos(consulta))


@acao_protegida(ACAO_CRIAR_CARGO)
def modal_criar_cargo(request: HttpRequest) -> HttpResponse:
    return render(request, TEMPLATE_MODAL_CRIAR_CARGO, contexto_modal_criar_cargo())


@acao_protegida(ACAO_CRIAR_CARGO)
@require_POST
def gravar_criacao_cargo(request: HttpRequest) -> HttpResponse:
    valores = _valores_do_formulario(request)
    desfecho = cadastro.criar_cargo(valores)
    if desfecho.cargo is None:
        return render(
            request,
            TEMPLATE_MODAL_CRIAR_CARGO,
            contexto_criacao_recusada(valores, desfecho.recusa),
            status=422,
        )
    registrar_ato(
        request, operacao="criar", alvo_tipo="cargo_comissao", alvo_identificador=desfecho.cargo.nome
    )
    return _resposta_concluida(request)


@acao_protegida(ACAO_EDITAR_CARGO)
def modal_editar_cargo(request: HttpRequest) -> HttpResponse:
    cargo = _cargo_do_get(request)
    if cargo is None:
        # Sem cargo escolhido — aberto pelo card, sem linha em foco —, a tela começa pelo select:
        # tanto o vigente quanto o extinto seguem editáveis (SPEC, §2).
        return render(
            request,
            TEMPLATE_MODAL_EDITAR_CARGO,
            {"cargo": None, "cargos_editaveis": CargoComissao.objects.order_by("nome")},
        )
    return render(request, TEMPLATE_MODAL_EDITAR_CARGO, contexto_modal_editar_cargo(cargo))


@acao_protegida(ACAO_EDITAR_CARGO)
@require_POST
def gravar_edicao_cargo(request: HttpRequest, cargo: int) -> HttpResponse:
    alvo = get_object_or_404(CargoComissao, pk=cargo)
    valores = _valores_do_formulario(request) | {"cargo_id": cargo}
    desfecho = cadastro.editar_cargo(alvo, valores)
    if desfecho.cargo is None:
        # `alvo` relido do banco: `editar_cargo` já alterou a instância em memória, e reaproveitá-la
        # mostraria no lado lido o valor que ainda não vale.
        return render(
            request,
            TEMPLATE_MODAL_EDITAR_CARGO,
            contexto_edicao_recusada(_cargo(cargo), valores, desfecho.recusa),
            status=422,
        )
    registrar_ato(
        request, operacao="editar", alvo_tipo="cargo_comissao", alvo_identificador=desfecho.cargo.nome
    )
    return _resposta_concluida(request)


@acao_protegida(ACAO_EXTINGUIR_CARGO)
def modal_extinguir_cargo(request: HttpRequest) -> HttpResponse:
    return render(
        request, TEMPLATE_MODAL_EXTINGUIR_CARGO, contexto_modal_extinguir(_cargo_do_get(request))
    )


@acao_protegida(ACAO_EXTINGUIR_CARGO)
@require_POST
def gravar_extincao_cargo(request: HttpRequest, cargo: int) -> HttpResponse:
    alvo = get_object_or_404(CargoComissao, pk=cargo)
    desfecho = extincao.extinguir_cargo(alvo, timezone.localdate())
    if desfecho.cargo is None:
        return render(
            request,
            TEMPLATE_MODAL_EXTINGUIR_CARGO,
            contexto_ato_extincao_recusado({"cargo": cargo}, desfecho.recusa),
            status=422,
        )
    # O nome DEPOIS do ato: numa edição que renomeia, é o nome novo que fica no rastro (§7).
    registrar_ato(
        request,
        operacao="extinguir",
        alvo_tipo="cargo_comissao",
        alvo_identificador=desfecho.cargo.nome,
    )
    return _resposta_concluida(request)


@acao_protegida(ACAO_REATIVAR_CARGO)
def modal_reativar_cargo(request: HttpRequest) -> HttpResponse:
    return render(
        request, TEMPLATE_MODAL_REATIVAR_CARGO, contexto_modal_reativar(_cargo_do_get(request))
    )


@acao_protegida(ACAO_REATIVAR_CARGO)
@require_POST
def gravar_reativacao_cargo(request: HttpRequest, cargo: int) -> HttpResponse:
    alvo = get_object_or_404(CargoComissao, pk=cargo)
    desfecho = extincao.reativar_cargo(alvo)
    if desfecho.cargo is None:
        return render(
            request,
            TEMPLATE_MODAL_REATIVAR_CARGO,
            contexto_ato_reativacao_recusado({"cargo": cargo}, desfecho.recusa),
            status=422,
        )
    registrar_ato(
        request,
        operacao="reativar",
        alvo_tipo="cargo_comissao",
        alvo_identificador=desfecho.cargo.nome,
    )
    return _resposta_concluida(request)


def _resposta_concluida(request: HttpRequest) -> HttpResponse:
    """O poço do modal responde vazio — é isso que fecha o modal —, e a tabela entra pelo
    hx-swap-oob no lugar dela, com todos os cargos: o toggle não precisa ser lembrado por
    ninguém, porque ele mesmo reaplica o filtro assim que o swap termina (Caveats).

    `TEMPLATE_CORPO_CARGOS_OOB`, não `TEMPLATE_CORPO_CARGOS`: o alvo do POST é #poco-modal, sem
    tabela ao redor, e um <tbody> oob sozinho falha calado sem o envelope <template> (Caveats)."""
    consulta = consulta_da_listagem({}, ColunaCargo)
    return render(request, TEMPLATE_CORPO_CARGOS_OOB, contexto_corpo_cargos(consulta, oob=True))


def _cargo_do_get(request: HttpRequest) -> CargoComissao | None:
    id_bruto = request.GET.get("cargo", "")
    return CargoComissao.objects.filter(pk=id_bruto).first() if id_bruto.isdigit() else None


def _cargo(pk: int) -> CargoComissao:
    return get_object_or_404(CargoComissao, pk=pk)


def _valores_do_formulario(request: HttpRequest) -> dict[str, str]:
    return {
        "nome": request.POST.get("nome", ""),
        "sigla": request.POST.get("sigla", ""),
        "nivel": request.POST.get("nivel", ""),
        "e_chefia": request.POST.get("e_chefia", ""),
        "alta_administracao": request.POST.get("alta_administracao", ""),
    }
