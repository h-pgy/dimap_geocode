"""
Contexto das telas do catálogo de tipos de unidade (SPEC user_admin/031): a listagem — sempre com
os extintos, que o toggle "Mostrar tipos extintos" filtra no cliente, nunca aqui — e os quatro atos
que a mantêm. Orquestração: traduz o model para o que o template consome. Nenhuma regra de negócio.
"""

from collections.abc import Collection, Mapping
from typing import Any

from apps.core.tabela import colunas_da_tabela, marca_descendente
from apps.unidades.consulta import tipos_unidade_disponiveis, unidades_ativas_do_tipo
from apps.unidades.direcao import ROTULO_ALTA_ADMINISTRACAO, padrao_do_nivel, rotulo_do_minimo
from apps.unidades.extincao_tipo import previa_da_extincao_tipo, previa_da_reativacao_tipo
from apps.unidades.models import TipoUnidade
from apps.unidades.schemas import RascunhoTipoUnidade
from services.domain.listagem_gestao import (
    ColunaTipoUnidade,
    ConsultaTiposUnidade,
    LinhaTipoUnidade,
    listar_tipos_unidade,
)
from services.domain.tipos_unidade import (
    IdentidadeTipoUnidade,
    PreviaDaEdicaoTipoUnidade,
    avaliar_edicao_tipo,
)
from services.domain.titularidade import NIVEL_MAXIMO, NIVEL_MINIMO
from services.utils.erros_formulario import RecusaDeFormulario

ROTULO_COLUNAS_TIPO_UNIDADE = {
    ColunaTipoUnidade.NOME: "Tipo de unidade",
    ColunaTipoUnidade.NIVEL: "Nível",
    ColunaTipoUnidade.RAIZ: "Pode ser raiz",
    ColunaTipoUnidade.TITULAR: "Requisito do titular",
    ColunaTipoUnidade.VEDADOS: "Tipos filhos vedados",
}
SEPARADOR_DE_VEDADOS = ", "


def contexto_listagem_tipos(consulta: ConsultaTiposUnidade) -> dict[str, Any]:
    return (
        contexto_corpo_tipos(consulta)
        | {
            "colunas": colunas_da_tabela(consulta, ColunaTipoUnidade, ROTULO_COLUNAS_TIPO_UNIDADE),
            "ordenar_por": consulta.ordenar_por or "",
            "descendente": marca_descendente(consulta),
        }
    )


def contexto_corpo_tipos(consulta: ConsultaTiposUnidade, *, oob: bool = False) -> dict[str, Any]:
    """O servidor manda SEMPRE todos os tipos, extintos inclusive — quem mostra ou esconde é o
    toggle "Mostrar tipos extintos", em `filtro_linha_extinta.js` (SPEC, Caveats)."""
    linhas = _linhas_de_tipos()
    return {
        "linhas": listar_tipos_unidade(linhas, consulta),
        "total_tipos": len(linhas),
        "oob": oob,
    }


def contexto_modal_criar_tipo(rascunho: RascunhoTipoUnidade) -> dict[str, Any]:
    return _contexto_do_formulario(_com_rascunho(_valores_em_branco(), rascunho)) | {
        "realce": {},
        "erros": (),
    }


def contexto_criacao_tipo_recusada(
    valores: Mapping[str, Any],
    recusa: RecusaDeFormulario,
) -> dict[str, Any]:
    return _contexto_do_formulario(valores) | {
        "realce": recusa.realce,
        "erros": recusa.mensagens,
    }


def contexto_escolher_tipo_a_editar() -> dict[str, Any]:
    """Sem tipo escolhido — aberto pelo card, sem linha em foco —, a tela começa pelo select: tanto
    o vigente quanto o extinto seguem editáveis (SPEC, §2)."""
    return {"tipo": None, "tipos_editaveis": TipoUnidade.objects.order_by("-nivel", "nome")}


def contexto_modal_editar_tipo(tipo: TipoUnidade, rascunho: RascunhoTipoUnidade) -> dict[str, Any]:
    return (
        _contexto_do_formulario(_com_rascunho(_valores_de(tipo), rascunho))
        | _travas_de(tipo)
        | {
            "tipo": tipo,
            "realce": {},
            "erros": (),
        }
    )


def contexto_edicao_tipo_recusada(
    tipo: TipoUnidade,
    valores: Mapping[str, Any],
    recusa: RecusaDeFormulario,
) -> dict[str, Any]:
    return (
        _contexto_do_formulario(valores)
        | _travas_de(tipo)
        | {
            "tipo": tipo,
            "realce": recusa.realce,
            "erros": recusa.mensagens,
        }
    )


def contexto_modal_extinguir_tipo(tipo: TipoUnidade | None) -> dict[str, Any]:
    """Sem tipo escolhido, ainda não há prévia: o select espera a escolha. O catálogo é global, e
    não há alcance a recortar."""
    vigentes = tipos_unidade_disponiveis()
    return {
        "tipo": tipo,
        "previa": previa_da_extincao_tipo(tipo) if tipo is not None else None,
        "requisito": rotulo_do_requisito(tipo) if tipo is not None else "",
        "vedados": _nomes_dos_vedados(tipo) if tipo is not None else "",
        "tipos": vigentes.exclude(pk=tipo.pk) if tipo else vigentes,
    }


def contexto_extincao_tipo_recusada(
    tipo: TipoUnidade,
    recusa: RecusaDeFormulario,
) -> dict[str, Any]:
    return contexto_modal_extinguir_tipo(tipo) | {
        "erros": recusa.mensagens,
        "realce": recusa.realce,
    }


def contexto_modal_reativar_tipo(tipo: TipoUnidade | None) -> dict[str, Any]:
    extintos = TipoUnidade.objects.filter(extinto_em__isnull=False).order_by("-nivel", "nome")
    return {
        "tipo": tipo,
        "previa": previa_da_reativacao_tipo(tipo) if tipo is not None else None,
        "tipos": extintos.exclude(pk=tipo.pk) if tipo else extintos,
    }


def contexto_reativacao_tipo_recusada(
    tipo: TipoUnidade,
    recusa: RecusaDeFormulario,
) -> dict[str, Any]:
    return contexto_modal_reativar_tipo(tipo) | {
        "erros": recusa.mensagens,
        "realce": recusa.realce,
    }


def rotulo_do_requisito(tipo: TipoUnidade) -> str:
    if tipo.exige_alta_administracao:
        return ROTULO_ALTA_ADMINISTRACAO
    padrao = rotulo_do_minimo(tipo)
    # Nível sem cargo de chefia cadastrado não tem padrão a dizer: sobra o número.
    return f"Mínimo {padrao}" if padrao else f"Mínimo nível {tipo.nivel_minimo_titular}"


def _linhas_de_tipos() -> list[LinhaTipoUnidade]:
    tipos = TipoUnidade.objects.prefetch_related("tipos_filhos_vedados").order_by("-nivel", "nome")
    return [_linha_do_tipo(tipo) for tipo in tipos]


def _linha_do_tipo(tipo: TipoUnidade) -> LinhaTipoUnidade:
    return LinhaTipoUnidade(
        pk=tipo.pk,
        nome=tipo.nome,
        nivel=tipo.nivel,
        pode_ser_raiz=tipo.pode_ser_raiz,
        exige_alta_administracao=tipo.exige_alta_administracao,
        titular=rotulo_do_requisito(tipo),
        vedados=_nomes_dos_vedados(tipo),
        unidades=unidades_ativas_do_tipo(tipo),
        extinto=tipo.extinto,
    )


def _nomes_dos_vedados(tipo: TipoUnidade) -> str:
    return SEPARADOR_DE_VEDADOS.join(sorted(vedado.nome for vedado in tipo.tipos_filhos_vedados.all()))


def _travas_de(tipo: TipoUnidade) -> dict[str, Any]:
    unidades_ativas = unidades_ativas_do_tipo(tipo)
    travas = avaliar_edicao_tipo(
        PreviaDaEdicaoTipoUnidade(
            tipo=IdentidadeTipoUnidade(tipo_id=tipo.pk, nome=tipo.nome),
            unidades_ativas=unidades_ativas,
        )
    )
    return {
        "unidades_ativas": unidades_ativas,
        "estrutura_travada": travas.estrutura_travada,
        "motivo_da_trava": travas.motivo,
        # O lado LIDO da face travada: o que está gravado, e não o que o POST recusado trouxe.
        "requisito_gravado": rotulo_do_requisito(tipo),
        "vedados_gravados": tipo.tipos_filhos_vedados.order_by("-nivel", "nome"),
    }


def _valores_em_branco() -> dict[str, Any]:
    return {
        "nome": "",
        "nivel": "",
        "pode_ser_raiz": False,
        "exige_alta_administracao": False,
        "nivel_minimo_titular": None,
        "tipos_filhos_vedados": (),
    }


def _valores_de(tipo: TipoUnidade) -> dict[str, Any]:
    return {
        "nome": tipo.nome,
        "nivel": tipo.nivel,
        "pode_ser_raiz": tipo.pode_ser_raiz,
        "exige_alta_administracao": tipo.exige_alta_administracao,
        "nivel_minimo_titular": tipo.nivel_minimo_titular,
        "tipos_filhos_vedados": tuple(tipo.tipos_filhos_vedados.values_list("pk", flat=True)),
    }


def _com_rascunho(valores: Mapping[str, Any], rascunho: RascunhoTipoUnidade) -> dict[str, Any]:
    """O bloco que pediu o próprio redesenho manda o estado dele inteiro; o que não pediu segue
    com o que a tela já tinha. Nada aqui é gravado — é o formulário ainda em preenchimento."""
    resultado = dict(valores)
    if rascunho.exige_alta_administracao is not None:
        resultado["exige_alta_administracao"] = rascunho.exige_alta_administracao
        resultado["nivel_minimo_titular"] = rascunho.nivel_minimo_titular
    if rascunho.vedar is not None or rascunho.desvedar is not None:
        vedados = [pk for pk in rascunho.tipos_filhos_vedados if pk != rascunho.desvedar]
        if rascunho.vedar is not None and rascunho.vedar not in vedados:
            vedados.append(rascunho.vedar)
        resultado["tipos_filhos_vedados"] = tuple(vedados)
    return resultado


def _contexto_do_formulario(valores: Mapping[str, Any]) -> dict[str, Any]:
    vedados_ids = _ids(valores.get("tipos_filhos_vedados", ()))
    todos = TipoUnidade.objects.order_by("-nivel", "nome")
    return {
        # O nível mínimo volta como texto do POST cru; o `selected` do select compara com o número.
        "valores": dict(valores) | {"nivel_minimo_titular": _inteiro(valores.get("nivel_minimo_titular"))},
        "vedados": todos.filter(pk__in=vedados_ids),
        "candidatos_a_vedar": todos.exclude(pk__in=vedados_ids),
        "minimo_opcoes": _opcoes_de_minimo(),
    }


def _opcoes_de_minimo() -> list[tuple[int, str]]:
    # O mesmo padrão de cargo que a página da unidade diz como mínimo do titular.
    return [(nivel, _rotulo_do_nivel(nivel)) for nivel in range(NIVEL_MINIMO, NIVEL_MAXIMO + 1)]


def _rotulo_do_nivel(nivel: int) -> str:
    padrao = padrao_do_nivel(nivel)
    return f"Nível {nivel} · {padrao}" if padrao else f"Nível {nivel}"


def _ids(brutos: Collection[Any]) -> list[int]:
    return [int(bruto) for bruto in brutos if str(bruto).isdigit()]


def _inteiro(bruto: Any) -> int | None:
    return int(bruto) if str(bruto).isdigit() else None
