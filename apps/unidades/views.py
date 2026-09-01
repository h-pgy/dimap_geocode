"""
Páginas de unidade: o formulário de cadastro (SPEC user_admin/012), a página própria
(SPEC user_admin/016), o organograma (SPEC user_admin/018), a listagem com organograma integrado
(SPEC user_admin/021) e os três atos que mantêm o organograma (SPEC user_admin/020) — criar, editar
e criar raiz.

As rotas de LEITURA seguem ABERTAS (exceção declarada nas SPECs 016, 018 e 021, §3.5); as de
ESCRITA e as duas de abertura de formulário de ato (`criar_unidade`, `criar_unidade_raiz`,
`editar_unidade`) são protegidas.
"""

from typing import cast

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.competencias.consulta import (
    alcance_do_perfil,
    partidas_do_alcance,
    unidades_dirigidas,
)
from apps.core.tabela import consulta_da_listagem
from apps.competencias.protecao import acao_protegida, pode_executar, registrar_ato
from apps.unidades import extincao
from apps.unidades.acoes_declaradas import (
    ACAO_CRIAR_UNIDADE,
    ACAO_CRIAR_UNIDADE_RAIZ,
    ACAO_DEFINIR_TITULAR,
    ACAO_EDITAR_UNIDADE,
    ACAO_EXTINGUIR_UNIDADE,
)
from apps.user_admin.acoes_declaradas import ACAO_DESIGNAR_SUBSTITUTO
from apps.unidades.cadastro import alterar_unidade, cadastrar_unidade
from apps.unidades.context import (
    contexto_ato_recusado,
    contexto_corpo_unidades,
    contexto_cor_sugerida,
    contexto_criacao_recusada,
    contexto_criar_unidade,
    contexto_edicao_recusada,
    contexto_listagem_unidades,
    contexto_modal_do_ato,
    contexto_modal_unidade,
    contexto_previa_do_ato,
    contexto_secao_direcao,
    contexto_unidade,
    contexto_unidade_selecionada,
)
from apps.unidades.models import Unidade, cargo_titulariza
from apps.unidades.schemas import ConsultaDeUnidades, SelecaoUnidadePai
from apps.unidades.titularidade import definir_titular, destituir_titular
from apps.user_admin.models import Perfil
from services.domain.listagem_gestao import ColunaUnidade

TEMPLATE_UNIDADE = "unidades/unidade_form.html"
TEMPLATE_UNIDADE_FORM = "unidades/partials/_formulario_unidade.html"
TEMPLATE_UNIDADE_CRIADA = "unidades/partials/_unidade_criada.html"
TEMPLATE_CAMPOS_UNIDADE = "unidades/partials/_campos_unidade.html"
TEMPLATE_UNIDADE_SELECIONADA = "unidades/partials/_unidade_criada_e_selecionada.html"
TEMPLATE_MODAL_UNIDADE = "unidades/partials/_modal_editar_unidade.html"
TEMPLATE_EDICAO_CONCLUIDA = "unidades/partials/_edicao_unidade_concluida.html"
TEMPLATE_PAGINA_UNIDADE = "unidades/unidade.html"
TEMPLATE_CAMPO_COR = "unidades/partials/_campo_cor_unidade.html"
TEMPLATE_LISTAGEM_UNIDADES = "unidades/unidades_list.html"
TEMPLATE_CORPO_UNIDADES = "unidades/partials/_corpo_unidades.html"
TEMPLATE_PAINEL_UNIDADES = "unidades/partials/_painel_unidades.html"
TEMPLATE_MODAL_ATO = "unidades/partials/_modal_ato_unidade.html"
TEMPLATE_PREVIA_ATO = "unidades/partials/_previa_e_botao_do_ato.html"
TEMPLATE_REATIVACAO_CONCLUIDA = "unidades/partials/_reativacao_concluida.html"
TEMPLATE_MODAL_TITULARIDADE = "unidades/partials/_modal_definir_titular_standalone.html"
TEMPLATE_FACE_TITULARIDADE = "unidades/partials/_face_titularidade.html"
TEMPLATE_TITULARIDADE_CONCLUIDA = "unidades/partials/_titularidade_concluida.html"



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
    # `todas`: a página é o único lugar em que a unidade extinta se mostra por si, e é onde mora o
    # gesto de trazê-la de volta (SPEC user_admin/025).
    unidade = get_object_or_404(Unidade.todas.select_related("tipo", "pai"), pk=pk)
    extinta = unidade.extinta_em is not None
    return render(
        request,
        TEMPLATE_PAGINA_UNIDADE,
        contexto_unidade(unidade)
        | {
            # Gesto de unidade viva não se oferece a unidade extinta, e vice-versa: a barreira
            # segue na rota, e a tela não convida ao 403.
            "pode_editar": not extinta and pode_executar(request.user, ACAO_EDITAR_UNIDADE, unidade.pk),
            "pode_designar_substituto": not extinta
            and pode_executar(request.user, ACAO_DESIGNAR_SUBSTITUTO, unidade.pk),
            "pode_definir_titular": not extinta
            and pode_executar(request.user, ACAO_DEFINIR_TITULAR, unidade.pk),
            # Extinguir e reativar são a MESMA competência (Caveats): a página oferece o gesto que
            # cabe ao estado da unidade — nunca os dois.
            "pode_extinguir": not extinta
            and pode_executar(request.user, ACAO_EXTINGUIR_UNIDADE, unidade.pk),
            "pode_reativar": extinta
            and pode_executar(request.user, ACAO_EXTINGUIR_UNIDADE, unidade.pk),
        },
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
    return render(
        request,
        TEMPLATE_EDICAO_CONCLUIDA,
        contexto_unidade(desfecho.unidade)
        | {
            "pode_editar": pode_executar(request.user, ACAO_EDITAR_UNIDADE, desfecho.unidade.pk),
            "pode_designar_substituto": pode_executar(
                request.user, ACAO_DESIGNAR_SUBSTITUTO, desfecho.unidade.pk
            ),
        },
    )


def listar_unidades(request: HttpRequest) -> HttpResponse:
    """Rota de leitura: a tabela filtrável com o organograma no topo. `?foco=<pk>` é como a seção
    de hierarquia da página da unidade chega aqui — a unidade já situada na árvore e no topo da
    tabela."""
    consulta = consulta_da_listagem(request.GET.dict(), ColunaUnidade)
    parametros = ConsultaDeUnidades.model_validate(request.GET.dict())
    unidade_em_foco = Unidade.todas.filter(pk=parametros.foco).first() if parametros.foco else None
    return render(
        request,
        TEMPLATE_LISTAGEM_UNIDADES,
        contexto_listagem_unidades(
            consulta, unidade_em_foco, parametros.extintas, _alcance_extincao_da_leitura(request)
        ),
    )


def painel_unidades(request: HttpRequest) -> HttpResponse:
    """Rota de leitura, alvo do toggle (SPEC user_admin/025). Troca o painel inteiro porque ligar as
    extintas muda a árvore, a tabela e o próprio estado da barra."""
    consulta = consulta_da_listagem(request.GET.dict(), ColunaUnidade)
    parametros = ConsultaDeUnidades.model_validate(request.GET.dict())
    unidade_em_foco = Unidade.todas.filter(pk=parametros.foco).first() if parametros.foco else None
    return render(
        request,
        TEMPLATE_PAINEL_UNIDADES,
        contexto_listagem_unidades(
            consulta, unidade_em_foco, parametros.extintas, _alcance_extincao_da_leitura(request)
        ),
    )


def corpo_unidades(request: HttpRequest) -> HttpResponse:
    # Alvo do swap do HTMX: só o <tbody>. Trocar o <thead> junto destruiria, a cada tecla, o campo
    # em que se está digitando. `extintas` viaja no campo oculto do cabeçalho (SPEC user_admin/025)
    # — o mesmo estado do toggle, sem que o filtro/ordenação o derrube.
    consulta = consulta_da_listagem(request.GET.dict(), ColunaUnidade)
    extintas = ConsultaDeUnidades.model_validate(request.GET.dict()).extintas
    return render(
        request,
        TEMPLATE_CORPO_UNIDADES,
        contexto_corpo_unidades(consulta, extintas=extintas, alcance_extincao=_alcance_extincao_da_leitura(request)),
    )


@acao_protegida(ACAO_EXTINGUIR_UNIDADE)
def extinguir_unidade(request: HttpRequest) -> HttpResponse:
    """Abre o modal do ato — a face sai do estado da unidade escolhida, com a unidade da linha, a
    em foco ou nenhuma (SPEC user_admin/025)."""
    autor = _autor(request)
    id_bruto = request.GET.get("unidade", "")
    unidade = Unidade.todas.filter(pk=id_bruto).first() if id_bruto.isdigit() else None
    return render(
        request, TEMPLATE_MODAL_ATO, contexto_modal_do_ato(unidade, _alcance_extincao(autor))
    )


@acao_protegida(ACAO_EXTINGUIR_UNIDADE)
def previa_do_ato(request: HttpRequest) -> HttpResponse:
    """Alvo do hx-get do select, ao trocar de unidade dentro do modal (SPEC user_admin/025)."""
    unidade = get_object_or_404(Unidade.todas, pk=request.GET.get("unidade"))
    return render(request, TEMPLATE_PREVIA_ATO, contexto_previa_do_ato(unidade))


@acao_protegida(ACAO_EXTINGUIR_UNIDADE)
@require_POST
def gravar_extincao_unidade(request: HttpRequest) -> HttpResponse:
    autor = _autor(request)
    valores = {"unidade_id": request.POST.get("unidade", "")}
    desfecho = extincao.extinguir_unidade(valores, timezone.localdate())
    if desfecho.unidade is None:
        return render(
            request,
            TEMPLATE_MODAL_ATO,
            contexto_ato_recusado(valores, desfecho.recusa, _alcance_extincao(autor)),
            status=422,
        )
    registrar_ato(
        request, operacao="extinguir", alvo_tipo="unidade", alvo_identificador=desfecho.unidade.sigla
    )
    consulta = consulta_da_listagem({}, ColunaUnidade)
    # `oob`: o POST responde ao `#poco-modal`, e o painel de verdade mora fora dele — sem o swap
    # fora de banda ele entraria duplicado, aninhado dentro do poço do modal.
    return render(
        request,
        TEMPLATE_PAINEL_UNIDADES,
        contexto_listagem_unidades(consulta, alcance_extincao=_alcance_extincao(autor)) | {"oob": True},
    )


@acao_protegida(ACAO_EXTINGUIR_UNIDADE)
@require_POST
def gravar_reativacao_unidade(request: HttpRequest) -> HttpResponse:
    """A outra operação da MESMA ação (SPEC user_admin/025): mesma barreira, mesmo alcance, outro
    desfecho e outra palavra no histórico."""
    autor = _autor(request)
    valores = {"unidade_id": request.POST.get("unidade", "")}
    desfecho = extincao.reativar_unidade(valores)
    if desfecho.unidade is None:
        return render(
            request,
            TEMPLATE_MODAL_ATO,
            contexto_ato_recusado(valores, desfecho.recusa, _alcance_extincao(autor)),
            status=422,
        )
    registrar_ato(
        request, operacao="reativar", alvo_tipo="unidade", alvo_identificador=desfecho.unidade.sigla
    )
    return render(
        request,
        TEMPLATE_REATIVACAO_CONCLUIDA,
        contexto_unidade(desfecho.unidade)
        | {
            "pode_editar": pode_executar(request.user, ACAO_EDITAR_UNIDADE, desfecho.unidade.pk),
            "pode_designar_substituto": pode_executar(
                request.user, ACAO_DESIGNAR_SUBSTITUTO, desfecho.unidade.pk
            ),
        },
    )


def _alcance_extincao(perfil: Perfil) -> frozenset[int]:
    # O ramo, MENOS as unidades de onde ele parte, mas COM as extintas: sem elas a unidade
    # recém-extinta sairia do alcance de quem a extinguiu e ninguém poderia reativá-la (SPEC
    # user_admin/025, mesma conta de `_conjunto_alcancado`).
    return alcance_do_perfil(perfil, com_extintas=True) - partidas_do_alcance(perfil)


def _alcance_extincao_da_leitura(request: HttpRequest) -> frozenset[int]:
    # As rotas de leitura da listagem são abertas (§3.5): visitante sem perfil não alcança unidade
    # alguma, e a lixeira simplesmente não aparece — a barreira segue sendo a rota de gravação.
    if not request.user.is_authenticated:
        return frozenset()
    return _alcance_extincao(cast(Perfil, request.user))


def arvore_de_unidades(request: HttpRequest) -> HttpResponse:
    """A página só do organograma foi absorvida pela listagem, que traz a mesma árvore com a tabela
    ao lado (SPEC user_admin/021). A rota sobrevive como redirect porque ela circulou: link velho
    não pode virar 404."""
    return redirect("unidades:listar_unidades")


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


@acao_protegida(ACAO_DEFINIR_TITULAR)
def modal_definir_titular(request: HttpRequest) -> HttpResponse:
    """Rota direta do painel / menu: abre o modal com o seletor de unidades do alcance."""
    autor = _autor(request)
    alcance = (
        Unidade.objects.all().order_by("sigla")
        if autor.is_superuser
        else Unidade.objects.filter(
            pk__in=(alcance_do_perfil(autor) - unidades_dirigidas(autor))
        ).order_by("sigla")
    )
    return render(
        request,
        TEMPLATE_MODAL_TITULARIDADE,
        {"unidades": alcance},
    )


@acao_protegida(ACAO_DEFINIR_TITULAR)
def face_titularidade(request: HttpRequest) -> HttpResponse:
    """Atualiza a face do modal conforme a unidade escolhida no select."""
    unidade_id = request.GET.get("unidade", "")
    if not unidade_id.isdigit():
        return HttpResponse("")
    unidade = get_object_or_404(Unidade, pk=int(unidade_id))
    return render(
        request,
        TEMPLATE_FACE_TITULARIDADE,
        contexto_unidade(unidade),
    )


@acao_protegida(ACAO_DEFINIR_TITULAR)
@require_POST
def gravar_definir_titular(request: HttpRequest) -> HttpResponse:
    unidade_id = request.POST.get("unidade", "")
    titular_id = request.POST.get("titular", "")
    if not unidade_id.isdigit() or not titular_id.isdigit():
        return HttpResponse(status=400)
    unidade_obj = get_object_or_404(Unidade, pk=int(unidade_id))
    novo_titular = get_object_or_404(Perfil, pk=int(titular_id))
    if (
        novo_titular.unidade_id != unidade_obj.id
        or not novo_titular.em_exercicio
        or not novo_titular.cargo_comissao
        or not cargo_titulariza(
            novo_titular.cargo_comissao,
            exige_alta_administracao=unidade_obj.tipo.exige_alta_administracao,
            nivel_minimo=unidade_obj.tipo.nivel_minimo_titular,
        )
    ):
        return HttpResponse(status=422)
    operacao = "trocar" if unidade_obj.titular is not None else "definir"
    definir_titular(novo_titular)
    registrar_ato(
        request,
        operacao=operacao,
        alvo_tipo="unidade",
        alvo_identificador=unidade_obj.sigla,
    )
    return render(
        request,
        TEMPLATE_TITULARIDADE_CONCLUIDA,
        contexto_secao_direcao(unidade_obj, request.user),
    )


@acao_protegida(ACAO_DEFINIR_TITULAR)
@require_POST
def gravar_destituir_titular(request: HttpRequest) -> HttpResponse:
    unidade_id = request.POST.get("unidade", "")
    if not unidade_id.isdigit():
        return HttpResponse(status=400)
    unidade_obj = get_object_or_404(Unidade, pk=int(unidade_id))
    destituir_titular(unidade_obj)
    registrar_ato(
        request,
        operacao="destituir",
        alvo_tipo="unidade",
        alvo_identificador=unidade_obj.sigla,
    )
    return render(
        request,
        TEMPLATE_TITULARIDADE_CONCLUIDA,
        contexto_secao_direcao(unidade_obj, request.user),
    )


