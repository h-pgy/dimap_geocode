"""
Testes de apps/unidades/views.py — `criar_unidade_raiz` e `gravar_unidade_raiz` (SPEC
user_admin/020, v3): ato próprio, exclusivo do superusuário. Não é estrutural (dirigir unidade não
dá esta caneta) nem concessão (que ela recusa mesmo gravada) — é a terceira resposta que o contrato
dá a "quem exerce" (`exclusiva_superusuario`), e por isso não entra em `slugs_liberados` de ninguém
além do superusuário. A rota não tem alcance: a raiz não pende de unidade alguma.

Todos levam o marker `banco`.
"""

from django.test import Client
from django.urls import reverse

import pytest

from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao, ExecucaoAcao
from apps.unidades.models import CorUnidade, TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, Perfil

banco = pytest.mark.banco

SLUG_ACAO = "unidades.criar_unidade_raiz"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Tipo Criar Unidade Raiz",
        "nivel": 30,
        "pode_ser_raiz": True,
        "nivel_minimo_titular": 1,
    }
    dados.update(overrides)
    return TipoUnidade.objects.create(**dados)  # type: ignore[arg-type]


def _unidade(sigla: str, **overrides: object) -> Unidade:
    dados: dict[str, object] = {
        "nome": f"Unidade {sigla}",
        "sigla": sigla,
        "tipo": _tipo_unidade(nome=f"Tipo {sigla}"),
    }
    dados.update(overrides)
    return Unidade.objects.create(**dados)  # type: ignore[arg-type]


def _cargo_base(**overrides: object) -> CargoBase:
    dados: dict[str, object] = {"nome": "Cargo Criar Unidade Raiz", "sigla": "CGCR"}
    dados.update(overrides)
    cargo, _ = CargoBase.objects.get_or_create(**dados)  # type: ignore[arg-type]
    return cargo


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Criar Unidade Raiz",
        "cargo_base": _cargo_base(),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _superusuario(rf: str) -> Perfil:
    return Perfil.objects.create_superuser(
        rf=rf,
        nome="Super",
        sobrenome="Usuário",
        password="segredo123",
        unidade=_unidade(f"CUR-SU-{rf}"),
        cargo_base=_cargo_base(),
    )


def _conceder(unidade: Unidade, cargo_base: CargoBase) -> Acao:
    # Ação NÃO estrutural — projeta exatamente como o contrato a declara (§3 da SPEC): a
    # exclusividade não é projetada, mas a concessão gravada existe para provar que ela não basta.
    acao, _ = Acao.objects.get_or_create(
        slug=SLUG_ACAO,
        defaults={"nome": "Criar unidade raiz", "tooltip": "tt", "estrutural": False},
    )
    atribuicao = AtribuicaoUnidade.objects.create(unidade=unidade, acao=acao)
    Concessao.objects.create(atribuicao=atribuicao, cargo_base=cargo_base)
    return acao


def _url_abrir() -> str:
    return reverse("unidades:criar_unidade_raiz")


def _url_gravar() -> str:
    return reverse("unidades:gravar_unidade_raiz")


# ---------------------------------------------------------------------------
# Exclusividade do superusuário — nem com a concessão gravada
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_criar_raiz_so_o_superusuario_exerce(client: Client) -> None:
    tipo_raiz = _tipo_unidade(nome="Tipo Raiz CUR")
    superusuario = _superusuario("9801000")

    client.force_login(superusuario)
    resposta = client.post(
        _url_gravar(),
        {
            "nome": "Secretaria Nova",
            "sigla": "CUR-NOVA",
            "tipo": str(tipo_raiz.pk),
            "cor": str(CorUnidade.AGUA_700),
        },
    )

    assert resposta.status_code == 200
    nova = Unidade.objects.get(sigla="CUR-NOVA")
    assert nova.pai_id is None
    execucao = ExecucaoAcao.objects.get(alvo_identificador="CUR-NOVA")
    assert execucao.operacao == "criar_raiz"

    # Quem não é superusuário não vê nem executa — mesmo com a concessão gravada para o slug.
    unidade = _unidade("CUR-NAO-SU")
    cargo = _cargo_base(nome="Cargo Concessão Raiz", sigla="CCR")
    perfil = _perfil(unidade, "9801010", "Concessão Raiz", cargo_base=cargo)
    _conceder(unidade, cargo)

    client.force_login(perfil)
    assert perfil.has_perm(SLUG_ACAO) is False
    resposta_negada = client.get(_url_abrir())
    assert resposta_negada.status_code == 403
    execucao_negada = ExecucaoAcao.objects.get(autorizado=False)
    assert execucao_negada.perfil_id == perfil.pk


# ---------------------------------------------------------------------------
# O pai é imposto pela rota — POST forjado não escapa disso
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_gravar_raiz_ignora_o_pai_forjado(client: Client) -> None:
    tipo_raiz = _tipo_unidade(nome="Tipo Raiz Forjado")
    outra = _unidade("CUR-FORJA-OUTRA")
    superusuario = _superusuario("9801100")

    client.force_login(superusuario)
    resposta = client.post(
        _url_gravar(),
        {
            "nome": "Unidade Forjada",
            "sigla": "CUR-FORJADA",
            "tipo": str(tipo_raiz.pk),
            "pai": str(outra.pk),
            "cor": str(CorUnidade.AGUA_700),
        },
    )

    assert resposta.status_code == 200
    nova = Unidade.objects.get(sigla="CUR-FORJADA")
    assert nova.pai_id is None
