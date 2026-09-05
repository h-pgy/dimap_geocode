"""A composição da tela de atribuições (SPEC autorizacao/007) e da tela de conceder competência
(SPEC autorizacao/008): o alvo escolhido, o organograma recortado ao alcance e o que a unidade-alvo
já exerce — a segunda troca só o que está no poço e como cada atribuição se resume. Orquestração —
nenhuma regra de negócio."""

from collections.abc import Mapping, Sequence
from typing import Any

from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from apps.cargos.models import CargoBase, CargoComissao
from apps.competencias.atribuicao import cargos_que_perdem
from apps.competencias.catalogo import acoes_oferecidas
from apps.competencias.comandos import ComandoAtribuicao
from apps.competencias.consulta import (
    alcance_de_leitura,
    alcance_do_perfil,
    dirige,
    ramos_do_alcance,
    unidades_dirigidas,
    unidades_lidas,
)
from apps.competencias.delegacao import candidatos_a_delegado
from apps.competencias.historico import linhas_de_execucoes
from apps.competencias.models import Acao, AtribuicaoUnidade, Concessao, Delegacao
from apps.core.tabela import colunas_da_tabela, consulta_da_listagem, marca_descendente
from apps.mapping.context import contexto_fundo_admin
from apps.unidades.context import contexto_organograma
from apps.unidades.models import Unidade
from apps.unidades.paleta import hex_da_cor
from apps.user_admin.models import Perfil
from services.domain.arvore_hierarquica import NoHierarquia
from services.domain.autorizacao import VarianteIcone
from services.domain.listagem_gestao import (
    TAMANHO_PAGINA,
    BuscaExecucoes,
    ColunaExecucao,
    LinhaExecucao,
    Pagina,
    listar_execucoes,
    paginar,
)
from services.utils.erros_formulario import RecusaDeFormulario

DESCRICAO_SEM_CARGO = "nenhum cargo ainda"

ROTULO_COLUNAS_EXECUCAO = {
    ColunaExecucao.SERVIDOR: "Servidor",
    ColunaExecucao.UNIDADE: "Unidade",
    ColunaExecucao.CARGO: "Cargo base",
    ColunaExecucao.COMISSAO: "Cargo em Comissão",
    ColunaExecucao.ACAO: "Ação",
    ColunaExecucao.OPERACAO: "Operação",
    ColunaExecucao.ALVO: "Alvo",
}


def contexto_da_tela(perfil: Perfil, unidade_alvo: Unidade | None = None) -> dict[str, Any]:
    ramos = ramos_do_alcance(perfil)
    # O alvo inicial sai dos PRÓPRIOS ramos do perfil: por construção está dentro do alcance, e é
    # isso que o dispensa da conferência do decorator, que num GET sem parâmetro não roda.
    alvo = unidade_alvo or _primeira_dirigida(ramos)
    return (
        contexto_fundo_admin()
        | contexto_organograma(
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
        contexto_fundo_admin()
        | contexto_organograma(
            alvo,
            arvores=ramos,
            com_link=False,
            com_irmas=False,
            abrir_o_ego=True,
        )
        | contexto_painel_concessoes(alvo, perfil=perfil)
        | _rotas_do_seletor("competencias:painel_concessoes", "#painel-concessoes")
    )


def contexto_painel_concessoes(
    unidade_alvo: Unidade | None,
    perfil: Perfil | None = None,
    *,
    fechar_modal: bool = False,
) -> dict[str, Any]:
    """O que `_painel_concessoes.html` consome sozinho — alvo do hx-get ao trocar de unidade na
    árvore, que não reenvia o organograma. `fechar_modal` fecha o de conceder que a unidade
    anterior possa ter deixado aberto — só a troca de unidade o pede; a carga inicial da página
    nunca deve, pois é ela quem primeiro grava o `#modal-conceder` (Caveats)."""
    return {
        "unidade_alvo": unidade_alvo,
        "subtitulo_alvo": _subtitulo_unidade(unidade_alvo) if unidade_alvo else "",
        "cor_alvo_hex": hex_da_cor(unidade_alvo.cor) if unidade_alvo else "",
    } | contexto_poco_concessoes(unidade_alvo, perfil=perfil, fechar_modal=fechar_modal)


def contexto_poco_concessoes(
    unidade_alvo: Unidade | None,
    perfil: Perfil | None = None,
    *,
    fechar_modal: bool = False,
) -> dict[str, Any]:
    """O que `_poco_concessoes.html` consome sozinho — alvo do swap de conceder, revogar e delegar.
    `fechar_modal` liga o checkbox OOB que fecha `#modal-conceder`: só quando esta renderização É
    a resposta de um ato que precisa fechá-lo — nunca na carga inicial da página, sob pena de dois
    elementos com o mesmo id (Caveats)."""
    pode_delegar = False
    if perfil is not None and unidade_alvo is not None:
        pode_delegar = perfil.is_superuser or dirige(perfil, unidade_alvo)
    return {
        "unidade_alvo": unidade_alvo,
        "atribuicoes": _atribuicoes_com_concessoes(unidade_alvo),
        "fechar_modal": fechar_modal,
        "pode_delegar": pode_delegar,
    }


def contexto_modal_conceder(atribuicao: AtribuicaoUnidade) -> dict[str, Any]:
    return {
        "atribuicao": atribuicao,
        "unidade_alvo": atribuicao.unidade,
        "cargos_base": CargoBase.objects.order_by("nome"),
        "cargos_comissao": CargoComissao.objects.order_by("nome"),
    }


def contexto_modal_delegar(
    atribuicao: AtribuicaoUnidade,
    perfil: Perfil,
    valores: Mapping[str, Any] | None = None,
    recusa: RecusaDeFormulario | None = None,
) -> dict[str, Any]:
    alcance = alcance_do_perfil(perfil)
    candidatos = candidatos_a_delegado(atribuicao.unidade, alcance)
    hoje = timezone.localdate()

    candidatos_propria = [c for c in candidatos if c.unidade_id == atribuicao.unidade_id]
    candidatos_subordinadas = [c for c in candidatos if c.unidade_id != atribuicao.unidade_id]

    candidatos_agrupados: list[dict[str, Any]] = []
    if candidatos_propria:
        candidatos_agrupados.append({
            "rotulo": f"{atribuicao.unidade.sigla} (Própria unidade)",
            "servidores": candidatos_propria,
        })
    subordinadas_map: dict[int, list[Perfil]] = {}
    for c in candidatos_subordinadas:
        subordinadas_map.setdefault(c.unidade_id, []).append(c)
    for unid_id, servs in subordinadas_map.items():
        unid_sigla = servs[0].unidade.sigla
        candidatos_agrupados.append({
            "rotulo": f"{unid_sigla} (Subordinada)",
            "servidores": servs,
        })

    return {
        "atribuicao": atribuicao,
        "unidade_alvo": atribuicao.unidade,
        "candidatos_agrupados": candidatos_agrupados,
        "candidatos": candidatos,
        "hoje": hoje.isoformat(),
        "valores": valores or {},
        "erros": recusa.mensagens if recusa else (),
        "realce": recusa.realce if recusa else {},
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
    hoje = timezone.localdate()
    delegacoes = list(
        Delegacao.objects.filter(unidade=unidade)
        .filter(Q(data_fim__isnull=True) | Q(data_fim__gte=hoje))
        .select_related("delegado", "delegado__unidade", "acao")
        .order_by("delegado__nome", "delegado__sobrenome")
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
            "delegacoes": [d for d in delegacoes if d.acao_id == atribuicao.acao_id],
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


# ---------------------------------------------------------------------------
# Registro de Ações (SPEC painel/002): a leitura do rastro que autorizacao/004 grava.
# ---------------------------------------------------------------------------


def contexto_registro_acoes(perfil: Perfil, parametros: Mapping[str, str]) -> dict[str, Any]:
    consulta = consulta_da_listagem(parametros, ColunaExecucao)
    return (
        contexto_fundo_admin()
        | contexto_corpo_execucoes(perfil, parametros)
        | {
            "colunas": colunas_da_tabela(consulta, ColunaExecucao, ROTULO_COLUNAS_EXECUCAO),
            "ordenar_por": consulta.ordenar_por or "",
            "descendente": marca_descendente(consulta),
            "unidades": _opcoes_de_unidade(perfil),
            "unidade_escolhida": _unidade_escolhida(parametros) or perfil.unidade_id,
            "servidores": Perfil.objects.order_by("nome", "sobrenome"),
            "perfil_escolhido": _int_ou_none(parametros.get("perfil")),
            "cargos_base": CargoBase.objects.order_by("nome"),
            "cargo_base_escolhido": _int_ou_none(parametros.get("cargo_base")),
            "cargos_comissao": CargoComissao.objects.order_by("nome"),
            "cargo_comissao_escolhido": _int_ou_none(parametros.get("cargo_comissao")),
        }
    )


def contexto_corpo_execucoes(perfil: Perfil, parametros: Mapping[str, str]) -> dict[str, Any]:
    # Unidades lidas → banco → memória → página, nesta ordem e sem atalho. O cabeçalho nunca vê
    # linha que a busca não trouxe, a busca nunca vê linha fora do alcance, e a paginação é a
    # ÚLTIMA: fatiar antes do filtro daria uma página 2 com linhas que o filtro já descartou.
    escolhida = _unidade_escolhida(parametros)
    busca = BuscaExecucoes.de_parametros(
        parametros,
        hoje=timezone.localdate(),
        unidades_lidas=unidades_lidas(perfil, escolhida),
    )
    filtradas = listar_execucoes(
        linhas_de_execucoes(busca), consulta_da_listagem(parametros, ColunaExecucao)
    )
    pagina = paginar(filtradas, _numero_da_pagina(parametros), TAMANHO_PAGINA)
    return {
        "pagina": pagina,
        "busca": busca,
        "subtitulo": _subtitulo_registro(escolhida or perfil.unidade_id, busca, pagina.total_linhas),
        "pagina_inicio": _pagina_inicio(pagina),
        "pagina_fim": _pagina_fim(pagina),
        "paginas_visiveis": _paginas_visiveis(pagina.numero, pagina.total_paginas),
    }


def _opcoes_de_unidade(perfil: Perfil) -> list[Unidade]:
    """Vazio para quem não dirige nada, e o template não desenha o campo.

    Um select de uma opção só não é escolha — é decoração que ocupa espaço e sugere um recorte que
    não existe. A ausência do controle é a mensagem, como a coluna sem peça na bandeja do
    cabeçalho (skill `componentes-frontend`); campo cinza desabilitado seria o contrário disso.

    As extintas entram na lista: elas estão no alcance, e é justamente o período em que existiram
    que se quer poder abrir.
    """
    if not unidades_dirigidas(perfil):
        return []
    return list(Unidade.todas.filter(pk__in=alcance_de_leitura(perfil)).order_by("sigla"))


def _subtitulo_registro(partida_id: int, busca: BuscaExecucoes, total: int) -> str:
    unidade = Unidade.todas.filter(pk=partida_id).first()
    sigla = unidade.sigla if unidade is not None else ""
    onde = f"na {sigla}"
    if len(busca.unidades_lidas) > 1:
        onde += " e nas unidades abaixo dela"
    periodo = f"{busca.inicio:%d/%m/%Y} e {busca.fim:%d/%m/%Y}"
    plural = "" if total == 1 else "s"
    return f"{total} ato{plural} praticado{plural} {onde}, entre {periodo}."


def _unidade_escolhida(parametros: Mapping[str, str]) -> int | None:
    # "unidade_partida", nunca "unidade": esse nome já é o da COLUNA que o cabeçalho filtra
    # (`ColunaExecucao.UNIDADE`) — a mesma query string carrega as duas coisas (§7), e uma
    # colidindo com a outra faria a escolha do card ser lida como termo de busca pelo cabeçalho.
    bruto = parametros.get("unidade_partida", "")
    return int(bruto) if bruto.isdigit() else None


def _numero_da_pagina(parametros: Mapping[str, str]) -> int:
    bruto = parametros.get("pagina", "")
    return int(bruto) if bruto.isdigit() else 1


def _int_ou_none(bruto: str | None) -> int | None:
    return int(bruto) if bruto and bruto.isdigit() else None


def _pagina_inicio(pagina: Pagina[LinhaExecucao]) -> int:
    return 0 if pagina.total_linhas == 0 else (pagina.numero - 1) * TAMANHO_PAGINA + 1


def _pagina_fim(pagina: Pagina[LinhaExecucao]) -> int:
    return min(pagina.numero * TAMANHO_PAGINA, pagina.total_linhas)


def _paginas_visiveis(numero: int, total: int) -> tuple[int | None, ...]:
    """Primeira, atual e última — sempre. Um vizinho de cortesia (a segunda ou a penúltima) só
    entra quando a atual está literalmente numa ponta, para não abrir a régua já mostrando só um
    número disponível pra ir adiante. Nunca há vizinho no meio: um período largo (§7 dos Caveats)
    desenharia uma centena de botões na mesma placa se a vizinhança de toda página em curso virasse
    números soltos em vez de reticências."""
    nucleo = {1, numero, total}
    if numero == 1:
        nucleo.add(2)
    if numero == total:
        nucleo.add(total - 1)
    ordenadas = sorted(nucleo & set(range(1, total + 1)))
    visiveis: list[int | None] = []
    anterior: int | None = None
    for pagina_numero in ordenadas:
        if anterior is not None and pagina_numero - anterior > 1:
            visiveis.append(None)
        visiveis.append(pagina_numero)
        anterior = pagina_numero
    return tuple(visiveis)
