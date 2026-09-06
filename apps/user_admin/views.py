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
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.competencias.consulta import alcance_do_perfil
from apps.core.tabela import consulta_da_listagem
from apps.competencias.protecao import acao_protegida, pode_executar, registrar_ato
from apps.unidades.acoes_declaradas import ACAO_EDITAR_UNIDADE
from apps.unidades.context import contexto_unidade
from apps.user_admin.acoes_declaradas import (
    ACAO_CRIAR_SERVIDOR,
    ACAO_DESIGNAR_SUBSTITUTO,
    ACAO_EDITAR_SERVIDOR,
    ACAO_EXONERAR_SERVIDOR,
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
from apps.user_admin.exoneracao import exonerar_servidor, reintegrar_servidor
from apps.user_admin.formularios import (
    ler_nova_substituicao,
    ler_novo_impedimento,
    ler_troca_de_substituto,
)
from apps.user_admin.substituicao import (
    designar_substituto,
    encerrar_substituicao,
    trocar_substituto,
)
from apps.user_admin.context import (
    contexto_administrador_recusado,
    contexto_botao_administrador,
    contexto_cadastro_concluido,
    contexto_cadastro_recusado,
    contexto_corpo_servidores,
    contexto_criar_perfil,
    contexto_edicao_recusada,
    contexto_face_exoneracao,
    contexto_face_substituicao,
    contexto_impedimento_recusado,
    contexto_listagem_servidores,
    contexto_modal_administrador,
    contexto_modal_designar,
    contexto_modal_designar_substituto,
    contexto_modal_encerrar,
    contexto_modal_exonerar_servidor,
    contexto_modal_impedimento,
    contexto_modal_perfil,
    contexto_modal_registrar_impedimento,
    contexto_modal_trocar,
    contexto_opcoes_administrador,
    contexto_opcoes_exoneracao,
    contexto_opcoes_impedimento,
    contexto_opcoes_substituicao,
    contexto_pagina_perfil,
    contexto_secao_exercicio,
)
from apps.user_admin.models import Impedimento, Perfil, Substituicao
from apps.user_admin.schemas import ComandoExoneracao, ConsultaDeServidores, MudancaDeAdministrador
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
TEMPLATE_MODAL_DESIGNAR = "user_admin/partials/_modal_designar.html"
TEMPLATE_MODAL_ENCERRAR = "user_admin/partials/_modal_encerrar.html"
TEMPLATE_MODAL_DESIGNAR_SUBSTITUTO = "user_admin/partials/_modal_designar_substituto.html"
TEMPLATE_FACE_SUBSTITUICAO = "user_admin/partials/_face_substituicao.html"
TEMPLATE_MODAL_EXONERAR = "user_admin/partials/_modal_exonerar_servidor.html"
TEMPLATE_FACE_EXONERACAO = "user_admin/partials/_face_exoneracao.html"
TEMPLATE_EXONERACAO_CONCLUIDA = "user_admin/partials/_exoneracao_concluida.html"


def listar_servidores(request: HttpRequest) -> HttpResponse:
    consulta = consulta_da_listagem(request.GET.dict(), ColunaServidor)
    exonerados = ConsultaDeServidores.model_validate(request.GET.dict()).exonerados
    return render(
        request,
        TEMPLATE_LISTAGEM,
        contexto_listagem_servidores(consulta, exonerados, _alcance_exoneracao_da_leitura(request)),
    )


def corpo_servidores(request: HttpRequest) -> HttpResponse:
    # Alvo do swap do HTMX: só o <tbody>. Trocar o <thead> junto destruiria, a cada tecla, o campo
    # em que se está digitando. `exonerados` viaja no campo oculto do cabeçalho (SPEC
    # user_admin/027) — o mesmo estado do toggle, sem que o filtro/ordenação o derrube.
    consulta = consulta_da_listagem(request.GET.dict(), ColunaServidor)
    exonerados = ConsultaDeServidores.model_validate(request.GET.dict()).exonerados
    return render(
        request,
        TEMPLATE_CORPO_SERVIDORES,
        contexto_corpo_servidores(consulta, exonerados, _alcance_exoneracao_da_leitura(request)),
    )


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
    autor = _autor(request)
    valores = {
        "rf": request.POST.get("rf", ""),
        "nome": request.POST.get("nome", ""),
        "sobrenome": request.POST.get("sobrenome", ""),
        "email": request.POST.get("email", ""),
        "unidade_id": request.POST.get("unidade", ""),
        "cargo_base_id": request.POST.get("cargo_base", ""),
        "cargo_comissao_id": request.POST.get("cargo_comissao", ""),
        "url_acesso": request.build_absolute_uri("/"),
        "administrador": request.POST.get("administrador") == "1",
    }
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
    registrar_ato(
        request,
        operacao="criar_administrador" if desfecho.perfil.is_superuser else "criar",
        alvo_tipo="servidor",
        alvo_identificador=desfecho.perfil.rf,
    )
    return render(request, TEMPLATE_CADASTRO_CONCLUIDO, contexto_cadastro_concluido(desfecho))


def pagina_perfil(request: HttpRequest, pk: int) -> HttpResponse:
    """Rota aberta de leitura (SPEC user_admin/017). O que a autorização decide aqui é um botão."""
    perfil = _perfil(pk)
    return render(
        request,
        TEMPLATE_PAGINA_PERFIL,
        contexto_pagina_perfil(perfil, pode_designar_substituto=_pode_designar_substituto(request, perfil))
        | {
            "pode_editar": pode_executar(request.user, ACAO_EDITAR_SERVIDOR, perfil.unidade_id),
            "pode_registrar_impedimento": _pode_registrar_impedimento(request, perfil),
            "pode_designar_substituto": _pode_designar_substituto(request, perfil),
            "pode_exonerar": _pode_exonerar(request, perfil),
            "pode_reintegrar": _pode_reintegrar(request, perfil),
        },
    )


@acao_protegida(ACAO_EDITAR_SERVIDOR)
def editar_perfil(request: HttpRequest, servidor: int) -> HttpResponse:
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
    valores = {
        "servidor_id": servidor,
        "rf": request.POST.get("rf", ""),
        "nome": request.POST.get("nome", ""),
        "sobrenome": request.POST.get("sobrenome", ""),
        "email": request.POST.get("email", ""),
        "unidade_id": request.POST.get("unidade", ""),
        "cargo_base_id": request.POST.get("cargo_base", ""),
        "cargo_comissao_id": request.POST.get("cargo_comissao", ""),
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
        operacao="editar_administrador" if desfecho.marca_alterada else "editar",
        alvo_tipo="servidor",
        alvo_identificador=desfecho.perfil.rf,
    )
    return render(request, TEMPLATE_EDICAO_CONCLUIDA, contexto_pagina_perfil(desfecho.perfil))


@acao_protegida(ACAO_TORNAR_ADMINISTRADOR)
def modal_administrador(request: HttpRequest) -> HttpResponse:
    return render(request, TEMPLATE_MODAL_ADMINISTRADOR, contexto_modal_administrador())


@acao_protegida(ACAO_TORNAR_ADMINISTRADOR)
def opcoes_administrador(request: HttpRequest) -> HttpResponse:
    unidade = request.GET.get("unidade", "")
    return render(
        request,
        TEMPLATE_OPCOES_SERVIDOR,
        contexto_opcoes_administrador(int(unidade) if unidade.isdigit() else None),
    )


@acao_protegida(ACAO_TORNAR_ADMINISTRADOR)
def estado_administrador(request: HttpRequest) -> HttpResponse:
    servidor = request.GET.get("servidor", "")
    if not servidor.isdigit():
        return HttpResponse("")
    return render(request, TEMPLATE_BOTAO_ADMINISTRADOR, contexto_botao_administrador(_perfil(int(servidor))))


@acao_protegida(ACAO_TORNAR_ADMINISTRADOR)
@require_POST
def gravar_administrador(request: HttpRequest, servidor: int) -> HttpResponse:
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
    registrar_ato(
        request,
        operacao="tornar" if mudanca.tornar else "revogar",
        alvo_tipo="servidor",
        alvo_identificador=desfecho.perfil.rf,
    )
    return render(request, TEMPLATE_BOTAO_ADMINISTRADOR, contexto_botao_administrador(desfecho.perfil))


@acao_protegida(ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR)
def modal_impedimento(request: HttpRequest, servidor: int) -> HttpResponse:
    return render(request, TEMPLATE_MODAL_IMPEDIMENTO, contexto_modal_impedimento(_perfil(servidor)))


@acao_protegida(ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR)
@require_POST
def gravar_impedimento(request: HttpRequest, servidor: int) -> HttpResponse:
    perfil = _perfil(servidor)
    leitura = ler_novo_impedimento(request.POST.dict())
    novo = leitura.dto
    if novo is None:
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
    revogacao = retorno_eh_revogacao(perfil)
    retornar_ao_exercicio(perfil)
    registrar_ato(
        request,
        operacao="revogar" if revogacao else "retornar",
        alvo_tipo="servidor",
        alvo_identificador=perfil.rf,
    )
    return _secao_atualizada(request, perfil)


@acao_protegida(ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR)
def modal_registrar_impedimento(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        TEMPLATE_MODAL_REGISTRAR_IMPEDIMENTO,
        contexto_modal_registrar_impedimento(alcance_do_perfil(_autor(request))),
    )


@acao_protegida(ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR)
def opcoes_impedimento(request: HttpRequest) -> HttpResponse:
    unidade = request.GET.get("unidade", "")
    return render(
        request,
        TEMPLATE_OPCOES_SERVIDOR,
        contexto_opcoes_impedimento(int(unidade) if unidade.isdigit() else None),
    )


@acao_protegida(ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR)
def face_impedimento(request: HttpRequest) -> HttpResponse:
    servidor = request.GET.get("servidor", "")
    if not servidor.isdigit():
        return HttpResponse("")
    perfil = _perfil(int(servidor))
    template = TEMPLATE_AVISO_RETORNO if perfil.esta_impedido else TEMPLATE_FORM_IMPEDIMENTO
    return render(request, template, contexto_modal_impedimento(perfil))


# ---------------------------------------------------------------------------
# Designar substituto, trocar e encerrar (SPEC user_admin/024)
# ---------------------------------------------------------------------------


@acao_protegida(ACAO_DESIGNAR_SUBSTITUTO)
def modal_designar(
    request: HttpRequest,
    servidor: int,
    impedimento: int,
) -> HttpResponse:
    afastamento = get_object_or_404(Impedimento, pk=impedimento, perfil_id=servidor)
    return render(
        request,
        TEMPLATE_MODAL_DESIGNAR,
        contexto_modal_designar(afastamento, alcance_do_perfil(_autor(request))),
    )


@acao_protegida(ACAO_DESIGNAR_SUBSTITUTO)
@require_POST
def gravar_designacao(
    request: HttpRequest,
    servidor: int,
    impedimento: int,
) -> HttpResponse:
    afastamento = get_object_or_404(Impedimento, pk=impedimento, perfil_id=servidor)
    autor = _autor(request)
    alcance = alcance_do_perfil(autor)
    leitura = ler_nova_substituicao(request.POST.dict())
    if leitura.dto is None:
        return render(
            request,
            TEMPLATE_MODAL_DESIGNAR,
            contexto_modal_designar(
                afastamento,
                alcance,
                valores=request.POST.dict(),
                recusa=leitura.recusa,
            ),
            status=422,
        )
    desfecho = designar_substituto(afastamento, leitura.dto, alcance=alcance)
    if desfecho.substituicao is None:
        return render(
            request,
            TEMPLATE_MODAL_DESIGNAR,
            contexto_modal_designar(
                afastamento,
                alcance,
                valores=request.POST.dict(),
                recusa=desfecho.recusa,
            ),
            status=422,
        )
    registrar_ato(
        request,
        operacao="designar",
        alvo_tipo="servidor",
        alvo_identificador=afastamento.perfil.rf,
    )
    return _secao_atualizada(request, afastamento.perfil)


@acao_protegida(ACAO_DESIGNAR_SUBSTITUTO)
def modal_trocar(
    request: HttpRequest,
    servidor: int,
    substituicao: int,
) -> HttpResponse:
    sub = get_object_or_404(Substituicao, pk=substituicao, impedimento__perfil_id=servidor)
    return render(
        request,
        TEMPLATE_MODAL_DESIGNAR,
        contexto_modal_trocar(sub, alcance_do_perfil(_autor(request))),
    )


@acao_protegida(ACAO_DESIGNAR_SUBSTITUTO)
@require_POST
def gravar_troca(
    request: HttpRequest,
    servidor: int,
    substituicao: int,
) -> HttpResponse:
    sub = get_object_or_404(Substituicao, pk=substituicao, impedimento__perfil_id=servidor)
    autor = _autor(request)
    alcance = alcance_do_perfil(autor)
    leitura = ler_troca_de_substituto(request.POST.dict())
    if leitura.dto is None:
        return render(
            request,
            TEMPLATE_MODAL_DESIGNAR,
            contexto_modal_trocar(
                sub,
                alcance,
                valores=request.POST.dict(),
                recusa=leitura.recusa,
            ),
            status=422,
        )
    desfecho = trocar_substituto(sub, leitura.dto, alcance=alcance)
    if desfecho.substituicao is None:
        return render(
            request,
            TEMPLATE_MODAL_DESIGNAR,
            contexto_modal_trocar(
                sub,
                alcance,
                valores=request.POST.dict(),
                recusa=desfecho.recusa,
            ),
            status=422,
        )
    registrar_ato(
        request,
        operacao="trocar",
        alvo_tipo="servidor",
        alvo_identificador=sub.impedimento.perfil.rf,
    )
    return _secao_atualizada(request, sub.impedimento.perfil)


@acao_protegida(ACAO_DESIGNAR_SUBSTITUTO)
def modal_encerrar(
    request: HttpRequest,
    servidor: int,
    substituicao: int,
) -> HttpResponse:
    sub = get_object_or_404(Substituicao, pk=substituicao, impedimento__perfil_id=servidor)
    return render(
        request,
        TEMPLATE_MODAL_ENCERRAR,
        contexto_modal_encerrar(sub),
    )


@acao_protegida(ACAO_DESIGNAR_SUBSTITUTO)
@require_POST
def gravar_encerramento(
    request: HttpRequest,
    servidor: int,
    substituicao: int,
) -> HttpResponse:
    sub = get_object_or_404(Substituicao, pk=substituicao, impedimento__perfil_id=servidor)
    encerrar_substituicao(sub)
    registrar_ato(
        request,
        operacao="encerrar",
        alvo_tipo="servidor",
        alvo_identificador=sub.impedimento.perfil.rf,
    )
    return _secao_atualizada(request, sub.impedimento.perfil)


@acao_protegida(ACAO_DESIGNAR_SUBSTITUTO)
def modal_designar_substituto(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        TEMPLATE_MODAL_DESIGNAR_SUBSTITUTO,
        contexto_modal_designar_substituto(alcance_do_perfil(_autor(request))),
    )


@acao_protegida(ACAO_DESIGNAR_SUBSTITUTO)
def opcoes_substituicao(request: HttpRequest) -> HttpResponse:
    unidade = request.GET.get("unidade", "")
    return render(
        request,
        TEMPLATE_OPCOES_SERVIDOR,
        contexto_opcoes_substituicao(int(unidade) if unidade.isdigit() else None),
    )


@acao_protegida(ACAO_DESIGNAR_SUBSTITUTO)
def face_substituicao(request: HttpRequest) -> HttpResponse:
    servidor = request.GET.get("servidor", "")
    if not servidor.isdigit():
        return HttpResponse("")
    perfil = _perfil(int(servidor))
    impedimento_bruto = request.GET.get("impedimento", "")
    impedimento_id = int(impedimento_bruto) if impedimento_bruto.isdigit() else None
    return render(
        request,
        TEMPLATE_FACE_SUBSTITUICAO,
        contexto_face_substituicao(
            perfil,
            impedimento_id,
            alcance_do_perfil(_autor(request)),
        ),
    )


# ---------------------------------------------------------------------------
# Exonerar e reintegrar, com as três portas (SPEC user_admin/027)
# ---------------------------------------------------------------------------


@acao_protegida(ACAO_EXONERAR_SERVIDOR)
def modal_exonerar_servidor(request: HttpRequest) -> HttpResponse:
    """A rota das três portas: a seção Exercício e a coluna da listagem chegam com `?servidor=`
    já resolvido — a face nasce pronta, sem select algum. O card do painel chega sem parâmetro, e
    as duas listas cascateiam até um servidor ser escolhido."""
    autor = _autor(request)
    id_bruto = request.GET.get("servidor", "")
    servidor = _perfil(int(id_bruto)) if id_bruto.isdigit() else None
    return render(
        request,
        TEMPLATE_MODAL_EXONERAR,
        contexto_modal_exonerar_servidor(servidor, autor.pk, alcance_do_perfil(autor)),
    )


@acao_protegida(ACAO_EXONERAR_SERVIDOR)
def opcoes_exoneracao(request: HttpRequest) -> HttpResponse:
    unidade = request.GET.get("unidade", "")
    return render(
        request,
        TEMPLATE_OPCOES_SERVIDOR,
        contexto_opcoes_exoneracao(int(unidade) if unidade.isdigit() else None),
    )


@acao_protegida(ACAO_EXONERAR_SERVIDOR)
def face_exoneracao(request: HttpRequest) -> HttpResponse:
    servidor = request.GET.get("servidor", "")
    if not servidor.isdigit():
        return HttpResponse("")
    return render(
        request,
        TEMPLATE_FACE_EXONERACAO,
        contexto_face_exoneracao(_perfil(int(servidor)), _autor(request).pk),
    )


@acao_protegida(ACAO_EXONERAR_SERVIDOR)
@require_POST
def gravar_exoneracao(request: HttpRequest, servidor: int) -> HttpResponse:
    comando = ComandoExoneracao(servidor_id=servidor, autor_id=_autor(request).pk)
    desfecho = exonerar_servidor(comando, timezone.localdate())
    if desfecho.perfil is None:
        return render(
            request,
            TEMPLATE_FACE_EXONERACAO,
            contexto_face_exoneracao(_perfil(servidor), _autor(request).pk),
            status=422,
        )
    registrar_ato(
        request,
        operacao="exonerar",
        alvo_tipo="servidor",
        alvo_identificador=desfecho.perfil.rf,
    )
    return _exoneracao_concluida(request, desfecho.perfil)


@acao_protegida(ACAO_EXONERAR_SERVIDOR)
@require_POST
def gravar_reintegracao(request: HttpRequest, servidor: int) -> HttpResponse:
    comando = ComandoExoneracao(servidor_id=servidor, autor_id=_autor(request).pk)
    desfecho = reintegrar_servidor(comando)
    if desfecho.perfil is None:
        return render(
            request,
            TEMPLATE_FACE_EXONERACAO,
            contexto_face_exoneracao(_perfil(servidor), _autor(request).pk),
            status=422,
        )
    registrar_ato(
        request,
        operacao="reintegrar",
        alvo_tipo="servidor",
        alvo_identificador=desfecho.perfil.rf,
    )
    return _exoneracao_concluida(request, desfecho.perfil)


def _exoneracao_concluida(request: HttpRequest, perfil: Perfil) -> HttpResponse:
    """No lugar do #poco-modal: fecha o modal e, na página do próprio servidor, atualiza a
    identidade e a seção de Exercício por hx-swap-oob. Da listagem ou do painel, os ids não
    existem no DOM e o oob simplesmente não encontra alvo."""
    return render(
        request,
        TEMPLATE_EXONERACAO_CONCLUIDA,
        contexto_pagina_perfil(perfil, pode_designar_substituto=_pode_designar_substituto(request, perfil))
        | {
            "pode_registrar_impedimento": _pode_registrar_impedimento(request, perfil),
            "pode_designar_substituto": _pode_designar_substituto(request, perfil),
            "pode_exonerar": _pode_exonerar(request, perfil),
            "pode_reintegrar": _pode_reintegrar(request, perfil),
        },
    )


def _pode_exonerar(request: HttpRequest, perfil: Perfil) -> bool:
    return not perfil.exonerado and pode_executar(request.user, ACAO_EXONERAR_SERVIDOR, perfil.unidade_id)


def _pode_reintegrar(request: HttpRequest, perfil: Perfil) -> bool:
    return perfil.exonerado and pode_executar(request.user, ACAO_EXONERAR_SERVIDOR, perfil.unidade_id)


def _alcance_exoneracao_da_leitura(request: HttpRequest) -> frozenset[int]:
    # A listagem é rota de leitura aberta (§3.5): visitante sem perfil não alcança unidade alguma,
    # e o gesto simplesmente não aparece — a barreira segue sendo a rota de gravação.
    if not request.user.is_authenticated:
        return frozenset()
    return alcance_do_perfil(_autor(request))


def _secao_atualizada(request: HttpRequest, perfil: Perfil) -> HttpResponse:
    contexto = contexto_secao_exercicio(
        perfil,
        _pode_registrar_impedimento(request, perfil),
        pode_designar_substituto=_pode_designar_substituto(request, perfil),
    )
    if perfil.unidade_id:
        contexto |= contexto_unidade(perfil.unidade) | {
            "pode_editar": pode_executar(request.user, ACAO_EDITAR_UNIDADE, perfil.unidade_id),
            "pode_designar_substituto": _pode_designar_substituto(request, perfil),
        }
    return render(
        request,
        TEMPLATE_IMPEDIMENTO_CONCLUIDO,
        contexto,
    )


def _pode_registrar_impedimento(request: HttpRequest, perfil: Perfil) -> bool:
    return pode_executar(request.user, ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR, perfil.unidade_id)


def _pode_designar_substituto(request: HttpRequest, perfil: Perfil) -> bool:
    return pode_executar(request.user, ACAO_DESIGNAR_SUBSTITUTO, perfil.unidade_id)


def _perfil(pk: int) -> Perfil:
    return get_object_or_404(
        Perfil.objects.select_related("unidade", "cargo_base", "cargo_comissao"),
        pk=pk,
    )


def _autor(request: HttpRequest) -> Perfil:
    return cast(Perfil, request.user)
