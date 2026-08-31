"""Testes de apps/competencias/resolucao.py (SPEC autorizacao/005): a borda entre o request e o
router — resolve o conjunto de slugs liberados ao perfil, com o atalho do superusuário que o
`PermissionsMixin.get_all_permissions` não cobre (só `has_perm` enumera tudo para ele).
"""

from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

import pytest

from apps.competencias.protecao import pode_executar
from apps.competencias.resolucao import slugs_liberados
from apps.competencias.schemas import RegistroAcoes
from apps.competencias.utils import instanciar_acao
from apps.painel.estrutura import Aba, ContratoPainel, Grupo, ItemAcao, ItemLivre
from apps.painel.resolucao import MontagemPainel, ResolvedorPainel
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import CargoBase, Perfil
from services.domain.autorizacao import VarianteIcone

banco = pytest.mark.banco


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _tipo_unidade(**overrides: object) -> TipoUnidade:
    dados: dict[str, object] = {
        "nome": "Divisão Resolução",
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


def _perfil(unidade: Unidade, rf: str, nome: str, **overrides: object) -> Perfil:
    dados: dict[str, object] = {
        "rf": rf,
        "nome": nome,
        "sobrenome": "Resolução",
        "cargo_base": CargoBase.objects.create(nome="Cargo Resolução", sigla="CGRS"),
        "unidade": unidade,
    }
    dados.update(overrides)
    perfil = Perfil(**dados)  # type: ignore[arg-type]
    perfil.set_password("segredo123")
    perfil.save()
    return perfil


def _registro(*slugs: str) -> RegistroAcoes:
    return RegistroAcoes(
        acoes=tuple(
            instanciar_acao(
                slug=slug,
                nome=slug,
                tooltip="tt",
                url_name="core:home",
            )
            for slug in slugs
        )
    )


# ---------------------------------------------------------------------------
# Superusuário recebe o registro inteiro; anônimo, nada
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_resolvedor_libera_o_catalogo_inteiro_para_superusuario(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "apps.competencias.resolucao.REGISTRO",
        _registro("menus.acao_um", "menus.acao_dois"),
    )
    superusuario = _perfil(_unidade("URESO"), "900900", "Super", is_superuser=True)

    assert slugs_liberados(superusuario) == frozenset(
        {"menus.acao_um", "menus.acao_dois"}
    )
    assert slugs_liberados(AnonymousUser()) == frozenset()


# ---------------------------------------------------------------------------
# Exonerado não enxerga ação alguma — nem o superusuário (SPEC user_admin/027)
# ---------------------------------------------------------------------------


@banco
@pytest.mark.django_db
def test_exonerado_nao_enxerga_acao_alguma() -> None:
    exonerado = _perfil(
        _unidade("URESO-EXON"),
        "900910",
        "Exonerado",
        is_superuser=True,
        is_active=False,
        exonerado_em=timezone.localdate(),
    )
    acao = instanciar_acao(
        slug="menus.acao_exonerado_teste",
        nome="Ação de Teste",
        tooltip="tt",
        url_name="core:home",
        # ItemAcao usa a variante grande por padrão, e recusa a ação que não a declara.
        variantes_icone=frozenset({VarianteIcone.GRANDE}),
    )

    assert slugs_liberados(exonerado) == frozenset()
    assert pode_executar(exonerado, acao) is False

    # O painel dele resolve sem card de ação nenhum; o item livre continua de pé — ele não é ato.
    aba = Aba(
        slug="painel.aba_exonerado_teste",
        rotulo="Aba",
        titulo="Aba",
        descricao="descrição",
        grupos=(
            Grupo(
                rotulo="Grupo",
                itens=(
                    ItemAcao(acao=acao),
                    ItemLivre(
                        slug="painel.livre_exonerado_teste",
                        nome="Livre",
                        tooltip="tt",
                        url_name="core:home",
                    ),
                ),
            ),
        ),
    )
    resolvido = ResolvedorPainel()(
        MontagemPainel(
            painel=ContratoPainel(abas=(aba,)),
            slugs_liberados=slugs_liberados(exonerado),
            perfil_id=exonerado.pk,
        )
    )

    (aba_resolvida,) = resolvido.abas
    (grupo_resolvido,) = aba_resolvida.grupos
    assert [item.slug for item in grupo_resolvido.itens] == [
        "painel.livre_exonerado_teste"
    ]
