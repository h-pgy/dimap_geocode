"""
Contexto das páginas administrativas de servidor (SPEC user_admin/007), da listagem de servidores
(SPEC user_admin/013), da seção de exercício (SPEC user_admin/015) e do cadastro de servidor
(SPEC criacao_usuarios/004). Orquestração: traduz o model para o que o template consome — os
catálogos dos selects, as linhas que o domínio filtra e ordena e a régua da calha. Nenhuma regra de
negócio.
"""

from collections.abc import Collection, Mapping
from datetime import date
from typing import Any

from django.utils import timezone

from apps.core.tabela import colunas_da_tabela, marca_descendente
from apps.mapping.context import contexto_fundo_admin
from apps.unidades.context import catalogo_de_unidades, contexto_do_modal_de_unidade
from apps.unidades.direcao import alarme_sem_direcao, estado_da_direcao
from apps.unidades.paleta import hex_da_cor
from apps.user_admin.acoes_declaradas import ACAO_CRIAR_SERVIDOR, ACAO_TORNAR_ADMINISTRADOR
from apps.user_admin.apresentacao import imagem_do_perfil, selo_do_exercicio
from apps.user_admin.exercicio import (
    candidatos_a_substituto,
    impedimentos_em_aberto,
    lacuna_proposta,
    periodo_de,
    substituicao_que_exerce,
    substituicao_vigente,
    substituicoes_do_impedimento,
    trechos_do_impedimento,
)
from apps.user_admin.models import (
    CargoBase,
    CargoComissao,
    Impedimento,
    Perfil,
    Substituicao,
    TipoImpedimento,
)
from services.domain.autorizacao import VarianteIcone
from services.domain.exercicio import Periodo, Trecho, vigente_em
from services.domain.listagem_gestao import (
    ColunaServidor,
    ConsultaServidores,
    LinhaServidor,
    listar_servidores,
)
from services.domain.titularidade import Direcao, avaliar_direcao
from services.utils.erros_formulario import RecusaDeFormulario

SEM_CARGO_COMISSAO = "—"
# Os campos do formulário de servidor que o `selected` do select compara com um `pk`.
CAMPOS_DE_ID = ("unidade_id", "cargo_base_id", "cargo_comissao_id")
ROTULO_UM_SUBSTITUTO = "Substituído por"
ROTULO_VARIOS_SUBSTITUTOS = "Substituições"
ROTULO_SEM_SUBSTITUTO = "Sem substituto"
PRAZO_INDETERMINADO = "prazo indeterminado"
SITUACAO_VIGENTE = "substituindo hoje"
SITUACAO_ENCERRADA = "encerrada"
SITUACAO_IMPEDIMENTO_VIGENTE = "vigente"
FORMATO_LONGO = "%d/%m/%Y"
FORMATO_CURTO = "%d/%m"
# Prazo indeterminado não tem denominador: a régua vai até a última data conhecida e o resto
# dissolve sob a máscara da calha.
FRACAO_REGUA_ABERTA = 72.0
LARGURA_TOTAL = 100.0
# O rótulo da coluna é da interface, não do domínio: o DTO carrega o dado, não o nome da vitrine.
ROTULO_DA_COLUNA = {
    ColunaServidor.NOME: "Servidor",
    ColunaServidor.RF: "RF",
    ColunaServidor.UNIDADE: "Unidade",
    ColunaServidor.CARGO: "Cargo base",
    ColunaServidor.COMISSAO: "Em comissão",
}

def contexto_criar_perfil(
    ids_permitidos: Collection[int],
    pode_administrador: bool = False,
) -> dict[str, Any]:
    # Os dois catálogos de unidade recortados na fonte, e não um deles pela ordem do merge: o
    # select de lotação e o de unidade superior do painel dividem a chave "unidades" (SPEC
    # criacao_usuarios/006). `pode_administrador` (SPEC user_admin/022) é o mesmo `has_perm` da
    # barreira, resolvido pela view — nunca uma segunda regra escrita na tela.
    return (
        contexto_fundo_admin()
        | contexto_do_modal_de_unidade(ids_permitidos)
        | _catalogos_de_lotacao(ids_permitidos)
        | _icone_administrador()
        | {"pode_administrador": pode_administrador}
    )


def contexto_cadastro_recusado(
    valores: Mapping[str, Any],
    recusa: RecusaDeFormulario,
    ids_permitidos: Collection[int],
    pode_administrador: bool = False,
) -> dict[str, Any]:
    """O que volta é o mesmo formulário: o digitado permanece, a foto não — arquivo de upload não
    se reconstrói de uma resposta de servidor.

    Repopula do formulário cru, e não do DTO: na recusa do próprio DTO não existe DTO algum para
    repopular. Recebe a recusa já desembrulhada porque a do desfecho é opcional, e desembrulhá-la
    aqui obrigaria este módulo a importar `cadastro.py` só para isso (SPEC criacao_usuarios/004)."""
    # A chave continua sendo `perfil`: é o nome que as seções do formulário já leem.
    return contexto_criar_perfil(ids_permitidos, pode_administrador) | {
        "perfil": _valores_do_formulario(valores),
        # `mensagens` alimenta a tarja; `realce`, a classe de cada controle — os dois já prontos
        # pela SPEC formularios/001, sem o template precisar de condicional.
        "erros": recusa.mensagens,
        "realce": recusa.realce,
    }


def _valores_do_formulario(valores: Mapping[str, Any]) -> dict[str, Any]:
    """O `selected` do select compara com `unidade.pk`: id que voltasse como texto não seria
    reconhecido, e o campo perderia a escolha justamente na tela que pede para corrigi-la. Só os
    ids são convertidos — RF com zero à esquerda não sobreviveria a um `int()`."""
    lidos = dict(valores)
    for campo in CAMPOS_DE_ID:
        bruto = lidos.get(campo)
        if not isinstance(bruto, str) or not bruto.isdigit():
            continue
        lidos[campo] = int(bruto)
    return lidos


def contexto_cadastro_concluido(perfil: Perfil) -> dict[str, Any]:
    return {"perfil": perfil}


def contexto_pagina_perfil(perfil: Perfil) -> dict[str, Any]:
    """O que a página lê. Sem catálogo nenhum: os selects são do modal, que vem por rota."""
    return (
        contexto_fundo_admin()
        | contexto_exercicio(perfil)
        | _icone_administrador()
        | {
            "perfil": perfil,
            "imagem": imagem_do_perfil(perfil),
            "cor_unidade_hex": hex_da_cor(perfil.cor_unidade),
            # Titularidade é atributo do perfil, e a unidade dirigida é sempre a de lotação:
            # perguntar de novo ao banco por Unidade.titular seria refazer o que já está em mãos.
            "unidade_dirigida": perfil.unidade if perfil.e_titular else None,
        }
    )


def contexto_modal_perfil(
    perfil: Perfil,
    ids_permitidos: Collection[int],
    valores: Mapping[str, Any] | None = None,
    pode_administrador: bool = False,
) -> dict[str, Any]:
    """O que o modal preenche: o perfil, os catálogos dos três selects e os do painel de unidade,
    que vem fechado dentro dele.

    O modal tem duas faces do mesmo servidor — o lado LIDO do `.campo-onsen`, que mostra o que está
    gravado, e o input atrás do lápis, que mostra o que a pessoa digitou. Na abertura os dois
    coincidem e `valores` sai do próprio perfil; na recusa eles divergem, e é essa divergência que
    deixa a pessoa comparar o que tentou com o que vale (SPEC criacao_usuarios/005).

    `perfil` continua sendo o model, e não um dicionário como no formulário de criação: o lado lido
    pede `unidade.sigla`, `cargo_base.nome`, o avatar e a tarja de titular."""
    return (
        contexto_do_modal_de_unidade(ids_permitidos)
        | _catalogos_de_lotacao(ids_permitidos)
        | _icone_administrador()
        | {
            "perfil": perfil,
            "valores": valores if valores is not None else _valores_do_perfil(perfil),
            "imagem": imagem_do_perfil(perfil),
            "cor_unidade_hex": hex_da_cor(perfil.cor_unidade),
            # SPEC user_admin/022: o mesmo `has_perm` da barreira, resolvido pela view.
            "pode_administrador": pode_administrador,
        }
    )


def _valores_do_perfil(perfil: Perfil) -> dict[str, Any]:
    """A abertura do modal, dita na mesma língua da recusa: os ids já como inteiros, que é o que o
    `selected` do select compara."""
    return {
        "rf": perfil.rf,
        "nome": perfil.nome,
        "sobrenome": perfil.sobrenome,
        "email": perfil.email,
        "unidade_id": perfil.unidade_id,
        "cargo_base_id": perfil.cargo_base_id,
        "cargo_comissao_id": perfil.cargo_comissao_id,
        # SPEC user_admin/022 v3: a marca é campo do formulário, e o que ela mostra na abertura é o
        # que está gravado.
        "administrador": perfil.is_superuser,
    }


def contexto_edicao_recusada(
    perfil: Perfil,
    ids_permitidos: Collection[int],
    valores: Mapping[str, Any],
    recusa: RecusaDeFormulario,
    pode_administrador: bool = False,
) -> dict[str, Any]:
    # `perfil` vem do banco INTOCADO: `editar_servidor` altera a instância dele em memória antes do
    # `full_clean`, e reaproveitá-la mostraria no lado lido o valor que a recusa impediu de gravar.
    return contexto_modal_perfil(
        perfil, ids_permitidos, _valores_do_formulario(valores), pode_administrador
    ) | {
        "erros": recusa.mensagens,
        "realce": recusa.realce,
    }


# ---------------------------------------------------------------------------
# O botão de administrador do sistema e o modal da rota direta (SPEC user_admin/022)
# ---------------------------------------------------------------------------


def contexto_botao_administrador(perfil: Perfil) -> dict[str, Any]:
    return {"perfil": perfil} | _icone_administrador()


def contexto_administrador_recusado(
    perfil: Perfil,
    recusa: RecusaDeFormulario,
) -> dict[str, Any]:
    return {
        "perfil": perfil,
        "erros": recusa.mensagens,
        "realce": recusa.realce,
    } | _icone_administrador()


def contexto_modal_administrador() -> dict[str, Any]:
    return catalogo_de_unidades() | _icone_administrador()


def _icone_administrador() -> dict[str, Any]:
    # O slug e a variante vão prontos para o `icone_acao` do template — o svg em si só se resolve
    # lá, porque o resolvedor mora em `apps.competencias`, que este módulo não pode importar
    # (mesmo molde de `acao_criar_servidor` em `contexto_listagem_servidores`).
    return {
        "acao_tornar_administrador": ACAO_TORNAR_ADMINISTRADOR.acao,
        "variante_icone_pequena": VarianteIcone.PEQUENO,
        "variante_icone_grande": VarianteIcone.GRANDE,
    }


def contexto_opcoes_administrador(unidade_id: int | None) -> dict[str, Any]:
    if unidade_id is None:
        return {"servidores": Perfil.objects.none()}
    return {
        "servidores": Perfil.objects.filter(unidade_id=unidade_id).order_by("nome", "sobrenome")
    }


def contexto_exercicio(perfil: Perfil) -> dict[str, Any]:
    """A seção e os diálogos dela: os cartões dos impedimentos em aberto, a agenda de cada um, a
    lacuna que a designação propõe e os candidatos dos dois alcances. Uma passagem só — nada na
    página pergunta duas vezes a mesma coisa ao banco."""
    tem_cargo_comissao = perfil.cargo_comissao_id is not None
    universos = _universos_de_candidatos(perfil) if tem_cargo_comissao else {}
    return {
        "exercicio": {
            "selo": selo_do_exercicio(perfil),
            "exonerado": perfil.exonerado,
            "afastado": perfil.esta_impedido,
            "tem_cargo_comissao": tem_cargo_comissao,
            "tipos_impedimento": TipoImpedimento.objects.order_by("nome"),
            "cartoes": [
                _cartao_do_impedimento(impedimento, universos)
                for impedimento in impedimentos_em_aberto(perfil)
            ],
            "substituindo": _substituindo(perfil),
            # Reflexo da SPEC 016: a mesma pergunta ("esta unidade tem direção hoje?"), aplicada à
            # unidade de quem é titular desta página.
            "alarme_sem_direcao": _alarme_sem_direcao_do_titular(perfil),
        }
    }


def contexto_listagem_servidores(consulta: ConsultaServidores) -> dict[str, Any]:
    # As colunas viajam com o termo e a ordem em vigor: carregada com filtro na query string, a
    # página nasce com as peças afundadas e a seta entintada, sem JavaScript de estado.
    return (
        contexto_fundo_admin()
        | contexto_corpo_servidores(consulta)
        | {
            "colunas": colunas_da_tabela(consulta, ColunaServidor, ROTULO_DA_COLUNA),
            # Os campos ocultos que viajam com os filtros: a ordem sobrevive à troca do corpo.
            "ordenar_por": consulta.ordenar_por or "",
            "descendente": marca_descendente(consulta),
            # O botão só existe para quem `perms` libera (SPEC criacao_usuarios/004); o slug e a
            # variante vão prontos para o `icone_acao` do template — o svg em si só se resolve lá,
            # porque o resolvedor mora em apps.competencias, que este módulo não pode importar.
            "acao_criar_servidor": ACAO_CRIAR_SERVIDOR.acao,
            "variante_icone_pequena": VarianteIcone.PEQUENO,
        }
    )


def contexto_corpo_servidores(consulta: ConsultaServidores) -> dict[str, Any]:
    linhas = _linhas_de_servidores()
    return {
        "linhas": listar_servidores(linhas, consulta),
        "total_servidores": len(linhas),
    }


def _alarme_sem_direcao_do_titular(perfil: Perfil) -> str:
    # Só o titular puxa o alarme para a própria página: o afastado sem cargo de direção não
    # deixa unidade nenhuma sem quem responda por ela.
    if not perfil.e_titular:
        return ""
    substituicao = substituicao_vigente(perfil)
    substituto = substituicao.substituto if substituicao else None
    if avaliar_direcao(estado_da_direcao(perfil, substituto)) != Direcao.SEM_DIRECAO:
        return ""
    return alarme_sem_direcao(perfil.unidade, perfil)


def _cartao_do_impedimento(
    impedimento: Impedimento,
    universos: dict[str, list[Perfil]],
) -> dict[str, Any]:
    # Uma consulta pela agenda, e é dela que saem a lista, a calha e a lacuna proposta.
    agenda = list(substituicoes_do_impedimento(impedimento))
    lacuna = lacuna_proposta(impedimento, agenda)
    itens = [
        _item_de_substituicao(substituicao, impedimento, universos)
        for substituicao in agenda
    ]
    return {
        "impedimento": impedimento,
        "periodo": _texto_periodo_longo(periodo_de(impedimento)),
        "situacao": _situacao_do_impedimento(impedimento),
        "rotulo_lista": (
            ROTULO_UM_SUBSTITUTO if len(agenda) == 1 else ROTULO_VARIOS_SUBSTITUTOS
        ),
        "substituicoes": itens,
        # O vínculo existe e não vale hoje: a pergunta é sempre "há substituição vigente hoje", e
        # nunca a existência da linha.
        "alerta_sem_cobertura": (
            bool(itens)
            and vigente_em(periodo_de(impedimento), timezone.localdate())
            and not any(item["vigente"] for item in itens)
        ),
        "lacuna_texto": _texto_periodo_corrido(lacuna) if lacuna is not None else "",
        "calha": _calha(impedimento, agenda),
        "lacuna": lacuna,
        "candidatos": (
            _candidatos(impedimento, lacuna, universos, exceto=None)
            if lacuna is not None
            else None
        ),
        "modal": f"modal-designar-{impedimento.pk}",
    }


def _item_de_substituicao(
    substituicao: Substituicao,
    impedimento: Impedimento,
    universos: dict[str, list[Perfil]],
) -> dict[str, Any]:
    hoje = timezone.localdate()
    periodo = periodo_de(substituicao)
    vigente = vigente_em(periodo, hoje)
    futura = substituicao.data_inicio > hoje
    return {
        "substituicao": substituicao,
        "perfil": substituicao.substituto,
        "imagem": imagem_do_perfil(substituicao.substituto),
        "cor_unidade_hex": hex_da_cor(substituicao.substituto.cor_unidade),
        "periodo": _texto_periodo_curto(periodo),
        "vigente": vigente,
        # O que passou recua e perde as ações: substituição encerrada não se troca nem se encerra.
        "encerrada": not vigente and not futura,
        "situacao": SITUACAO_VIGENTE if vigente else "" if futura else SITUACAO_ENCERRADA,
        "candidatos": (
            None
            if not vigente and not futura
            else _candidatos(impedimento, periodo, universos, exceto=substituicao.pk)
        ),
        "modal_trocar": f"modal-trocar-{substituicao.pk}",
        "modal_encerrar": f"modal-encerrar-{substituicao.pk}",
    }


def _calha(
    impedimento: Impedimento,
    agenda: list[Substituicao],
) -> dict[str, Any]:
    # left/width em porcentagem: medida de renderização, não conhecimento de domínio — trechos()
    # devolve períodos e a régua sai daqui. Em texto já formatado porque float em template é
    # localizado (pt-br), e "14,75%" não é CSS.
    pedacos = trechos_do_impedimento(impedimento, agenda)
    # A chave admite None porque é o id do trecho descoberto que consulta este mapa.
    nomes: dict[int | None, str] = {
        substituicao.substituto_id: substituicao.substituto.nome
        for substituicao in agenda
    }
    dias = _dias_da_regua(impedimento, pedacos)
    escala = LARGURA_TOTAL if impedimento.data_fim is not None else FRACAO_REGUA_ABERTA
    entintados: list[dict[str, str]] = []
    marcas: list[dict[str, Any]] = []
    for pedaco in pedacos:
        inicio = (pedaco.periodo.inicio - impedimento.data_inicio).days / dias * escala
        largura = _largura_do_trecho(pedaco.periodo, dias, escala, inicio)
        if pedaco.substituto_id is not None:
            entintados.append(_medida(inicio, largura))
        marcas.append(
            {
                "left": f"{inicio + largura / 2:.2f}",
                "rotulo": nomes.get(pedaco.substituto_id, ROTULO_SEM_SUBSTITUTO),
                "periodo": _texto_periodo_curto(pedaco.periodo),
                "vazia": pedaco.substituto_id is None,
            }
        )
    return {
        # Prazo indeterminado: a calha não termina, se dissolve.
        "aberta": impedimento.data_fim is None,
        "trechos": entintados,
        "marcas": marcas,
    }


def _substituindo(perfil: Perfil) -> dict[str, Any] | None:
    substituicao = substituicao_que_exerce(perfil)
    if substituicao is None:
        return None
    substituido = substituicao.impedimento.perfil
    return {
        "perfil": substituido,
        "imagem": imagem_do_perfil(substituido),
        "cor_unidade_hex": hex_da_cor(substituido.cor_unidade),
        "periodo": _texto_periodo_curto(periodo_de(substituicao)),
        # O do afastamento aparece junto de propósito: é ele que explica por que a substituição
        # termina antes.
        "periodo_do_afastamento": _texto_periodo_corrido(
            periodo_de(substituicao.impedimento)
        ),
    }


def _universos_de_candidatos(perfil: Perfil) -> dict[str, list[Perfil]]:
    # As duas listas nascem renderizadas: o toggle de alcance troca qual aparece, e uma rota para
    # isso recalcularia o que não muda com o diálogo aberto. O prefetch é o que faz o avaliador
    # rodar sem uma consulta por candidato.
    servidores = list(
        Perfil.objects.exclude(pk=perfil.pk)
        .select_related("unidade", "cargo_comissao")
        .prefetch_related("impedimentos", "substituicoes_exercidas")
        .order_by("nome", "sobrenome")
    )
    return {
        "unidade": [
            candidato
            for candidato in servidores
            if candidato.unidade_id == perfil.unidade_id
        ],
        "ampliado": sorted(servidores, key=lambda c: _ordem_do_alcance(c, perfil)),
    }


def _ordem_do_alcance(candidato: Perfil, substituido: Perfil) -> int:
    # Ampliada, a lista abre pela unidade superior: é de onde a cobertura de fora costuma vir.
    if candidato.unidade_id == substituido.unidade.pai_id:
        return 0
    if candidato.unidade_id == substituido.unidade_id:
        return 1
    return 2


def _candidatos(
    impedimento: Impedimento,
    periodo: Periodo,
    universos: dict[str, list[Perfil]],
    exceto: int | None,
) -> dict[str, list[Perfil]]:
    return {
        alcance: candidatos_a_substituto(impedimento, periodo, perfis, exceto=exceto)
        for alcance, perfis in universos.items()
    }


def _dias_da_regua(impedimento: Impedimento, pedacos: tuple[Trecho, ...]) -> int:
    fim = impedimento.data_fim or _ultima_data_conhecida(pedacos)
    return ((fim or impedimento.data_inicio) - impedimento.data_inicio).days + 1


def _ultima_data_conhecida(pedacos: tuple[Trecho, ...]) -> date | None:
    conhecidas = [
        pedaco.periodo.fim for pedaco in pedacos if pedaco.periodo.fim is not None
    ]
    return max(conhecidas) if conhecidas else None


def _largura_do_trecho(
    periodo: Periodo,
    dias: int,
    escala: float,
    inicio: float,
) -> float:
    # Sem fim conhecido o trecho vai até a borda, e é a máscara da calha que o dissolve.
    if periodo.fim is None:
        return LARGURA_TOTAL - inicio
    return ((periodo.fim - periodo.inicio).days + 1) / dias * escala


def _medida(inicio: float, largura: float) -> dict[str, str]:
    return {
        "left": f"{inicio:.2f}",
        "width": f"{largura:.2f}",
    }


def _situacao_do_impedimento(impedimento: Impedimento) -> str:
    dias = (impedimento.data_inicio - timezone.localdate()).days
    if dias <= 0:
        return SITUACAO_IMPEDIMENTO_VIGENTE
    return f"começa em {dias} dia{'s' if dias > 1 else ''}"


def _texto_periodo_longo(periodo: Periodo) -> str:
    fim = periodo.fim.strftime(FORMATO_LONGO) if periodo.fim else PRAZO_INDETERMINADO
    return f"{periodo.inicio.strftime(FORMATO_LONGO)} → {fim}"


def _texto_periodo_curto(periodo: Periodo) -> str:
    if periodo.fim is None:
        return f"a partir de {periodo.inicio.strftime(FORMATO_CURTO)}"
    inicio = periodo.inicio.strftime(FORMATO_CURTO)
    return f"{inicio} → {periodo.fim.strftime(FORMATO_CURTO)}"


def _texto_periodo_corrido(periodo: Periodo) -> str:
    # A seta é da linha do tempo; dentro de uma frase, o período se lê por extenso.
    if periodo.fim is None:
        return f"a partir de {periodo.inicio.strftime(FORMATO_CURTO)}"
    inicio = periodo.inicio.strftime(FORMATO_CURTO)
    return f"de {inicio} a {periodo.fim.strftime(FORMATO_CURTO)}"


def _catalogos_de_lotacao(ids_permitidos: Collection[int] | None = None) -> dict[str, Any]:
    return catalogo_de_unidades(ids_permitidos) | {
        "cargos_base": CargoBase.objects.order_by("nome"),
        "cargos_comissao": CargoComissao.objects.order_by("nome"),
    }


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
        unidade_pk=perfil.unidade_id,
        cor_unidade=hex_da_cor(perfil.cor_unidade),
        cargo=perfil.cargo_base.nome,
        comissao=perfil.cargo_comissao.nome if perfil.cargo_comissao else SEM_CARGO_COMISSAO,
        impedido=perfil.esta_impedido,
    )
