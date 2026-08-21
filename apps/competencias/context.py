"""A composição da tela de atribuições (SPEC autorizacao/007): o alvo escolhido, o organograma
recortado ao alcance e o que a unidade-alvo já exerce. Orquestração — nenhuma regra de negócio."""

from collections.abc import Sequence
from typing import Any

from django.db.models import Count

from apps.competencias.atribuicao import cargos_que_perdem
from apps.competencias.catalogo import acoes_oferecidas
from apps.competencias.comandos import ComandoAtribuicao
from apps.competencias.consulta import ramos_do_alcance
from apps.competencias.models import Acao, AtribuicaoUnidade
from apps.user_admin.context import contexto_organograma
from apps.user_admin.models import Perfil, Unidade
from apps.user_admin.paleta import hex_da_cor
from services.domain.arvore_hierarquica import NoHierarquia
from services.domain.autorizacao import VarianteIcone

DESCRICAO_SEM_CARGO = "nenhum cargo ainda"


def contexto_da_tela(perfil: Perfil, unidade_alvo: Unidade | None = None) -> dict[str, Any]:
    ramos = ramos_do_alcance(perfil)
    # O alvo inicial sai dos PRÓPRIOS ramos do perfil: por construção está dentro do alcance, e é
    # isso que o dispensa da conferência do decorator, que num GET sem parâmetro não roda.
    alvo = unidade_alvo or _primeira_dirigida(ramos)
    return contexto_organograma(
        alvo,
        arvores=ramos,
        # Nesta tela o card escolhe o alvo: levar à página da unidade seria sair no meio do ato, e
        # chamar as irmãs não tem o que revelar — a linha do nível já vem aberta.
        com_link=False,
        com_irmas=False,
        abrir_o_ego=True,
    ) | contexto_painel(alvo)


def contexto_painel(unidade_alvo: Unidade | None) -> dict[str, Any]:
    """O que `_painel_atribuicoes.html` consome sozinho — alvo do hx-get ao trocar de unidade na
    árvore, que não reenvia o organograma."""
    return {
        "unidade_alvo": unidade_alvo,
        "subtitulo_alvo": _subtitulo_unidade(unidade_alvo) if unidade_alvo else "",
        "cor_alvo_hex": hex_da_cor(unidade_alvo.cor) if unidade_alvo else "",
    } | contexto_poco(unidade_alvo)


def contexto_poco(unidade_alvo: Unidade | None) -> dict[str, Any]:
    """O que `_poco_atribuicoes.html` consome sozinho — alvo do swap de atribuir e remover."""
    return {"unidade_alvo": unidade_alvo, "atribuicoes": _atribuicoes_de(unidade_alvo)}


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
