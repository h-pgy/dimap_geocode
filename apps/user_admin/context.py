"""
Contexto das páginas administrativas de servidor (SPEC user_admin/007), de unidade
(SPEC user_admin/012) e da listagem de servidores (SPEC user_admin/013). Orquestração: traduz o
model para o que o template consome — o hex da cor, a imagem já resolvida pelo domínio, os
catálogos dos selects e as linhas que o domínio filtra e ordena. Nenhuma regra de negócio.
"""

from typing import Any

from apps.mapping.context import contexto_fundo_admin
from apps.user_admin.models import (
    CargoBase,
    CargoComissao,
    Perfil,
    TipoUnidade,
    Unidade,
)
from apps.user_admin.paleta import TINTA_AVATAR, hex_da_cor, tons_da_paleta
from services.domain.avatar import resolver_imagem_perfil
from services.domain.servidores_listagem import (
    ColunaServidor,
    ConsultaServidores,
    LinhaServidor,
    listar_servidores,
)

SEM_CARGO_COMISSAO = "—"
# Valores do aria-sort (WAI-ARIA); o relevo da seta é afordância e não carrega a semântica sozinho.
ORDEM_ASCENDENTE = "ascending"
ORDEM_DESCENDENTE = "descending"
# O par que o campo oculto do cabeçalho carrega — o mesmo que o JavaScript da seta escreve.
DESCENDENTE_LIGADO = "1"
DESCENDENTE_DESLIGADO = "0"
# O rótulo da coluna é da interface, não do domínio: o DTO carrega o dado, não o nome da vitrine.
ROTULO_DA_COLUNA = {
    ColunaServidor.NOME: "Servidor",
    ColunaServidor.RF: "RF",
    ColunaServidor.UNIDADE: "Unidade",
    ColunaServidor.CARGO: "Cargo base",
    ColunaServidor.COMISSAO: "Em comissão",
}


def contexto_criar_perfil() -> dict[str, Any]:
    return (
        contexto_fundo_admin()
        | _catalogos_de_lotacao()
        | _contexto_do_modal_de_unidade()
    )


def contexto_editar_perfil(perfil: Perfil) -> dict[str, Any]:
    cor_unidade_hex = hex_da_cor(perfil.cor_unidade)
    imagem = resolver_imagem_perfil(
        nome=perfil.nome,
        sobrenome=perfil.sobrenome,
        cor_fundo=cor_unidade_hex,
        cor_tinta=TINTA_AVATAR,
        foto_url=_foto_url(perfil),
    )
    return (
        contexto_fundo_admin()
        | _catalogos_de_lotacao()
        | _contexto_do_modal_de_unidade()
        | {
            "perfil": perfil,
            "imagem": imagem,
            "cor_unidade_hex": cor_unidade_hex,
        }
    )


def contexto_listagem_servidores(consulta: ConsultaServidores) -> dict[str, Any]:
    # As colunas viajam com o termo e a ordem em vigor: carregada com filtro na query string, a
    # página nasce com as peças afundadas e a seta entintada, sem JavaScript de estado.
    return (
        contexto_fundo_admin()
        | contexto_corpo_servidores(consulta)
        | {
            "colunas": _colunas(consulta),
            # Os campos ocultos que viajam com os filtros: a ordem sobrevive à troca do corpo.
            "ordenar_por": consulta.ordenar_por or "",
            "descendente": DESCENDENTE_LIGADO if consulta.descendente else DESCENDENTE_DESLIGADO,
        }
    )


def contexto_corpo_servidores(consulta: ConsultaServidores) -> dict[str, Any]:
    linhas = _linhas_de_servidores()
    return {
        "linhas": listar_servidores(linhas, consulta),
        "total_servidores": len(linhas),
    }


def contexto_criar_unidade() -> dict[str, Any]:
    return (
        contexto_fundo_admin() | _catalogos_de_unidade() | contexto_cor_sugerida(None)
    )


def contexto_cor_sugerida(pai_pk: int | None) -> dict[str, Any]:
    pai = Unidade.objects.filter(pk=pai_pk).first() if pai_pk else None
    # Instância não gravada só para não repetir aqui o default que o model já decide.
    cor = Unidade(pai=pai).cor_sugerida
    return {
        "tons": tons_da_paleta(cor),
        "cor_hex": hex_da_cor(cor),
    }


def _contexto_do_modal_de_unidade() -> dict[str, Any]:
    # O modal de nova unidade é renderizado com a página, em criar e em editar (SPEC 012): os
    # catálogos dele custam uma consulta e dispensam rota e hx-get de abertura. Sem isto o disco de
    # paleta nasce sem tons e o select de tipo, vazio.
    return _catalogos_de_unidade() | contexto_cor_sugerida(None)


def _catalogos_de_lotacao() -> dict[str, Any]:
    return _catalogo_de_unidades() | {
        "cargos_base": CargoBase.objects.order_by("nome"),
        "cargos_comissao": CargoComissao.objects.order_by("nome"),
    }


def _catalogos_de_unidade() -> dict[str, Any]:
    # Nível decrescente: a lista de tipos desce da mais abrangente para a mais específica.
    return _catalogo_de_unidades() | {
        "tipos_unidade": TipoUnidade.objects.order_by("-nivel", "nome"),
    }


def _catalogo_de_unidades() -> dict[str, Any]:
    # A mesma lista serve à lotação do servidor e à unidade superior do formulário de unidade.
    return {"unidades": Unidade.objects.select_related("tipo").order_by("sigla")}


def _linhas_de_servidores() -> list[LinhaServidor]:
    # O domínio recebe as linhas materializadas: são dezenas de registros, e filtrar por texto
    # normalizado no banco exigiria duplicar a normalização única em SQL (§6.1).
    perfis = Perfil.objects.select_related(
        "unidade",
        "cargo_base",
        "cargo_comissao",
    ).order_by("nome", "sobrenome")
    return [_linha_do_perfil(perfil) for perfil in perfis]


def _linha_do_perfil(perfil: Perfil) -> LinhaServidor:
    return LinhaServidor(
        pk=perfil.pk,
        nome=f"{perfil.nome} {perfil.sobrenome}",
        rf=perfil.rf,
        unidade=perfil.unidade.sigla,
        cor_unidade=hex_da_cor(perfil.cor_unidade),
        cargo=perfil.cargo_base.nome,
        comissao=perfil.cargo_comissao.nome if perfil.cargo_comissao else SEM_CARGO_COMISSAO,
        impedido=perfil.esta_impedido,
    )


def _colunas(consulta: ConsultaServidores) -> list[dict[str, Any]]:
    termos = {filtro.coluna: filtro.termo for filtro in consulta.filtros}
    return [
        {
            "slug": coluna.value,
            "rotulo": ROTULO_DA_COLUNA[coluna],
            "termo": termos.get(coluna, ""),
            "ordem": _ordem_da_coluna(coluna, consulta),
        }
        for coluna in ColunaServidor
    ]


def _ordem_da_coluna(coluna: ColunaServidor, consulta: ConsultaServidores) -> str:
    # Vazio = sem ordem; o template só escreve aria-sort quando há ordenação nesta coluna.
    if consulta.ordenar_por != coluna:
        return ""
    return ORDEM_DESCENDENTE if consulta.descendente else ORDEM_ASCENDENTE


def _foto_url(perfil: Perfil) -> str | None:
    # Registro órfão (arquivo apagado do storage) viraria <img> quebrado: sem arquivo em disco, o
    # avatar de iniciais assume. A checagem é daqui, não do resolver — ele é domínio puro e não
    # conhece Django nem I/O (SPEC user_admin/006).
    nome_arquivo = perfil.foto.name
    if not nome_arquivo:
        return None
    if not perfil.foto.storage.exists(nome_arquivo):
        return None
    return perfil.foto.url
