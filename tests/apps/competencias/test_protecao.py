"""Testes de apps/competencias/protecao.py (SPEC autorizacao/004): a barreira de autorização,
a conferência do alvo contra o alcance declarado e o registro da execução — negada ou não —, no
mesmo decorator que protege toda rota de ação.

Não há rota de ação real ainda: as views usadas aqui são dummies, decoradas com `acao_protegida`
e chamadas diretamente via `RequestFactory` — `_chamar` fecha o mesmo laço que o middleware de
exceção do Django fecharia numa rota de verdade, convertendo `PermissionDenied`/`BadRequest` em
resposta HTTP com o status code certo.

Todos levam o marker `banco`: a autorização é resolvida contra concessão e titularidade gravadas.
"""

from collections.abc import Callable
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.handlers.exception import response_for_exception
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory
from django.utils import timezone

import pytest

from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao, ExecucaoAcao
from apps.competencias.protecao import acao_protegida, registrar_ato
from apps.competencias.registro import REGISTRO
from apps.competencias.schemas import AcaoImplementada, RegistroAcoes
from apps.user_admin.exercicio import designar_substituto, registrar_impedimento
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, CargoComissao, Perfil, TipoImpedimento
from apps.user_admin.schemas import NovaSubstituicao, NovoImpedimento
from apps.unidades.titularidade import definir_titular
from services.domain.autorizacao import Acao as AcaoDominio
from services.domain.autorizacao import TipoAlcance, UnidadesSubordinadas

banco = pytest.mark.banco

SLUG_SIMPLES = "competencias.protecao_simples"
SLUG_COM_ALCANCE = "competencias.protecao_alcance"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Proteção",
        "nivel": 10,
        "pode_ser_raiz": True,
        "nivel_minimo_titular": 1,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(sigla: str, **overrides: object) -> Unidade:
    dados: dict[str, object] = {
        "nome": f"Divisão {sigla}",
        "sigla": sigla,
        "tipo": _tipo_unidade(nome=f"Tipo {sigla}"),
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base(**overrides: object) -> CargoBase:
    dados: dict[str, object] = {"nome": "Cargo Proteção", "sigla": "CGPT"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _cargo_chefia(nome: str, nivel: int) -> CargoComissao:
    return CargoComissao.objects.create(
        nome=nome, sigla="CDA", nivel=nivel, e_chefia=True
    )


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Proteção",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _fresco(perfil: Perfil) -> Perfil:
    # Recarrega do banco: o cache de `has_perm` é do objeto Python, e cada requisição simulada
    # precisa ver o efeito de mudanças de estado como uma requisição nova veria.
    return Perfil.objects.get(pk=perfil.pk)


def _conceder(
    unidade: Unidade,
    slug: str,
    cargo_base: CargoBase | None = None,
    cargo_comissao: CargoComissao | None = None,
) -> None:
    acao, _ = Acao.objects.get_or_create(
        slug=slug, defaults={"nome": "Ação Proteção", "tooltip": "tt"}
    )
    atribuicao = AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)
    Concessao.objects.create(
        atribuicao=atribuicao, cargo_base=cargo_base, cargo_comissao=cargo_comissao
    )


def _acao_implementada(
    slug: str,
    alcance: TipoAlcance | None = None,
    estrutural: bool = False,
) -> AcaoImplementada:
    return AcaoImplementada(
        acao=AcaoDominio(
            slug=slug,
            nome="Ação de Proteção",
            tooltip="tt",
            alcance=alcance,
            estrutural=estrutural,
        ),
        url_name="competencias:protecao_teste",
    )


def _post(
    perfil: Perfil | AnonymousUser, dados: dict[str, str] | None = None
) -> HttpRequest:
    request = RequestFactory().post("/protecao-teste/", dados or {})
    request.user = perfil
    return request


def _get(
    perfil: Perfil | AnonymousUser, dados: dict[str, str] | None = None
) -> HttpRequest:
    request = RequestFactory().get("/protecao-teste/", dados or {})
    request.user = perfil
    return request


def _chamar(
    view: Callable[[HttpRequest], HttpResponse], request: HttpRequest
) -> HttpResponse:
    try:
        return view(request)
    except Exception as exc:
        return response_for_exception(request, exc)


# ---------------------------------------------------------------------------
# Views dummy — nenhuma rota de ação existe ainda; só o que exercita o decorator
# ---------------------------------------------------------------------------

_ACAO_SIMPLES = _acao_implementada(SLUG_SIMPLES)
_ACAO_COM_ALCANCE = _acao_implementada(
    SLUG_COM_ALCANCE, alcance=UnidadesSubordinadas(), estrutural=True
)


@acao_protegida(_ACAO_SIMPLES)
def _view_simples(request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok")


@acao_protegida(_ACAO_SIMPLES)
def _view_que_registra(request: HttpRequest) -> HttpResponse:
    registrar_ato(
        request,
        operacao=request.POST.get("operacao", ""),
        alvo_tipo=request.POST.get("alvo_tipo", ""),
        alvo_identificador=request.POST.get("alvo_identificador", ""),
    )
    return HttpResponse("ok")


@acao_protegida(_ACAO_COM_ALCANCE)
def _view_com_alcance(request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok")


# ---------------------------------------------------------------------------
# Conferência do alvo declarado (alcance)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_rota_confere_o_alvo_declarado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "apps.competencias.consulta.REGISTRO",
        RegistroAcoes(acoes=(*REGISTRO.todas(), _ACAO_COM_ALCANCE)),
    )
    raiz = _unidade("PROT-RAIZ")
    subordinada = _unidade("PROT-SUB", pai=raiz)
    fora_do_alcance = _unidade("PROT-FORA")
    titular = _perfil(
        raiz,
        "900800",
        "Titular",
        cargo_comissao=_cargo_chefia("Diretor Proteção", nivel=1),
    )
    definir_titular(titular)

    # Alvo dentro da subárvore dirigida: autorizado.
    resposta = _chamar(
        _view_com_alcance, _post(_fresco(titular), {"unidade": str(subordinada.pk)})
    )
    assert resposta.status_code == 200

    # Alvo fora da subárvore dirigida: 403 e linha de negativa.
    resposta = _chamar(
        _view_com_alcance, _post(_fresco(titular), {"unidade": str(fora_do_alcance.pk)})
    )
    assert resposta.status_code == 403
    assert ExecucaoAcao.objects.filter(autorizado=False).count() == 1

    # Requisição que altera estado sem o parâmetro do alvo: 400, sem linha nova.
    antes = ExecucaoAcao.objects.count()
    resposta = _chamar(_view_com_alcance, _post(_fresco(titular), {}))
    assert resposta.status_code == 400
    assert ExecucaoAcao.objects.count() == antes

    # Leitura sem alvo escolhido abre normalmente.
    resposta = _chamar(_view_com_alcance, _get(_fresco(titular)))
    assert resposta.status_code == 200


# ---------------------------------------------------------------------------
# Barreira de competência
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_rota_nega_autenticado_sem_competencia_com_403() -> None:
    unidade = _unidade("PROT-403")
    perfil = _perfil(unidade, "900801", "Sem Competência")

    resposta = _chamar(_view_simples, _get(_fresco(perfil)))

    assert resposta.status_code == 403


@banco
@pytest.mark.django_db
def test_rota_manda_anonimo_para_o_login() -> None:
    resposta = _chamar(_view_simples, _get(AnonymousUser()))

    assert resposta.status_code == 302
    assert resposta["Location"].startswith(str(settings.LOGIN_URL))
    assert ExecucaoAcao.objects.count() == 0


# ---------------------------------------------------------------------------
# Registro da execução autorizada
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_execucao_autorizada_fica_registrada_com_a_lotacao_do_momento() -> None:
    unidade_origem = _unidade("PROT-ORIG")
    unidade_destino = _unidade("PROT-DEST")
    cargo = _cargo_base()
    perfil = _perfil(unidade_origem, "900802", "Fulano", cargo_base=cargo)
    _conceder(unidade_origem, SLUG_SIMPLES, cargo_base=cargo)

    resposta = _chamar(_view_simples, _post(_fresco(perfil)))
    assert resposta.status_code == 200

    execucao = ExecucaoAcao.objects.get()
    assert execucao.perfil_id == perfil.pk
    assert execucao.unidade_id == unidade_origem.pk
    assert execucao.cargo_base_id == cargo.pk
    assert execucao.autorizado is True

    perfil.unidade = unidade_destino
    perfil.save(update_fields=["unidade"])
    execucao.refresh_from_db()
    assert execucao.unidade_id == unidade_origem.pk


@banco
@pytest.mark.django_db
def test_ato_praticado_em_substituicao_diz_por_quem_responde() -> None:
    unidade_titular = _unidade("PROT-SUBST-A")
    unidade_substituto = _unidade("PROT-SUBST-B")
    cargo_titular = _cargo_chefia("Diretor Proteção Substituição", nivel=1)
    titular = _perfil(
        unidade_titular, "900803", "Titular", cargo_comissao=cargo_titular
    )
    definir_titular(titular)
    substituto = _perfil(unidade_substituto, "900804", "Substituto")
    _conceder(unidade_substituto, SLUG_SIMPLES, cargo_base=substituto.cargo_base)

    # Por competência própria: ninguém coberto, campo vazio.
    resposta = _chamar(_view_simples, _post(_fresco(substituto)))
    assert resposta.status_code == 200
    primeira = ExecucaoAcao.objects.get()
    assert primeira.substituindo_id is None

    _conceder(unidade_titular, SLUG_SIMPLES, cargo_comissao=cargo_titular)
    tipo_impedimento = TipoImpedimento.objects.create(nome="Licença Proteção")
    hoje = timezone.localdate()
    impedimento = registrar_impedimento(
        titular,
        NovoImpedimento(
            tipo=tipo_impedimento.pk,
            data_inicio=hoje - timedelta(days=1),
            data_fim=None,
        ),
    )
    designar_substituto(
        impedimento,
        NovaSubstituicao(substituto=substituto.pk, data_inicio=hoje, data_fim=None),
    )

    # Cobrindo o titular: o registro diz por quem o autor respondia.
    resposta = _chamar(_view_simples, _post(_fresco(substituto)))
    assert resposta.status_code == 200
    segunda = ExecucaoAcao.objects.exclude(pk=primeira.pk).get()
    assert segunda.perfil_id == substituto.pk
    assert segunda.substituindo_id == titular.pk


# ---------------------------------------------------------------------------
# Registro da tentativa negada, e só ela em leitura
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_tentativa_negada_fica_registrada() -> None:
    unidade = _unidade("PROT-NEGA")
    perfil = _perfil(unidade, "900805", "Sem Competência Registro")

    resposta = _chamar(_view_simples, _get(_fresco(perfil)))

    assert resposta.status_code == 403
    execucao = ExecucaoAcao.objects.get()
    assert execucao.autorizado is False


@banco
@pytest.mark.django_db
def test_leitura_autorizada_nao_vira_registro() -> None:
    unidade = _unidade("PROT-LEITURA")
    cargo = _cargo_base()
    autorizado = _perfil(unidade, "900806", "Autorizado", cargo_base=cargo)
    _conceder(unidade, SLUG_SIMPLES, cargo_base=cargo)
    # Cargo distinto: o default de _perfil() reusaria o MESMO CargoBase de `autorizado`
    # (_cargo_base() é get_or_create por nome+sigla fixos) e concederia a ele por acidente.
    negado = _perfil(
        unidade, "900807", "Negado", cargo_base=_cargo_base(nome="Outro Cargo", sigla="OUTR")
    )

    resposta = _chamar(_view_simples, _get(_fresco(autorizado)))
    assert resposta.status_code == 200
    assert ExecucaoAcao.objects.count() == 0

    resposta = _chamar(_view_simples, _get(_fresco(negado)))
    assert resposta.status_code == 403
    assert ExecucaoAcao.objects.count() == 1


# ---------------------------------------------------------------------------
# O que a view acrescenta ao registro
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_operacoes_opostas_ficam_distinguiveis() -> None:
    unidade = _unidade("PROT-OPOSTAS")
    cargo = _cargo_base()
    perfil = _perfil(unidade, "900808", "Duas Operações", cargo_base=cargo)
    _conceder(unidade, SLUG_SIMPLES, cargo_base=cargo)

    _chamar(_view_que_registra, _post(_fresco(perfil), {"operacao": "atribuir"}))
    _chamar(_view_que_registra, _post(_fresco(perfil), {"operacao": "remover"}))

    operacoes = set(ExecucaoAcao.objects.values_list("operacao", flat=True))
    assert operacoes == {"atribuir", "remover"}


@banco
@pytest.mark.django_db
def test_alvo_e_opcional_no_registro() -> None:
    unidade = _unidade("PROT-ALVO")
    cargo = _cargo_base()
    perfil = _perfil(unidade, "900809", "Alvo Opcional", cargo_base=cargo)
    _conceder(unidade, SLUG_SIMPLES, cargo_base=cargo)

    _chamar(
        _view_que_registra,
        _post(
            _fresco(perfil),
            {
                "operacao": "atribuir",
                "alvo_tipo": "unidade_acao",
                "alvo_identificador": "X:Y",
            },
        ),
    )
    _chamar(_view_simples, _post(_fresco(perfil)))

    com_alvo = ExecucaoAcao.objects.get(alvo_identificador="X:Y")
    assert com_alvo.alvo_tipo == "unidade_acao"

    sem_alvo = ExecucaoAcao.objects.exclude(pk=com_alvo.pk).get()
    assert sem_alvo.alvo_tipo == ""
    assert sem_alvo.alvo_identificador == ""
