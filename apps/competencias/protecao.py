"""
A barreira de toda rota de ação (SPEC autorizacao/004): autoriza pelo contrato, confere o alvo que
o alcance declara e grava a execução — autorizada ou não —, no mesmo decorator. Autorizar sem
registrar deixaria o rastro dependente de disciplina de quem escreve a view; conferir o alvo dentro
de cada view deixaria a declaração do contrato sem quem a cumprisse.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import wraps
from typing import cast

from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import BadRequest, PermissionDenied
from django.http import HttpRequest, HttpResponse

from apps.competencias.consulta import alcance_do_perfil, partidas_do_alcance
from apps.competencias.registro_execucao import gravar_execucao
from apps.competencias.schemas import AcaoImplementada
from apps.user_admin.models import Perfil
from services.domain.autorizacao import Acao as AcaoDominio
from services.domain.autorizacao import (
    LotacaoAtualEDestino,
    LotacaoDoServidor,
    TipoAlcance,
    UnidadesEstritamenteSubordinadas,
    UnidadesSubordinadas,
)

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
                conferir_alvo(request, perfil, acao.acao, kwargs)
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


def conferir_alvo(
    request: HttpRequest,
    perfil: Perfil,
    acao: AcaoDominio,
    kwargs_da_rota: Mapping[str, object],
) -> None:
    """Segunda barreira do decorator, e a que faz `alcance` valer alguma coisa. Levanta ou passa —
    quem precisa do alvo é a view, que o relê do próprio request.

    Roda DEPOIS do login e do `has_perm`: sem perfil autenticado não há unidade dirigida de onde
    partir, e perguntar o alcance do anônimo seria consulta jogada fora.
    """
    # Ação sem alcance declarado não incide sobre unidade — é o caso das que recebem uma entidade
    # territorial. Nada a conferir.
    if acao.alcance is None:
        return
    # SPEC user_admin/020: alcançar tudo é o que `is_superuser` já significa no `has_perm` do
    # Django — mantê-lo preso ao alcance deixaria o administrador sem poder criar a primeira
    # unidade de um ramo. A saída existe para as ações COM alvo; criar raiz não passa por aqui,
    # porque a ação dela declara `alcance=None` e já retornou acima.
    if perfil.is_superuser:
        return
    valores = _valores_dos_alvos(request, acao.alcance, kwargs_da_rota)
    # Leitura sem alvo escolhido: a tela abre e escolhe depois. Em requisição que altera estado a
    # ausência já virou 400 lá dentro.
    if not valores:
        return
    # Uma passagem só pela árvore, e não uma por alvo: o alcance é o mesmo para os dois.
    alcance = _conjunto_alcancado(acao.alcance, perfil)
    if not all(unidade in alcance for unidade in _unidades_alvo(acao.alcance, valores)):
        raise PermissionDenied


def _conjunto_alcancado(alcance: TipoAlcance, perfil: Perfil) -> frozenset[int]:
    # A conferência de pertencimento continua escrita uma vez só, em `conferir_alvo`; o que muda por
    # alcance é o CONJUNTO em que se procura (SPEC user_admin/025).
    if isinstance(alcance, UnidadesEstritamenteSubordinadas):
        return alcance_do_perfil(perfil, com_extintas=True) - partidas_do_alcance(perfil)
    return alcance_do_perfil(perfil)


def _valores_dos_alvos(
    request: HttpRequest,
    alcance: TipoAlcance,
    kwargs_da_rota: Mapping[str, object],
) -> dict[str, int]:
    """Cada parâmetro declarado, procurado no caminho da rota, no corpo e na query string. Ausência
    tem duas leituras, e é aqui que elas se separam: em leitura é a tela ainda sem alvo escolhido;
    em requisição que altera estado é alvo faltando, e sem este ramo um POST que omitisse o
    parâmetro escaparia da conferência inteira."""
    valores: dict[str, int] = {}
    for parametro in alcance.parametros_alvo:
        id_bruto = _valor_do_parametro(request, parametro, kwargs_da_rota)
        if id_bruto is None:
            if request.method in METODOS_QUE_ALTERAM:
                raise BadRequest(f"Parâmetro obrigatório ausente: '{parametro}'.")
            continue
        if not id_bruto.isdigit():
            # Id malformado é 400, não 500: o valor vem do cliente e nunca chega ao `int()` sem
            # passar por aqui.
            raise BadRequest(f"Id malformado para '{parametro}': '{id_bruto}'.")
        id_alvo = int(id_bruto)
        valores[parametro] = id_alvo
    return valores


def _unidades_alvo(alcance: TipoAlcance, valores: Mapping[str, int]) -> tuple[int, ...]:
    """Despacha pelo subtipo concreto: é ele que sabe se o número é uma unidade ou a pessoa lotada
    nela. A regra de pertencimento é a mesma para todos e fica escrita uma vez só, em
    `conferir_alvo`; alcance novo sem ramo aqui estoura em vez de passar batido."""
    if isinstance(alcance, UnidadesSubordinadas | UnidadesEstritamenteSubordinadas):
        # Os dois alcances de unidade extraem o alvo do mesmo jeito — cada parâmetro declarado
        # carrega uma unidade. O `if` é o mesmo caso de leitura sem alvo escolhido que
        # `_valores_dos_alvos` já deixou passar: em POST a ausência virou 400 lá (SPEC
        # user_admin/020).
        return tuple(valores[parametro] for parametro in alcance.parametros_alvo if parametro in valores)
    if isinstance(alcance, LotacaoDoServidor):
        # A mesma leitura de `LotacaoAtualEDestino`, sem destino: aceitar a unidade do cliente
        # abriria a ação inteira — bastaria mandar a própria (SPEC user_admin/023).
        return (_lotacao_de(valores["servidor"]),)
    if isinstance(alcance, LotacaoAtualEDestino):
        # A origem é lida no banco, nunca recebida do cliente: aceitá-la do request deixaria
        # qualquer um editar quem quisesse, bastando mandar a própria unidade.
        origem = _lotacao_de(valores["servidor"])
        destino = valores.get("unidade")
        return (origem,) if destino is None else (origem, destino)
    raise NotImplementedError(f"alcance sem conferência: {type(alcance).__name__}")


def _lotacao_de(id_servidor: int) -> int:
    """Servidor inexistente não tem lotação e por isso não está no alcance de ninguém: 403, e não
    404 — a rota protegida não confirma quem existe."""
    lotacao = Perfil.objects.filter(pk=id_servidor).values_list("unidade_id", flat=True).first()
    if lotacao is None:
        raise PermissionDenied
    return lotacao


def pode_executar(
    usuario: Perfil | AnonymousUser,
    acao: AcaoImplementada,
    id_unidade_alvo: int | None = None,
) -> bool:
    """A mesma dupla conferência do decorator, na forma de que a TELA precisa: responde em vez de
    levantar. O router filtra e a rota decide (§3.5) — esconder o botão é UX, e a barreira segue
    sendo o `acao_protegida`."""
    if not usuario.has_perm(acao.acao.slug):
        return False
    if acao.acao.alcance is None or id_unidade_alvo is None:
        return True
    return id_unidade_alvo in _conjunto_alcancado(acao.acao.alcance, cast(Perfil, usuario))


def _valor_do_parametro(
    request: HttpRequest,
    parametro: str,
    kwargs_da_rota: Mapping[str, object],
) -> str | None:
    """O caminho da rota vence: é o único que a view não pode forjar — vem do `<int:...>` que o
    Django já converteu. POST antes de GET, e string vazia conta como ausente: `select` sem
    escolha manda o campo com valor vazio, que não é um id."""
    bruto = kwargs_da_rota.get(parametro)
    if bruto is not None:
        return str(bruto)
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
