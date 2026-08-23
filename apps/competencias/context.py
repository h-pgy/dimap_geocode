"""A composição da tela de atribuições (SPEC autorizacao/007) e da tela de conceder competência
(SPEC autorizacao/008): o alvo escolhido, o organograma recortado ao alcance e o que a unidade-alvo
já exerce — a segunda troca só o que está no poço e como cada atribuição se resume. Orquestração —
nenhuma regra de negócio."""

from collections.abc import Sequence
from typing import Any

from django.db.models import Count
from django.urls import reverse

from apps.competencias.atribuicao import cargos_que_perdem
from apps.competencias.catalogo import acoes_oferecidas
from apps.competencias.comandos import ComandoAtribuicao
from apps.competencias.consulta import ramos_do_alcance
from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao
from apps.unidades.context import contexto_organograma
from apps.unidades.models import Unidade
from apps.unidades.paleta import hex_da_cor
from apps.user_admin.models import CargoBase, CargoComissao, Perfil
from services.domain.arvore_hierarquica import NoHierarquia
from services.domain.autorizacao import VarianteIcone

DESCRICAO_SEM_CARGO = "nenhum cargo ainda"


def contexto_da_tela(perfil: Perfil, unidade_alvo: Unidade | None = None) -> dict[str, Any]:
    ramos = ramos_do_alcance(perfil)
    # O alvo inicial sai dos PRÓPRIOS ramos do perfil: por construção está dentro do alcance, e é
    # isso que o dispensa da conferência do decorator, que num GET sem parâmetro não roda.
    alvo = unidade_alvo or _primeira_dirigida(ramos)
    return (
        contexto_organograma(
            alvo,
            arvores=ramos,
            # Nesta tela o card escolhe o alvo: levar à página da unidade seria sair no meio do
            # ato, e chamar as irmãs não tem o que revelar — a linha do nível já vem aberta.
            com_link=False,
            com_irmas=False,
            abrir_o_ego=True,
        )
        | contexto_painel(alvo)
        | _rotas_do_seletor("competencias:painel_atribuicoes", "#painel-atribuicoes")
    )


def contexto_painel(
    unidade_alvo: Unidade | None, *, fechar_modal: bool = False
) -> dict[str, Any]:
    """O que `_painel_atribuicoes.html` consome sozinho — alvo do hx-get ao trocar de unidade na
    árvore, que não reenvia o organograma. `fechar_modal` fecha o catálogo/confirmação que a
    unidade anterior possa ter deixado aberto — só a troca de unidade o pede; a carga inicial da
    página nunca deve (Caveats de `contexto_poco`)."""
    return {
        "unidade_alvo": unidade_alvo,
        "subtitulo_alvo": _subtitulo_unidade(unidade_alvo) if unidade_alvo else "",
        "cor_alvo_hex": hex_da_cor(unidade_alvo.cor) if unidade_alvo else "",
    } | contexto_poco(unidade_alvo, fechar_modal=fechar_modal)


def contexto_poco(
    unidade_alvo: Unidade | None, *, fechar_modal: bool = False
) -> dict[str, Any]:
    """O que `_poco_atribuicoes.html` consome sozinho — alvo do swap de atribuir e remover.
    `fechar_modal` liga os checkboxes OOB que fecham `#modal-catalogo`/`#modal-remover`: só quando
    esta renderização É a resposta de um ato que precisa fechá-los — nunca na carga inicial da
    página, sob pena de dois elementos com o mesmo id (mesmo Caveat de `contexto_poco_concessoes`):
    o `label for` do botão Cancelar mira o primeiro da árvore, que não é o checkbox aberto, e o
    modal trava sem fechar nunca."""
    return {
        "unidade_alvo": unidade_alvo,
        "atribuicoes": _atribuicoes_de(unidade_alvo),
        "fechar_modal": fechar_modal,
    }


def contexto_catalogo(unidade_alvo: Unidade) -> dict[str, Any]:
    return {
        "unidade_alvo": unidade_alvo,
        "acoes": acoes_oferecidas(unidade_alvo),
        "variante_icone": VarianteIcone.GRANDE,
    }


def contexto_confirmar_remocao(comando: ComandoAtribuicao) -> dict[str, Any]:
    cargos = cargos_que_perdem(comando)
    return {
        "unidade_alvo": Unidade.objects.get(pk=comando.unidade_alvo_id),
        "acao": Acao.objects.get(slug=comando.acao_slug),
        "cargos": cargos,
        "resumo_cargos": _resumo_cargos(len(cargos)),
        "comando": comando,
    }


def contexto_da_tela_conceder(perfil: Perfil, unidade_alvo: Unidade | None = None) -> dict[str, Any]:
    """Mesmo alcance da SPEC 007 (Caveats): a unidade sem titular, ou sem direção, ficaria sem
    quem distribua as atribuições se o alvo partisse só da unidade do perfil."""
    ramos = ramos_do_alcance(perfil)
    alvo = unidade_alvo or _primeira_dirigida(ramos)
    return (
        contexto_organograma(
            alvo,
            arvores=ramos,
            com_link=False,
            com_irmas=False,
            abrir_o_ego=True,
        )
        | contexto_painel_concessoes(alvo)
        | _rotas_do_seletor("competencias:painel_concessoes", "#painel-concessoes")
    )


def contexto_painel_concessoes(
    unidade_alvo: Unidade | None, *, fechar_modal: bool = False
) -> dict[str, Any]:
    """O que `_painel_concessoes.html` consome sozinho — alvo do hx-get ao trocar de unidade na
    árvore, que não reenvia o organograma. `fechar_modal` fecha o de conceder que a unidade
    anterior possa ter deixado aberto — só a troca de unidade o pede; a carga inicial da página
    nunca deve, pois é ela quem primeiro grava o `#modal-conceder` (Caveats)."""
    return {
        "unidade_alvo": unidade_alvo,
        "subtitulo_alvo": _subtitulo_unidade(unidade_alvo) if unidade_alvo else "",
        "cor_alvo_hex": hex_da_cor(unidade_alvo.cor) if unidade_alvo else "",
    } | contexto_poco_concessoes(unidade_alvo, fechar_modal=fechar_modal)


def contexto_poco_concessoes(
    unidade_alvo: Unidade | None, *, fechar_modal: bool = False
) -> dict[str, Any]:
    """O que `_poco_concessoes.html` consome sozinho — alvo do swap de conceder e revogar.
    `fechar_modal` liga o checkbox OOB que fecha `#modal-conceder`: só quando esta renderização É
    a resposta de um ato que precisa fechá-lo — nunca na carga inicial da página, sob pena de dois
    elementos com o mesmo id (Caveats)."""
    return {
        "unidade_alvo": unidade_alvo,
        "atribuicoes": _atribuicoes_com_concessoes(unidade_alvo),
        "fechar_modal": fechar_modal,
    }


def contexto_modal_conceder(atribuicao: AtribuicaoUnidade) -> dict[str, Any]:
    return {
        "atribuicao": atribuicao,
        "unidade_alvo": atribuicao.unidade,
        "cargos_base": CargoBase.objects.order_by("nome"),
        "cargos_comissao": CargoComissao.objects.order_by("nome"),
    }


def _primeira_dirigida(ramos: Sequence[NoHierarquia]) -> Unidade | None:
    """Por sigla, e não pela ordem do conjunto: `unidades_dirigidas` não tem ordem, e a tela abriria
    numa unidade diferente a cada requisição. `None` é o perfil que tem a ação por concessão e não
    dirige nada — árvore vazia, e nada a atribuir."""
    return (
        Unidade.objects.filter(pk__in=[ramo.unidade_id for ramo in ramos])
        .order_by("sigla")
        .first()
    )


def _atribuicoes_de(unidade: Unidade | None) -> list[dict[str, Any]]:
    if unidade is None:
        return []
    atribuicoes = (
        AtribuicaoUnidade.objects.filter(unidade=unidade)
        .select_related("acao")
        .annotate(total_concessoes=Count("concessoes"))
        .order_by("acao__nome")
    )
    return [
        {
            "atribuicao": atribuicao,
            "acao": atribuicao.acao,
            "variante_icone": VarianteIcone.PEQUENO,
            "vazio": atribuicao.total_concessoes == 0,
            "descricao": _descricao_dos_cargos(atribuicao.total_concessoes),
        }
        for atribuicao in atribuicoes
    ]


def _atribuicoes_com_concessoes(unidade: Unidade | None) -> list[dict[str, Any]]:
    if unidade is None:
        return []
    atribuicoes = (
        AtribuicaoUnidade.objects.filter(unidade=unidade)
        .select_related("acao")
        .prefetch_related("concessoes__cargo_base", "concessoes__cargo_comissao")
        .order_by("acao__nome")
    )
    return [
        {
            "atribuicao": atribuicao,
            "acao": atribuicao.acao,
            "variante_icone": VarianteIcone.GRANDE,
            "concessoes": [
                {"concessao": concessao, "rotulo": _rotulo_cargo(concessao)}
                for concessao in atribuicao.concessoes.all()
            ],
        }
        for atribuicao in atribuicoes
    ]


def _rotulo_cargo(concessao: Concessao) -> str:
    if concessao.cargo_comissao is not None:
        return f"{concessao.cargo_comissao.padrao} · {concessao.cargo_comissao.nome}"
    return concessao.cargo_base.nome if concessao.cargo_base is not None else ""


def _rotas_do_seletor(url_name: str, alvo_painel: str) -> dict[str, Any]:
    """`_seletor_unidade_alvo.html` é compartilhado com a SPEC 007 (Caveats): a rota do hx-get e o
    alvo do swap variam por tela, e vêm daqui — não do partial, que não sabe qual delas o inclui."""
    return {"url_painel": reverse(url_name), "alvo_painel": alvo_painel}


def _descricao_dos_cargos(total: int) -> str:
    if total == 0:
        return DESCRICAO_SEM_CARGO
    return f"{total} cargo{'s' if total != 1 else ''} exerce{'m' if total != 1 else ''}"


def _resumo_cargos(total: int) -> str:
    verbo = "perde" if total == 1 else "perdem"
    return f"{total} cargo{'s' if total != 1 else ''} {verbo} esta competência junto com a atribuição."


def _subtitulo_unidade(unidade: Unidade) -> str:
    partes = [unidade.nome, unidade.tipo.nome]
    pai = unidade.pai
    if pai is not None:
        partes.append(f"subordinada à {pai.sigla}")
    return " · ".join(partes)
