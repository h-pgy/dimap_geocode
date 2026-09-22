"""Testes de apps/acoes_lote/views.py (SPEC certidao_lancamento/001):
o router de ações do lote localizado — enforcement de SQL e ID válidos na borda,
e restrição de oferta das ações do lote por competência de perfil.
"""

from itertools import count

from django.test import Client
from django.urls import reverse
import pytest

from apps.cargos.models import CargoBase
from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil

banco = pytest.mark.banco
SLUG_ACAO = "certidao_lancamento.emitir"
_SIGLAS = count(300)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(nome: str = "Tipo Ações Lote") -> TipoUnidade:
    return TipoUnidade.objects.create(
        nome=nome,
        nivel=10,
        pode_ser_raiz=True,
        nivel_minimo_titular=1,
    )


def _unidade(sigla: str = "LOTE-1") -> Unidade:
    return Unidade.objects.create(
        nome=f"Unidade {sigla}",
        sigla=sigla,
        tipo=_tipo_unidade(f"Tipo {sigla}"),
    )


def _cargo_base(nome: str = "Auditor Fiscal") -> CargoBase:
    num = next(_SIGLAS)
    return CargoBase.objects.create(nome=f"{nome} {num}", sigla=f"AF{num}")


def _perfil(unidade: Unidade, rf: str = "880001", nome: str = "Servidor") -> Perfil:
    perfil = Perfil(
        rf=rf,
        nome=nome,
        sobrenome="Lote",
        cargo_base=_cargo_base(),
        unidade=unidade,
    )
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _acao(slug: str = SLUG_ACAO) -> Acao:
    return Acao.objects.create(
        slug=slug,
        nome="Emitir certidão de existência de lançamento",
        tooltip="Emite o PDF selado que atesta o lançamento do IPTU do lote.",
        ativa=True,
    )


def _atribuir(unidade: Unidade, acao: Acao) -> AtribuicaoUnidade:
    return AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)


def _conceder(atribuicao: AtribuicaoUnidade, cargo_base: CargoBase) -> Concessao:
    return Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo_base)


def _url_router() -> str:
    return reverse("acoes_lote:acoes")


# ---------------------------------------------------------------------------
# Testes do router de ações do lote (SPEC 001 §8)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_poco_de_acoes_lote_so_para_quem_tem_concessao_e_sql_valido(client: Client) -> None:
    unidade = _unidade("LOTE-POCO")
    user_sem_concessao = _perfil(unidade, rf="880010", nome="Sem Concessao")
    user_com_concessao = _perfil(unidade, rf="880011", nome="Com Concessao")

    acao = _acao(SLUG_ACAO)
    atribuicao = _atribuir(unidade, acao)
    _conceder(atribuicao, user_com_concessao.cargo_base)

    sql_valido = "005.003.0048-5"
    id_poligono = "1001"
    params = {"sql": sql_valido, "id": id_poligono}

    # Anônimo recebe o poço vazio
    resposta_anonimo = client.get(_url_router(), params)
    assert resposta_anonimo.status_code == 200
    assert "Certidão de lançamento" not in resposta_anonimo.content.decode()

    # Autenticado sem concessão recebe o poço vazio
    client.force_login(user_sem_concessao)
    resposta_sem = client.get(_url_router(), params)
    assert resposta_sem.status_code == 200
    assert "Certidão de lançamento" not in resposta_sem.content.decode()

    # Autenticado com concessão e SQL válido: botão aponta para o modal com id e sql
    client.force_login(user_com_concessao)
    resposta_com = client.get(_url_router(), params)
    assert resposta_com.status_code == 200
    corpo = resposta_com.content.decode()
    assert "Certidão de lançamento" in corpo
    assert f"id={id_poligono}" in corpo
    assert f"sql={sql_valido}" in corpo
    assert 'hx-target="#poco-modal"' in corpo


@banco
@pytest.mark.django_db
def test_router_acoes_lote_recusa_sql_invalido_ou_ausente(client: Client) -> None:
    unidade = _unidade("LOTE-RECUSA")
    user = _perfil(unidade, rf="880020", nome="Autorizado")
    acao = _acao(SLUG_ACAO)
    atribuicao = _atribuir(unidade, acao)
    _conceder(atribuicao, user.cargo_base)

    client.force_login(user)

    casos_invalidos: tuple[dict[str, str], ...] = (
        {"id": "1001"},  # sem SQL
        {"sql": "", "id": "1001"},  # SQL vazio
        {"sql": "00500300485", "id": "1001"},  # sem pontos/traço
        {"sql": "abc.def.ghij-k", "id": "1001"},  # com letras
        {"sql": "005.003", "id": "1001"},  # incompleto
        {"sql": "005.003.0048-5"},  # sem id
        {"sql": "005.003.0048-5", "id": "abc"},  # id não numérico
        {},  # sem parâmetros
    )
    for params in casos_invalidos:
        resposta = client.get(_url_router(), params)
        assert resposta.status_code == 200
        assert resposta.content.strip() == b""
