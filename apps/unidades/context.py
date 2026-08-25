"""
Contexto das telas de unidade: o formulário de cadastro (SPEC user_admin/012), a página própria
(SPEC user_admin/016), o organograma (SPEC user_admin/018), a listagem com organograma integrado
(SPEC user_admin/021) e os dois atos que mantêm o organograma (SPEC user_admin/020). Orquestração:
traduz o model para o que o template consome — o hex da cor, os catálogos dos selects, as linhas
que o domínio filtra e ordena e os ramos da árvore já casados com as unidades. Nenhuma regra de
negócio.
"""

from collections.abc import Collection, Mapping, Sequence
from typing import Any

from django.utils import timezone

from apps.core.tabela import colunas_da_tabela, marca_descendente
from apps.mapping.context import contexto_fundo_admin
from apps.unidades.consulta import posicao_de
from apps.unidades.direcao import (
    alarme_sem_direcao,
    alarme_sem_titular,
    estado_da_direcao,
    rotulo_do_minimo,
)
from apps.unidades.models import CorUnidade, TipoUnidade, Unidade
from apps.unidades.paleta import hex_da_cor, tons_da_paleta
from apps.unidades.titularidade import candidatos_a_titular
from apps.user_admin.apresentacao import imagem_do_perfil, selo_do_exercicio
from apps.user_admin.exercicio import substituicao_vigente
from apps.user_admin.models import q_vigente_em
from services.domain.arvore_hierarquica import NoHierarquia
from services.domain.listagem_gestao import (
    ColunaUnidade,
    ConsultaUnidades,
    LinhaUnidade,
    listar_unidades,
)
from services.domain.titularidade import avaliar_direcao
from services.utils.erros_formulario import RecusaDeFormulario

# O rótulo da coluna é da interface, não do domínio: o DTO carrega o dado, não o nome da vitrine.
ROTULO_COLUNAS_UNIDADE = {
    ColunaUnidade.SIGLA: "Sigla",
    ColunaUnidade.NOME: "Unidade",
    ColunaUnidade.TIPO: "Tipo",
    ColunaUnidade.TITULAR: "Titular",
    ColunaUnidade.PAI: "Subordinação",
}


def contexto_criar_unidade(
    ids_permitidos: Collection[int] | None = None,
    *,
    raiz: bool = False,
) -> dict[str, Any]:
    return (
        contexto_fundo_admin()
        | _catalogos_de_unidade(ids_permitidos)
        | contexto_cor_sugerida(None)
        | {"raiz": raiz}
    )


def contexto_listagem_unidades(
    consulta: ConsultaUnidades,
    unidade_em_foco: Unidade | None = None,
) -> dict[str, Any]:
    return (
        contexto_fundo_admin()
        | contexto_organograma(unidade_em_foco)
        | contexto_corpo_unidades(consulta, unidade_em_foco)
        | {
            "colunas": colunas_da_tabela(consulta, ColunaUnidade, ROTULO_COLUNAS_UNIDADE),
            # Os campos ocultos que viajam com os filtros: a ordem sobrevive à troca do corpo.
            "ordenar_por": consulta.ordenar_por or "",
            "descendente": marca_descendente(consulta),
        }
    )


def contexto_corpo_unidades(
    consulta: ConsultaUnidades,
    unidade_em_foco: Unidade | None = None,
) -> dict[str, Any]:
    linhas = _linhas_de_unidades()
    processadas = listar_unidades(linhas, consulta)
    return {
        "linhas": _foco_no_topo(processadas, unidade_em_foco),
        "total_unidades": len(linhas),
        "unidade_foco_pk": unidade_em_foco.pk if unidade_em_foco else None,
    }


def contexto_unidade(unidade: Unidade) -> dict[str, Any]:
    """Uma passagem só: quem a tela carrega para desenhar é quem ela usa para decidir."""
    titular = unidade.titular
    # A vigente vem da SPEC 015: o predicado de data não se copia por tela.
    substituicao = substituicao_vigente(titular) if titular else None
    substituto = substituicao.substituto if substituicao else None
    direcao = avaliar_direcao(estado_da_direcao(titular, substituto))
    titular_impedimento = (
        titular.impedimentos.filter(q_vigente_em(timezone.localdate())).first()
        if titular and direcao == "sem_direcao"
        else None
    )
    return (
        contexto_fundo_admin()
        | _catalogos_de_unidade()
        | contexto_organograma(unidade)
        | {
            "unidade": unidade,
            "unidade_cor_hex": hex_da_cor(unidade.cor),
            "pai_cor_hex": hex_da_cor(unidade.pai.cor) if unidade.pai else None,
            "titular": titular,
            "titular_selo": selo_do_exercicio(titular) if titular else None,
            "titular_imagem": imagem_do_perfil(titular) if titular else None,
            "titular_cor_unidade_hex": hex_da_cor(titular.cor_unidade) if titular else None,
            "titular_impedimento": titular_impedimento,
            "substituto": substituto,
            "substituto_imagem": imagem_do_perfil(substituto) if substituto else None,
            "substituto_cor_unidade_hex": (
                hex_da_cor(substituto.cor_unidade) if substituto else None
            ),
            # O template acende selo e alarme pelo enum; a causa é decidida no domínio.
            "direcao": direcao,
            "alarme_sem_titular": alarme_sem_titular(unidade),
            "alarme_sem_direcao": alarme_sem_direcao(unidade, titular) if titular else "",
            "candidatos": candidatos_a_titular(unidade),
            "cargo_minimo": rotulo_do_minimo(unidade.tipo),
            "total_lotados": unidade.perfis.count(),
        }
    )


def contexto_organograma(
    unidade_em_foco: Unidade | None,
    *,
    arvores: Sequence[NoHierarquia] | None = None,
    com_link: bool = True,
    com_irmas: bool = True,
    abrir_o_ego: bool = False,
) -> dict[str, Any]:
    """A seção da página da unidade (caminho aberto até `unidade_em_foco`) e a página da árvore
    inteira (`unidade_em_foco=None`) nascem da mesma regra: a posição da raiz é o organograma
    inteiro, e o caminho que abre é a posição da unidade da página.

    `arvores` recorta o organograma ao que o chamador alcança; sem elas, a hierarquia inteira.
    Recebe a árvore pronta, e não as raízes, porque quem tem o recorte já a percorreu para saber
    qual é (SPEC autorizacao/007)."""
    # A regra devolve ids; o template precisa de unidades. Casar as duas coisas aqui é o que impede
    # o domínio de conhecer `Unidade` e o template de conhecer id solto.
    ramos = (
        list(arvores)
        if arvores is not None
        else [posicao_de(raiz.pk).ego for raiz in Unidade.objects.filter(pai__isnull=True)]
    )
    por_id = Unidade.objects.in_bulk(
        frozenset(unidade_id for ramo in ramos for unidade_id in ramo.ids)
    )
    caminho = frozenset(posicao_de(unidade_em_foco.pk).acima) if unidade_em_foco else frozenset()
    # Ordenar aqui, e não na origem: sigla é da `Unidade`, e é o `in_bulk` desta função que a tem
    # em mãos. `unidades_dirigidas` devolve conjunto — sem isto a árvore trocaria de ordem entre
    # duas aberturas da mesma tela.
    ramos = sorted(ramos, key=lambda ramo: por_id[ramo.unidade_id].sigla)
    return {
        "ramos": [_ramo(ramo, por_id, caminho, unidade_em_foco) for ramo in ramos],
        "unidade_em_foco": unidade_em_foco,
        # As três SEMPRE no contexto, mesmo no default: variável ausente é falsa no template, e as
        # telas da 018 perderiam o elo e a seta em silêncio.
        "com_link": com_link,
        "com_irmas": com_irmas,
        "abrir_o_ego": abrir_o_ego,
    }


def contexto_da_paleta(cor: str) -> dict[str, Any]:
    """Recebe o valor CRU do POST para repopular a tela recusada — por isso `str`, e não o enum:
    slug forjado cai no default em vez de estourar o template, e quem o recusa é o DTO."""
    tinta = cor if cor in CorUnidade.values else CorUnidade.AGUA_700
    return {
        "tons": tons_da_paleta(tinta),
        "cor_hex": hex_da_cor(tinta),
    }


def contexto_cor_sugerida(pai_pk: int | None) -> dict[str, Any]:
    # Continua sendo a resposta do hx-get do select de pai — e só do CADASTRO: na edição a cor é
    # escolha gravada, e resugerir repintaria a unidade sem que ninguém pedisse.
    pai = Unidade.objects.filter(pk=pai_pk).first() if pai_pk else None
    return contexto_da_paleta(Unidade(pai=pai).cor_sugerida)


def contexto_do_modal_de_unidade(
    ids_permitidos: Collection[int] | None = None,
) -> dict[str, Any]:
    # O modal de nova unidade é renderizado com a página, em criar e em editar (SPEC 012): os
    # catálogos dele custam uma consulta e dispensam rota e hx-get de abertura. Sem isto o disco de
    # paleta nasce sem tons e o select de tipo, vazio.
    return _catalogos_de_unidade(ids_permitidos) | contexto_cor_sugerida(None)


def contexto_criacao_recusada(
    valores: Mapping[str, Any],
    recusa: RecusaDeFormulario,
    ids_permitidos: Collection[int] | None = None,
    *,
    raiz: bool = False,
) -> dict[str, Any]:
    return (
        _catalogos_de_unidade(ids_permitidos)
        | contexto_da_paleta(str(valores.get("cor", "")))
        | {
            "valores": valores,
            "realce": recusa.realce,
            "erros": recusa.mensagens,
            "raiz": raiz,
        }
    )


def contexto_unidade_selecionada(
    unidade: Unidade,
    ids_permitidos: Collection[int] | None = None,
) -> dict[str, Any]:
    return {"unidade": unidade, "selecionado": unidade.pk} | catalogo_de_unidades(ids_permitidos)


def contexto_modal_unidade(unidade: Unidade) -> dict[str, Any]:
    """Abertura do modal de edição: `valores` nasce igual ao que já está gravado — na recusa os
    dois divergem, e é `contexto_edicao_recusada` quem os separa. Sem recorte de alcance: o destino
    da transferência pode ficar fora dele de propósito (SPEC, §7) — recortar o select impediria a
    própria transferência que o ato existe para permitir."""
    return (
        _catalogos_de_unidade()
        | contexto_da_paleta(unidade.cor)
        | {
            "unidade": unidade,
            "valores": _valores_de(unidade),
            "realce": {},
            "erros": (),
            "exige_confirmacao": False,
        }
    )


def contexto_edicao_recusada(
    unidade: Unidade,
    valores: Mapping[str, Any],
    recusa: RecusaDeFormulario,
    *,
    exige_confirmacao: bool = False,
) -> dict[str, Any]:
    return (
        _catalogos_de_unidade()
        | contexto_da_paleta(str(valores.get("cor", "")))
        | {
            "unidade": unidade,
            "valores": valores,
            "realce": recusa.realce,
            "erros": recusa.mensagens,
            "exige_confirmacao": exige_confirmacao,
        }
    )


def catalogo_de_unidades(ids_permitidos: Collection[int] | None = None) -> dict[str, Any]:
    """`ids_permitidos` recorta o catálogo ao alcance de quem abre a tela (SPEC
    criacao_usuarios/004). Sem ele, todas — que é o que o modal de edição continua pedindo.

    Recebe ids, e não o perfil: este módulo não pode importar `apps.competencias`, que já importa
    o contexto daqui (SPEC autorizacao/003). Quem resolve o alcance é a view."""
    unidades = Unidade.objects.select_related("tipo").order_by("sigla")
    if ids_permitidos is not None:
        unidades = unidades.filter(pk__in=ids_permitidos)
    return {"unidades": unidades}


def _foco_no_topo(
    linhas: Sequence[LinhaUnidade],
    unidade_em_foco: Unidade | None,
) -> list[LinhaUnidade]:
    """Chegar pela seção de hierarquia (`?foco=`) já abre a tabela com a unidade na primeira
    posição — o mesmo lugar em que o deslizamento do JS a deixaria se ela tivesse sido clicada."""
    if unidade_em_foco is None:
        return list(linhas)
    no_topo = [linha for linha in linhas if linha.pk == unidade_em_foco.pk]
    return no_topo + [linha for linha in linhas if linha.pk != unidade_em_foco.pk]


def _linhas_de_unidades() -> list[LinhaUnidade]:
    unidades = (
        Unidade.objects.select_related("tipo", "pai").prefetch_related("perfis").order_by("sigla")
    )
    return [_linha_da_unidade(unidade) for unidade in unidades]


def _linha_da_unidade(unidade: Unidade) -> LinhaUnidade:
    titular = unidade.titular
    return LinhaUnidade(
        pk=unidade.pk,
        sigla=unidade.sigla,
        nome=unidade.nome,
        tipo=unidade.tipo.nome,
        exige_alta_administracao=unidade.tipo.exige_alta_administracao,
        cor_hex=hex_da_cor(unidade.cor),
        titular_pk=titular.pk if titular else None,
        titular_nome=f"{titular.nome} {titular.sobrenome}" if titular else None,
        pai_pk=unidade.pai.pk if unidade.pai else None,
        pai_sigla=unidade.pai.sigla if unidade.pai else None,
    )


def _ramo(
    no: NoHierarquia,
    por_id: Mapping[int, Unidade],
    caminho: frozenset[int],
    em_foco: Unidade | None,
) -> dict[str, Any]:
    """O card sai daqui já sabendo o que é: fora do caminho, no caminho, ou em foco. Quem decide o
    estado inicial é o servidor; o JS só o move a partir dali."""
    unidade = por_id[no.unidade_id]
    return {
        "unidade": unidade,
        "cor_hex": hex_da_cor(unidade.cor),
        "no_caminho": no.unidade_id in caminho,
        "em_foco": em_foco is not None and no.unidade_id == em_foco.pk,
        "filhas": [_ramo(filha, por_id, caminho, em_foco) for filha in no.filhas],
    }


def _catalogos_de_unidade(ids_permitidos: Collection[int] | None = None) -> dict[str, Any]:
    # Nível decrescente: a lista de tipos desce da mais abrangente para a mais específica.
    return catalogo_de_unidades(ids_permitidos) | {
        "tipos_unidade": TipoUnidade.objects.order_by("-nivel", "nome"),
    }


def _valores_de(unidade: Unidade) -> dict[str, Any]:
    return {
        "nome": unidade.nome,
        "sigla": unidade.sigla,
        "tipo_id": unidade.tipo_id,
        "pai_id": unidade.pai_id,
        "cor": unidade.cor,
    }
