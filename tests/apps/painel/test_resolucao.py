"""Testes de apps/painel/resolucao.py (SPEC painel/001): a cascata do painel — o item filtra pela
caneta (só o ato, nunca a view livre), o grupo some sem nenhum item visível, a aba some sem nenhum
grupo visível (salvo a básica), e a ordem declarada sobrevive nos três níveis.
"""

from django.urls import reverse

from apps.competencias.utils import instanciar_acao
from apps.painel.estrutura import (
    PARTIAL_CARTAO,
    Aba,
    ContratoPainel,
    Grupo,
    ItemAcao,
    ItemLivre,
)
from apps.painel.resolucao import MontagemPainel, ResolvedorPainel
from services.domain.autorizacao import VarianteIcone

# Rota sem argumento algum: âncora neutra para item livre que não precisa do perfil da sessão.
URL_NAME_NEUTRA = "core:home"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _item_acao(
    slug: str = "painel.acao_teste",
    url_name: str = URL_NAME_NEUTRA,
    partial: str | None = None,
    variante_icone: VarianteIcone = VarianteIcone.GRANDE,
) -> ItemAcao:
    acao_implementada = instanciar_acao(
        slug=slug,
        nome=f"Ação {slug}",
        tooltip="tt",
        url_name=url_name,
        partial="_ignorado.html",
        variantes_icone=frozenset({variante_icone}),
    )
    return ItemAcao(acao=acao_implementada, partial=partial, variante_icone=variante_icone)


def _item_livre(
    slug: str = "painel.item_teste",
    nome: str = "Item de Teste",
    tooltip: str = "tt",
    url_name: str = URL_NAME_NEUTRA,
    argumento_perfil: str | None = None,
    partial: str | None = None,
) -> ItemLivre:
    return ItemLivre(
        slug=slug,
        nome=nome,
        tooltip=tooltip,
        url_name=url_name,
        argumento_perfil=argumento_perfil,
        partial=partial,
    )


def _grupo(
    *itens: ItemAcao | ItemLivre,
    rotulo: str = "Grupo de Teste",
    partial_padrao: str = PARTIAL_CARTAO,
) -> Grupo:
    return Grupo(rotulo=rotulo, itens=itens, partial_padrao=partial_padrao)


def _aba(
    *,
    slug: str = "painel.aba_teste",
    rotulo: str = "Aba de Teste",
    titulo: str = "Aba de Teste",
    descricao: str = "descrição",
    itens_acima: tuple[ItemAcao | ItemLivre, ...] = (),
    grupos: tuple[Grupo, ...] = (),
    itens_abaixo: tuple[ItemAcao | ItemLivre, ...] = (),
    basica: bool = False,
) -> Aba:
    return Aba(
        slug=slug,
        rotulo=rotulo,
        titulo=titulo,
        descricao=descricao,
        itens_acima=itens_acima,
        grupos=grupos,
        itens_abaixo=itens_abaixo,
        basica=basica,
    )


def _montagem(
    *abas: Aba,
    slugs_liberados: frozenset[str] = frozenset(),
    perfil_id: int = 1,
) -> MontagemPainel:
    return MontagemPainel(
        painel=ContratoPainel(abas=abas),
        slugs_liberados=slugs_liberados,
        perfil_id=perfil_id,
    )


# ---------------------------------------------------------------------------
# O grupo mistura as duas naturezas; só o ato passa pela caneta
# ---------------------------------------------------------------------------


def test_grupo_mistura_ato_filtrado_e_view_livre() -> None:
    grupo = _grupo(
        _item_acao(slug="painel.ato_sem_caneta"),
        _item_livre(slug="painel.livre_sempre"),
    )
    aba = _aba(grupos=(grupo,))

    resolvido = ResolvedorPainel()(_montagem(aba, slugs_liberados=frozenset()))

    (aba_resolvida,) = resolvido.abas
    (grupo_resolvido,) = aba_resolvida.grupos
    assert [item.slug for item in grupo_resolvido.itens] == ["painel.livre_sempre"]


# ---------------------------------------------------------------------------
# O que fica vazio some: grupo, depois aba
# ---------------------------------------------------------------------------


def test_grupo_sem_item_visivel_nao_entra_no_painel() -> None:
    grupo_vazio = _grupo(_item_acao(slug="painel.ato_sem_caneta"))
    # basica=True: o alvo deste teste é o GRUPO desaparecer, não a aba — que uma aba comum some
    # junto quando fica sem grupo algum é o que `test_aba_sem_grupo_visivel_nao_entra_no_painel`
    # fixa.
    aba = _aba(grupos=(grupo_vazio,), basica=True)

    resolvido = ResolvedorPainel()(_montagem(aba, slugs_liberados=frozenset()))

    (aba_resolvida,) = resolvido.abas
    assert aba_resolvida.grupos == ()


def test_aba_sem_grupo_visivel_nao_entra_no_painel() -> None:
    aba = _aba(
        grupos=(
            _grupo(_item_acao(slug="painel.ato_um")),
            _grupo(_item_acao(slug="painel.ato_dois")),
        ),
    )

    resolvido = ResolvedorPainel()(_montagem(aba, slugs_liberados=frozenset()))

    assert resolvido.abas == ()


def test_aba_basica_entra_sem_caneta_alguma() -> None:
    aba = _aba(
        basica=True,
        grupos=(
            _grupo(_item_livre(slug="painel.dados"), rotulo="Meus dados"),
            _grupo(_item_livre(slug="painel.senha"), rotulo="Senha"),
        ),
        itens_abaixo=(_item_livre(slug="painel.sair", nome="Encerrar sessão"),),
    )

    resolvido = ResolvedorPainel()(_montagem(aba, slugs_liberados=frozenset()))

    (aba_resolvida,) = resolvido.abas
    assert [grupo.rotulo for grupo in aba_resolvida.grupos] == ["Meus dados", "Senha"]
    assert [item.slug for item in aba_resolvida.itens_abaixo] == ["painel.sair"]


# ---------------------------------------------------------------------------
# Ordem declarada preservada nos três níveis
# ---------------------------------------------------------------------------


def test_ordem_declarada_preservada_em_abas_grupos_e_itens() -> None:
    aba_a = _aba(
        slug="painel.aba_a",
        grupos=(
            _grupo(
                _item_livre(slug="painel.a1"),
                _item_livre(slug="painel.a2"),
                rotulo="Grupo A",
            ),
        ),
        basica=True,
    )
    aba_b = _aba(
        slug="painel.aba_b",
        grupos=(_grupo(_item_livre(slug="painel.b1"), rotulo="Grupo B"),),
        basica=True,
    )

    resolvido = ResolvedorPainel()(_montagem(aba_a, aba_b, slugs_liberados=frozenset()))

    assert [aba.slug for aba in resolvido.abas] == ["painel.aba_a", "painel.aba_b"]
    (grupo_a,) = resolvido.abas[0].grupos
    assert [item.slug for item in grupo_a.itens] == ["painel.a1", "painel.a2"]


# ---------------------------------------------------------------------------
# O template do item é o do continente, salvo o que declara o seu
# ---------------------------------------------------------------------------


def test_item_usa_partial_do_continente_e_o_proprio_quando_declara() -> None:
    partial_do_grupo = "painel/partials/_card_do_grupo.html"
    grupo = _grupo(
        _item_livre(slug="painel.sem_partial_proprio"),
        _item_livre(slug="painel.com_partial_proprio", partial="painel/partials/_botao_sair.html"),
        partial_padrao=partial_do_grupo,
    )
    aba = _aba(grupos=(grupo,))

    resolvido = ResolvedorPainel()(_montagem(aba, slugs_liberados=frozenset()))

    (grupo_resolvido,) = resolvido.abas[0].grupos
    herdado, proprio = grupo_resolvido.itens
    assert herdado.partial == partial_do_grupo
    assert proprio.partial == "painel/partials/_botao_sair.html"


# ---------------------------------------------------------------------------
# Item fora de qualquer grupo passa pelo mesmo filtro
# ---------------------------------------------------------------------------


def test_item_avulso_resolve_fora_dos_grupos_e_passa_pelo_mesmo_filtro() -> None:
    aba = _aba(
        itens_acima=(
            _item_livre(slug="painel.avulso_acima"),
            _item_acao(slug="painel.ato_avulso_sem_caneta"),
        ),
        itens_abaixo=(_item_livre(slug="painel.avulso_abaixo"),),
    )

    resolvido = ResolvedorPainel()(_montagem(aba, slugs_liberados=frozenset()))

    (aba_resolvida,) = resolvido.abas
    assert [item.slug for item in aba_resolvida.itens_acima] == ["painel.avulso_acima"]
    assert [item.slug for item in aba_resolvida.itens_abaixo] == ["painel.avulso_abaixo"]


# ---------------------------------------------------------------------------
# Item livre com argumento resolve a URL com o perfil da sessão
# ---------------------------------------------------------------------------


def test_item_livre_com_argumento_resolve_url_com_o_perfil_da_sessao() -> None:
    aba = _aba(
        itens_acima=(
            _item_livre(
                slug="painel.meus_dados",
                url_name="user_admin:pagina_perfil",
                argumento_perfil="pk",
            ),
            _item_livre(slug="painel.sem_argumento", url_name=URL_NAME_NEUTRA),
        ),
    )

    resolvido = ResolvedorPainel()(_montagem(aba, slugs_liberados=frozenset(), perfil_id=42))

    com_argumento, sem_argumento = resolvido.abas[0].itens_acima
    assert com_argumento.url == reverse("user_admin:pagina_perfil", kwargs={"pk": 42})
    assert sem_argumento.url == reverse(URL_NAME_NEUTRA)
