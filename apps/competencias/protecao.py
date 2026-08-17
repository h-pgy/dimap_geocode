"""
A barreira de toda rota de ação (SPEC autorizacao/004): autoriza pelo contrato, confere o alvo que
o alcance declara e grava a execução — autorizada ou não —, no mesmo decorator. Autorizar sem
registrar deixaria o rastro dependente de disciplina de quem escreve a view; conferir o alvo dentro
de cada view deixaria a declaração do contrato sem quem a cumprisse.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import cast

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import BadRequest, PermissionDenied
from django.http import HttpRequest, HttpResponse

from apps.competencias.consulta import alcance_do_perfil
from apps.competencias.registro_execucao import gravar_execucao
from apps.competencias.schemas import AcaoImplementada
from apps.user_admin.models import Perfil
from services.domain.autorizacao import Acao as AcaoDominio
from services.domain.autorizacao import UnidadesSubordinadas

ViewFunc = Callable[..., HttpResponse]

METODOS_QUE_ALTERAM = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def acao_protegida(acao: AcaoImplementada) -> Callable[[ViewFunc], ViewFunc]:
    """Autoriza pelo contrato, confere o alvo declarado e grava a execução — autorizada ou não.

    403 para autenticado, login para anônimo: redirecionar quem já está logado não diz nada, e para
    o HTMX o redirect vira a página de login trocada dentro de um fragmento.

    Grava-se SEMPRE a negativa, e a execução quando ela altera estado: tela de ação é aberta por GET
    a cada navegação e a cada swap, e registrar tudo afogaria o ato de verdade em leitura.
    """

    def decorator(view: ViewFunc) -> ViewFunc:
        @wraps(view)
        def wrapper(request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            # AUTH_USER_MODEL é Perfil: autenticado aqui É um Perfil — narrowing para o resto da
            # função, que só fala a linguagem do domínio (Perfil, nunca o union do Django).
            perfil = cast(Perfil, request.user)
            if not perfil.has_perm(acao.acao.slug):
                gravar_execucao(perfil, acao, autorizado=False)
                raise PermissionDenied
            try:
                conferir_alvo(request, perfil, acao.acao)
            except PermissionDenied:
                gravar_execucao(perfil, acao, autorizado=False)
                raise
            except BadRequest:
                # Parâmetro ausente ou malformado é requisição errada, não tentativa negada contra
                # o alcance — não gera linha.
                raise
            resposta = view(request, *args, **kwargs)
            # `_registro_ato` só existe se a view chamou `registrar_ato` (ver abaixo). É a ÚNICA
            # ponte entre as duas: a view nunca chama `gravar_execucao`, só deixa esse recado.
            registro = getattr(request, "_registro_ato", None)
            if request.method in METODOS_QUE_ALTERAM or registro is not None:
                gravar_execucao(
                    perfil,
                    acao,
                    autorizado=True,
                    operacao=registro.operacao if registro else "",
                    alvo_tipo=registro.alvo_tipo if registro else "",
                    alvo_identificador=registro.alvo_identificador if registro else "",
                )
            return resposta

        return wrapper

    return decorator


def conferir_alvo(request: HttpRequest, perfil: Perfil, acao: AcaoDominio) -> None:
    """Segunda barreira do decorator, e a que faz `alcance` valer alguma coisa. Levanta ou passa —
    quem precisa do alvo é a view, que o relê do próprio request.

    Roda DEPOIS do login e do `has_perm`: sem perfil autenticado não há unidade dirigida de onde
    partir, e perguntar o alcance do anônimo seria consulta jogada fora.
    """
    # Ação sem alcance declarado não incide sobre unidade — é o caso das que recebem uma entidade
    # territorial. Nada a conferir.
    if acao.alcance is None:
        return
    id_bruto = _valor_do_parametro(request, acao.alcance.parametro_id_unidade_alvo)
    if id_bruto is None:
        # A ausência tem duas leituras, e é aqui que elas se separam: em leitura é a tela ainda sem
        # alvo escolhido; em requisição que altera estado é alvo faltando, e sem este ramo um POST
        # que omitisse o parâmetro escaparia da conferência inteira.
        if request.method in METODOS_QUE_ALTERAM:
            raise BadRequest(
                f"Parâmetro obrigatório ausente: '{acao.alcance.parametro_id_unidade_alvo}'."
            )
        return
    if not id_bruto.isdigit():
        # Id malformado é 400, não 500: o valor vem do cliente e nunca chega ao `int()` sem passar
        # por aqui.
        raise BadRequest(
            f"Id malformado para '{acao.alcance.parametro_id_unidade_alvo}': '{id_bruto}'."
        )
    id_unidade_alvo = int(id_bruto)
    # Despacha pelo subtipo concreto de `alcance` — cada um tem sua própria regra de pertencimento,
    # e é por isso que `TipoAlcance` é herança e não enum. Alcance novo sem ramo aqui não passa
    # batido: `NotImplementedError` aponta exatamente este ponto de extensão.
    if isinstance(acao.alcance, UnidadesSubordinadas):
        if not _unidade_esta_subordinada(perfil, id_unidade_alvo):
            # Mesmo tratamento da falta de competência: 403 e linha de negativa. Alvo de outro ramo
            # é tentativa de praticar ato onde não se responde, e é isso que o histórico precisa
            # mostrar.
            raise PermissionDenied
    else:
        raise NotImplementedError(
            f"conferência de alvo não implementada para {type(acao.alcance).__name__}"
        )


def _unidade_esta_subordinada(perfil: Perfil, id_unidade_alvo: int) -> bool:
    return id_unidade_alvo in alcance_do_perfil(perfil)


def _valor_do_parametro(request: HttpRequest, parametro: str) -> str | None:
    """POST antes de GET, e string vazia conta como ausente: `select` sem escolha manda o campo com
    valor vazio, que não é um id."""
    valor = request.POST.get(parametro) or request.GET.get(parametro)
    return valor or None


@dataclass(frozen=True)
class _RegistroAto:
    """Recado da view para o decorator — detalhe interno de `protecao.py`, nunca importado fora
    daqui. Não é DTO de domínio: não cruza a fronteira de nenhum serviço, só passa de uma função
    para a outra dentro do mesmo request."""

    operacao: str
    alvo_tipo: str
    alvo_identificador: str


def registrar_ato(
    request: HttpRequest,
    operacao: str,
    alvo_tipo: str = "",
    alvo_identificador: str = "",
) -> None:
    """Enriquece o registro que o decorator vai gravar — e força a gravação quando o ato é uma
    leitura (emitir um documento, por exemplo), que o decorator sozinho não registraria.

    Só a view sabe sobre o que o ato incidiu; o registro existe mesmo se ela não disser. A view
    NUNCA chama `gravar_execucao` — só grava este recado; quem lê e persiste é sempre o decorator,
    depois que a view retorna.
    """
    request._registro_ato = _RegistroAto(operacao, alvo_tipo, alvo_identificador)  # type: ignore[attr-defined]
