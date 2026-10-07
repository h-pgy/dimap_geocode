"""
Testes de apps/unidades/extincao_tipo.py e de `tipos_unidade_disponiveis`, em
apps/unidades/consulta.py (SPEC user_admin/031): o ato data o tipo sem tocar em unidade alguma — o
tipo continua sendo avaliado, e só o cadastro de unidades (`tipos_unidade_disponiveis`) filtra o
extinto.

Chamam `extinguir_tipo_unidade`/`reativar_tipo_unidade` direto, e não pela rota: as quatro ações
são exclusivas do superusuário e sem alcance, e o contrato HTTP delas (segurança, registro, edição)
está em tests/apps/unidades/views/. Todos levam o marker `banco`.
"""

from datetime import date

import pytest

from apps.cargos.models import CargoBase, CargoComissao
from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao
from apps.unidades.consulta import tipos_unidade_disponiveis
from apps.unidades.extincao_tipo import extinguir_tipo_unidade, reativar_tipo_unidade
from apps.unidades.models import TipoUnidade, Unidade
from apps.unidades.titularidade import definir_titular
from apps.user_admin.models import Perfil

banco = pytest.mark.banco

HOJE = date(2026, 10, 7)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(nome: str, **overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {"nome": nome, "nivel": 10, "pode_ser_raiz": True, "nivel_minimo_titular": 1}
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(sigla: str, tipo: TipoUnidade, **overrides: object) -> Unidade:
    dados: dict[str, object] = {"nome": f"Unidade {sigla}", "sigla": sigla, "tipo": tipo}
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base(**overrides: object) -> CargoBase:
    dados: dict[str, object] = {"nome": "Cargo Base Extinção Tipo", "sigla": "CGBET"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _cargo_chefia(nome: str) -> CargoComissao:
    return CargoComissao.objects.create(nome=nome, sigla="CDA", nivel=1, e_chefia=True)


def _perfil(unidade: Unidade, rf: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": "Servidor",
        "sobrenome": "Extinção Tipo",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _disponiveis(tipo_atual_id: int | None = None) -> set[int]:
    return set(tipos_unidade_disponiveis(tipo_atual_id).values_list("pk", flat=True))


# ---------------------------------------------------------------------------
# O ato move a data e o cadastro de unidades segue a data
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_extinguir_data_o_tipo_e_o_tira_do_cadastro_de_unidades() -> None:
    tipo = _tipo_unidade("Tipo Extinguido")

    desfecho = extinguir_tipo_unidade(tipo, HOJE)

    assert desfecho.tipo is not None
    assert desfecho.tipo.extinto_em == HOJE
    assert tipo.pk not in _disponiveis()


@banco
@pytest.mark.django_db
def test_tipo_extinto_segue_ofertado_a_unidade_que_ja_o_possui() -> None:
    possuido = _tipo_unidade("Tipo Possuído Extinto")
    outro_extinto = _tipo_unidade("Outro Tipo Extinto")
    unidade = _unidade("TIPO-POSSUI", possuido)
    extinguir_tipo_unidade(possuido, HOJE)
    extinguir_tipo_unidade(outro_extinto, HOJE)

    disponiveis = _disponiveis(tipo_atual_id=unidade.tipo_id)

    assert possuido.pk in disponiveis
    assert outro_extinto.pk not in disponiveis


@banco
@pytest.mark.django_db
def test_reativar_devolve_o_tipo_ao_cadastro_de_unidades() -> None:
    tipo = _tipo_unidade("Tipo Reativado")
    extinguir_tipo_unidade(tipo, HOJE)

    desfecho = reativar_tipo_unidade(tipo)

    assert desfecho.tipo is not None
    assert desfecho.tipo.extinto_em is None
    assert tipo.pk in _disponiveis()


# ---------------------------------------------------------------------------
# Extinguir não toca em unidade: hierarquia, titular e competência seguem de pé
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_unidades_de_tipo_extinto_seguem_na_hierarquia_e_exercem_competencia() -> None:
    tipo_superior = _tipo_unidade("Tipo Superior Extinto", nivel=20)
    tipo_filha = _tipo_unidade("Tipo Filha Vigente", nivel=10, pode_ser_raiz=False)
    superior = _unidade("TIPO-SUP", tipo_superior)
    filha = _unidade("TIPO-FILHA", tipo_filha, pai=superior)
    titular = _perfil(superior, "9610000", cargo_comissao=_cargo_chefia("Diretor Tipo Extinto"))
    definir_titular(titular)
    lotado = _perfil(superior, "9610001", cargo_base=_cargo_base(nome="Cargo Concedido Tipo", sigla="CGCT"))
    acao, _ = Acao.objects.get_or_create(
        slug="competencias.definir_atribuicao",
        defaults={"nome": "Definir atribuição", "tooltip": "tt", "estrutural": False},
    )
    atribuicao = AtribuicaoUnidade.objects.create(unidade=superior, acao=acao)
    Concessao.objects.create(atribuicao=atribuicao, cargo_base=lotado.cargo_base)
    assert Perfil.objects.get(pk=lotado.pk).has_perm("competencias.definir_atribuicao")

    extinguir_tipo_unidade(tipo_superior, HOJE)

    superior = Unidade.objects.get(pk=superior.pk)
    filha = Unidade.objects.get(pk=filha.pk)
    assert superior.extinta_em is None
    assert superior.tipo.extinto is True
    # Subordinando e sendo subordinada: a hierarquia continua válida sob o tipo extinto.
    assert filha.pai_id == superior.pk
    superior.full_clean()
    filha.full_clean()
    assert superior.titular == titular
    assert Perfil.objects.get(pk=lotado.pk).has_perm("competencias.definir_atribuicao")
