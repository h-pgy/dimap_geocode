"""
Páginas administrativas de servidor (SPEC user_admin/007), a listagem de servidores
(SPEC user_admin/013), a página própria do servidor (SPEC user_admin/017), o cadastro de servidor
(SPEC criacao_usuarios/004) e a edição dele (SPEC criacao_usuarios/005): ver um servidor é página
e editar é modal, buscado por rota própria. Criar e editar servidor são atos administrativos —
`criar_perfil`/`editar_perfil` só abrem a tela, e são `gravar_servidor`/`gravar_edicao` quem
gravam (§3.5).

As rotas de LEITURA de servidor nascem ABERTAS, exceção declarada nas SPECs 013 e 017 nos termos
do §3.5: a proteção por perfil de administrador entra com a SPEC de autenticação.
"""

from typing import cast

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.competencias.consulta import alcance_do_perfil
from apps.core.tabela import consulta_da_listagem
from apps.competencias.protecao import acao_protegida, pode_executar, registrar_ato
from apps.user_admin.acoes_declaradas import (
    ACAO_CRIAR_SERVIDOR,
    ACAO_EDITAR_SERVIDOR,
    ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR,
    ACAO_TORNAR_ADMINISTRADOR,
)
from apps.user_admin.administrador import mudar_administrador
from apps.user_admin.cadastro import criar_servidor, editar_servidor
from apps.user_admin.exercicio import (
    registrar_impedimento,
    retornar_ao_exercicio,
    retorno_eh_revogacao,
)
from apps.user_admin.formularios import ler_novo_impedimento
from apps.user_admin.context import (
    contexto_administrador_recusado,
    contexto_botao_administrador,
    contexto_cadastro_concluido,
    contexto_cadastro_recusado,
    contexto_corpo_servidores,
    contexto_criar_perfil,
    contexto_edicao_recusada,
    contexto_impedimento_recusado,
    contexto_listagem_servidores,
    contexto_modal_administrador,
    contexto_modal_impedimento,
    contexto_modal_perfil,
    contexto_modal_registrar_impedimento,
    contexto_opcoes_administrador,
    contexto_opcoes_impedimento,
    contexto_pagina_perfil,
    contexto_secao_exercicio,
)
from apps.user_admin.models import Perfil
from apps.user_admin.schemas import MudancaDeAdministrador
from services.domain.listagem_gestao import ColunaServidor
from services.utils.erros_formulario import RecusaDeFormulario

TEMPLATE_FORMULARIO = "user_admin/perfil_form.html"
TEMPLATE_FORMULARIO_RECUSADO = "user_admin/partials/_formulario_servidor.html"
TEMPLATE_CADASTRO_CONCLUIDO = "user_admin/partials/_cadastro_concluido.html"
TEMPLATE_PAGINA_PERFIL = "user_admin/perfil.html"
TEMPLATE_MODAL_PERFIL = "user_admin/partials/_modal_editar_perfil.html"
TEMPLATE_EDICAO_CONCLUIDA = "user_admin/partials/_edicao_concluida.html"
TEMPLATE_LISTAGEM = "user_admin/servidores_list.html"
TEMPLATE_CORPO_SERVIDORES = "user_admin/partials/_corpo_servidores.html"
TEMPLATE_MODAL_ADMINISTRADOR = "user_admin/partials/_modal_administrador.html"
TEMPLATE_OPCOES_SERVIDOR = "user_admin/partials/_opcoes_servidor.html"
TEMPLATE_BOTAO_ADMINISTRADOR = "user_admin/partials/_botao_administrador.html"
TEMPLATE_MODAL_IMPEDIMENTO = "user_admin/partials/_modal_impedimento.html"
TEMPLATE_MODAL_RETORNO = "user_admin/partials/_modal_retorno.html"
TEMPLATE_IMPEDIMENTO_CONCLUIDO = "user_admin/partials/_impedimento_concluido.html"
TEMPLATE_MODAL_REGISTRAR_IMPEDIMENTO = "user_admin/partials/_modal_registrar_impedimento.html"
TEMPLATE_FORM_IMPEDIMENTO = "user_admin/partials/_form_impedimento.html"
TEMPLATE_AVISO_RETORNO = "user_admin/partials/_aviso_retorno.html"


def listar_servidores(request: HttpRequest) -> HttpResponse:
    consulta = consulta_da_listagem(request.GET.dict(), ColunaServidor)
    return render(request, TEMPLATE_LISTAGEM, contexto_listagem_servidores(consulta))


def corpo_servidores(request: HttpRequest) -> HttpResponse:
    # Alvo do swap do HTMX: só o <tbody>. Trocar o <thead> junto destruiria, a cada tecla, o campo
    # em que se está digitando.
    consulta = consulta_da_listagem(request.GET.dict(), ColunaServidor)
    return render(request, TEMPLATE_CORPO_SERVIDORES, contexto_corpo_servidores(consulta))


@acao_protegida(ACAO_CRIAR_SERVIDOR)
def criar_perfil(request: HttpRequest) -> HttpResponse:
    # Oferecer o que o decorator vai recusar no POST é convidar ao 403: a lista sai do mesmo
    # alcance que a barreira confere.
    autor = _autor(request)
    return render(
        request,
        TEMPLATE_FORMULARIO,
        contexto_criar_perfil(alcance_do_perfil(autor), pode_executar(autor, ACAO_TORNAR_ADMINISTRADOR)),
    )


@acao_protegida(ACAO_CRIAR_SERVIDOR)
@require_POST
def gravar_servidor(request: HttpRequest) -> HttpResponse:
    # A view traduz nome de controle em nome de campo e NÃO constrói o DTO: quem o constrói é o
    # ato, porque a recusa dele volta como o próprio formulário, não como página de erro (SPEC
    # formularios/001). `.get(..., "")` porque só `unidade` tem rede — o decorator já devolve 400
    # quando ela falta; nos demais, chave ausente daria 500 justamente na rota que existe para
    # transformar entrada ruim em recusa na tela.
    autor = _autor(request)
    valores = {
        "rf": request.POST.get("rf", ""),
        "nome": request.POST.get("nome", ""),
        "sobrenome": request.POST.get("sobrenome", ""),
        "email": request.POST.get("email", ""),
        "unidade_id": request.POST.get("unidade", ""),
        "cargo_base_id": request.POST.get("cargo_base", ""),
        "cargo_comissao_id": request.POST.get("cargo_comissao", ""),
        # O host de onde o convite parte é da orquestração, não do formulário.
        "url_acesso": request.build_absolute_uri("/"),
        # SPEC user_admin/022: bool explícito, não string crua — o mesmo molde de
        # `confirmar_transferencia` em `unidades/views.py`.
        "administrador": request.POST.get("administrador") == "1",
    }
    # Quem pode armar a marca é resolvido aqui, na orquestração, e desce como dado — o mesmo
    # desenho de `raiz_permitida` em `unidades.gravar_unidade`.
    desfecho = criar_servidor(valores, foto=request.FILES.get("foto"), administrador_permitido=autor.is_superuser)
    if desfecho.perfil is None:
        return render(
            request,
            TEMPLATE_FORMULARIO_RECUSADO,
            contexto_cadastro_recusado(
                valores,
                desfecho.recusa,
                alcance_do_perfil(autor),
                pode_executar(autor, ACAO_TORNAR_ADMINISTRADOR),
            ),
            status=422,
        )
    # A view NUNCA grava a execução: deixa o recado e quem persiste é o decorator, depois do return.
    registrar_ato(
        request,
        # SPEC user_admin/022: operação própria — cadastrar alguém já administrador não é o
        # mesmo ato que cadastrar um servidor comum, e o histórico precisa separá-los.
        operacao="criar_administrador" if desfecho.perfil.is_superuser else "criar",
        alvo_tipo="servidor",
        alvo_identificador=desfecho.perfil.rf,
    )
    return render(request, TEMPLATE_CADASTRO_CONCLUIDO, contexto_cadastro_concluido(desfecho.perfil))


def pagina_perfil(request: HttpRequest, pk: int) -> HttpResponse:
    """Rota aberta de leitura (SPEC user_admin/017). O que a autorização decide aqui é um botão."""
    perfil = _perfil(pk)
    return render(
        request,
        TEMPLATE_PAGINA_PERFIL,
        contexto_pagina_perfil(perfil)
        | {
            "pode_editar": pode_executar(request.user, ACAO_EDITAR_SERVIDOR, perfil.unidade_id),
            # Esconder o botão é UX; a barreira é o `acao_protegida` das rotas. O `pode_executar`
            # responde às duas conferências de uma vez — competência e alcance —, e por isso recebe
            # a unidade do servidor da página.
            "pode_registrar_impedimento": _pode_registrar_impedimento(request, perfil),
        },
    )


@acao_protegida(ACAO_EDITAR_SERVIDOR)
def editar_perfil(request: HttpRequest, servidor: int) -> HttpResponse:
    # Só o partial do modal: a página de leitura não o carrega, e os catálogos dos selects só são
    # consultados quando alguém abre o lápis. Nenhuma conferência de lotação escrita aqui: o
    # contrato da ação declara o alcance pela pessoa, e o decorator já resolveu a unidade dela.
    # Oferecer destino que o decorator vai recusar no POST é convidar ao 403 — que o HTMX não troca
    # na tela: a lista sai do mesmo alcance que a barreira confere, como em `criar_perfil`.
    autor = _autor(request)
    return render(
        request,
        TEMPLATE_MODAL_PERFIL,
        contexto_modal_perfil(
            _perfil(servidor),
            alcance_do_perfil(autor),
            pode_administrador=pode_executar(autor, ACAO_TORNAR_ADMINISTRADOR),
        ),
    )


@acao_protegida(ACAO_EDITAR_SERVIDOR)
@require_POST
def gravar_edicao(request: HttpRequest, servidor: int) -> HttpResponse:
    # A view traduz nome de controle em nome de campo e NÃO constrói o DTO: quem o constrói é o
    # ato, porque a recusa dele volta como o próprio modal (SPEC formularios/001). `.get(..., "")`
    # porque só `unidade` tem rede — o decorator já devolve 400 quando ela falta; nos demais, chave
    # ausente daria 500 na rota que existe para transformar entrada ruim em recusa na tela.
    valores = {
        # Do caminho da rota, nunca do corpo: é o mesmo id que o decorator conferiu.
        "servidor_id": servidor,
        "rf": request.POST.get("rf", ""),
        "nome": request.POST.get("nome", ""),
        "sobrenome": request.POST.get("sobrenome", ""),
        "email": request.POST.get("email", ""),
        "unidade_id": request.POST.get("unidade", ""),
        "cargo_base_id": request.POST.get("cargo_base", ""),
        "cargo_comissao_id": request.POST.get("cargo_comissao", ""),
        # SPEC user_admin/022 v3: bool explícito, não string crua — o mesmo molde de
        # `gravar_servidor`. A marca viaja com o formulário e é gravada pelo mesmo ato.
        "administrador": request.POST.get("administrador") == "1",
    }
    autor = _autor(request)
    pode_administrador = pode_executar(autor, ACAO_TORNAR_ADMINISTRADOR)
    desfecho = editar_servidor(
        valores,
        autor_id=autor.pk,
        foto=request.FILES.get("foto"),
        administrador_permitido=pode_administrador,
    )
    if desfecho.perfil is None:
        return render(
            request,
            TEMPLATE_MODAL_PERFIL,
            contexto_edicao_recusada(
                _perfil(servidor),
                alcance_do_perfil(autor),
                valores,
                desfecho.recusa,
                pode_administrador,
            ),
            status=422,
        )
    registrar_ato(
        request,
        # SPEC user_admin/022 v3: operação própria — a edição que dá ou tira a condição não é o
        # mesmo ato que a edição comum, e o histórico precisa separá-los.
        operacao="editar_administrador" if desfecho.marca_alterada else "editar",
        alvo_tipo="servidor",
        alvo_identificador=desfecho.perfil.rf,
    )
    # O poço volta vazio — é assim que o modal fecha — e a página se atualiza pelo swap fora de
    # banda que o partial carrega.
    return render(request, TEMPLATE_EDICAO_CONCLUIDA, contexto_pagina_perfil(desfecho.perfil))


@acao_protegida(ACAO_TORNAR_ADMINISTRADOR)
def modal_administrador(request: HttpRequest) -> HttpResponse:
    """A rota direta da ação (SPEC user_admin/022), pinçada pelo `MENU_ADMINISTRADOR`: escolhe-se a
    unidade e, dentro dela, o servidor — sem recorte de alcance, porque só o superusuário chega
    aqui e ele alcança tudo."""
    return render(request, TEMPLATE_MODAL_ADMINISTRADOR, contexto_modal_administrador())


@acao_protegida(ACAO_TORNAR_ADMINISTRADOR)
def opcoes_administrador(request: HttpRequest) -> HttpResponse:
    # A lista de servidores da unidade escolhida, recarregada por HTMX quando o primeiro select
    # muda. Leitura protegida pela mesma ação, e sem registro: é navegação dentro da tela do ato.
    unidade = request.GET.get("unidade", "")
    return render(
        request,
        TEMPLATE_OPCOES_SERVIDOR,
        contexto_opcoes_administrador(int(unidade) if unidade.isdigit() else None),
    )


@acao_protegida(ACAO_TORNAR_ADMINISTRADOR)
def estado_administrador(request: HttpRequest) -> HttpResponse:
    """O botão do servidor escolhido no modal direto — mesmo partial que `gravar_administrador`
    devolve, só que sem gravar nada: é a segunda metade do gesto de escolher (unidade, depois
    servidor), sem registro."""
    servidor = request.GET.get("servidor", "")
    if not servidor.isdigit():
        return HttpResponse("")
    return render(request, TEMPLATE_BOTAO_ADMINISTRADOR, contexto_botao_administrador(_perfil(int(servidor))))


@acao_protegida(ACAO_TORNAR_ADMINISTRADOR)
@require_POST
def gravar_administrador(request: HttpRequest, servidor: int) -> HttpResponse:
    # DTO na fronteira; malformado morre no PydanticValidationMiddleware. `servidor` vem do caminho
    # da rota, e o autor do request — nenhum dos dois do corpo, que o cliente escreve.
    mudanca = MudancaDeAdministrador(
        servidor_id=servidor,
        tornar=request.POST.get("tornar") == "1",
        autor_id=_autor(request).pk,
    )
    desfecho = mudar_administrador(mudanca)
    if desfecho.perfil is None:
        return render(
            request,
            TEMPLATE_BOTAO_ADMINISTRADOR,
            contexto_administrador_recusado(_perfil(servidor), desfecho.recusa),
            status=422,
        )
    # Duas operações, uma ação: é o que torna conceder e revogar distinguíveis no histórico.
    registrar_ato(
        request,
        operacao="tornar" if mudanca.tornar else "revogar",
        alvo_tipo="servidor",
        alvo_identificador=desfecho.perfil.rf,
    )
    return render(request, TEMPLATE_BOTAO_ADMINISTRADOR, contexto_botao_administrador(desfecho.perfil))


@acao_protegida(ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR)
def modal_impedimento(request: HttpRequest, servidor: int) -> HttpResponse:
    """O diálogo que a seção de exercício abre (SPEC user_admin/023). Nenhuma conferência de lotação
    escrita aqui: o contrato declara o alcance pela pessoa, e o decorator já resolveu a unidade
    dela."""
    return render(request, TEMPLATE_MODAL_IMPEDIMENTO, contexto_modal_impedimento(_perfil(servidor)))


@acao_protegida(ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR)
@require_POST
def gravar_impedimento(request: HttpRequest, servidor: int) -> HttpResponse:
    # A view lê o formulário e NÃO constrói o DTO: a recusa dele volta como o próprio modal, e é por
    # isso que ela não passa pelo PydanticValidationMiddleware (SPEC formularios/001).
    perfil = _perfil(servidor)
    leitura = ler_novo_impedimento(request.POST.dict())
    novo = leitura.dto
    if novo is None:
        # Sem DTO a leitura traz a recusa; o `or` é só o que o tipo pede, não um caso real.
        return render(
            request,
            TEMPLATE_MODAL_IMPEDIMENTO,
            contexto_impedimento_recusado(
                perfil,
                request.POST.dict(),
                leitura.recusa or RecusaDeFormulario(),
            ),
            status=422,
        )
    registrar_impedimento(perfil, novo)
    registrar_ato(
        request,
        operacao="registrar",
        alvo_tipo="servidor",
        alvo_identificador=perfil.rf,
    )
    return _secao_atualizada(request, perfil)


@acao_protegida(ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR)
def modal_retorno(request: HttpRequest, servidor: int) -> HttpResponse:
    return render(request, TEMPLATE_MODAL_RETORNO, contexto_modal_impedimento(_perfil(servidor)))


@acao_protegida(ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR)
@require_POST
def gravar_retorno(request: HttpRequest, servidor: int) -> HttpResponse:
    perfil = _perfil(servidor)
    # A pergunta é sobre o estado ANTES do ato: depois dele não sobra vigente algum a consultar.
    revogacao = retorno_eh_revogacao(perfil)
    retornar_ao_exercicio(perfil)
    registrar_ato(
        request,
        # Três operações, uma ação: registrar, devolver a cadeira e revogar um registro que nunca
        # vigorou são fatos diferentes, e é a operação que os separa no histórico.
        operacao="revogar" if revogacao else "retornar",
        alvo_tipo="servidor",
        alvo_identificador=perfil.rf,
    )
    return _secao_atualizada(request, perfil)


@acao_protegida(ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR)
def modal_registrar_impedimento(request: HttpRequest) -> HttpResponse:
    # Oferecer unidade que o decorator vai recusar no POST é convidar ao 403, que o HTMX não troca
    # na tela: o select sai do MESMO alcance que a barreira confere (molde de `criar_perfil`).
    return render(
        request,
        TEMPLATE_MODAL_REGISTRAR_IMPEDIMENTO,
        contexto_modal_registrar_impedimento(alcance_do_perfil(_autor(request))),
    )


@acao_protegida(ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR)
def opcoes_impedimento(request: HttpRequest) -> HttpResponse:
    # A lista de servidores da unidade escolhida, recarregada por HTMX quando o primeiro select
    # muda. Leitura protegida pela mesma ação, e sem registro: é navegação dentro da tela do ato.
    unidade = request.GET.get("unidade", "")
    return render(
        request,
        TEMPLATE_OPCOES_SERVIDOR,
        contexto_opcoes_impedimento(int(unidade) if unidade.isdigit() else None),
    )


@acao_protegida(ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR)
def face_impedimento(request: HttpRequest) -> HttpResponse:
    """A segunda metade do gesto de escolher: qual das duas caras o modal mostra é o estado gravado
    do servidor, e não uma escolha de quem abriu — quem está impedido se devolve, quem não está se
    impede. O `servidor` da query string passou pelo `conferir_alvo` do decorator como qualquer
    outro: escolher alguém de outro ramo neste select é 403, e não uma tela que abre e falha no
    POST."""
    servidor = request.GET.get("servidor", "")
    if not servidor.isdigit():
        return HttpResponse("")
    perfil = _perfil(int(servidor))
    template = TEMPLATE_AVISO_RETORNO if perfil.esta_impedido else TEMPLATE_FORM_IMPEDIMENTO
    return render(request, template, contexto_modal_impedimento(perfil))


def _secao_atualizada(request: HttpRequest, perfil: Perfil) -> HttpResponse:
    """O poço volta vazio — é assim que o modal fecha — e a seção se atualiza pelo swap fora de
    banda que o partial carrega, no molde de `_edicao_concluida.html`."""
    return render(
        request,
        TEMPLATE_IMPEDIMENTO_CONCLUIDO,
        contexto_secao_exercicio(perfil, _pode_registrar_impedimento(request, perfil)),
    )


def _pode_registrar_impedimento(request: HttpRequest, perfil: Perfil) -> bool:
    return pode_executar(request.user, ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR, perfil.unidade_id)


def _perfil(pk: int) -> Perfil:
    return get_object_or_404(
        Perfil.objects.select_related("unidade", "cargo_base", "cargo_comissao"),
        pk=pk,
    )


def _autor(request: HttpRequest) -> Perfil:
    # AUTH_USER_MODEL é Perfil: autenticado aqui É um Perfil — o decorator já barrou o anônimo.
    return cast(Perfil, request.user)
