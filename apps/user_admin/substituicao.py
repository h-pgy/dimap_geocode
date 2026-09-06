"""
Atos e leituras de substituição (SPEC user_admin/024): designar, trocar, encerrar e leituras da
cobertura — módulo próprio que recebe de `exercicio.py` os atos e leituras de substituição.
Uma porta pública por ato: ela confere o alcance, chama a escrita privada e traduz a recusa.
"""

from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Protocol

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.core.erros_formulario import de_validation_error
from apps.user_admin.formularios import traduzir_recusa_substituicao
from apps.user_admin.models import Impedimento, Perfil, Substituicao, q_em_aberto_em, q_vigente_em
from apps.user_admin.schemas import NovaSubstituicao, TrocaDeSubstituto
from services.domain.exercicio import (
    Designacao,
    Periodo,
    Substituido,
    Substituto,
    Trecho,
    avaliar_designacao,
    lacunas,
    trechos,
)
from services.utils.erros_formulario import ErroBruto, RecusaDeFormulario

DIA = timedelta(days=1)

ERRO_SUBSTITUTO_FORA_DO_ALCANCE = (
    "Servidor: fora do seu alcance — só quem está no seu ramo pode ser designado."
)


class TemPeriodo(Protocol):
    """Impedimento e substituição partilham a convenção de período — e é só isso que a montagem
    dos DTOs precisa saber sobre eles."""

    data_inicio: date
    data_fim: date | None


@dataclass(frozen=True)
class DesfechoSubstituicao:
    """Recado do ato para a view — mesma natureza do `DesfechoAdministrador` de `administrador.py`.
    Ou a cobertura gravada, ou a recusa que a tela mostra: nunca as duas, nunca nenhuma."""

    substituicao: Substituicao | None
    recusa: RecusaDeFormulario = RecusaDeFormulario()


# ---------------------------------------------------------------------------
# Portas públicas dos atos
# ---------------------------------------------------------------------------


def designar_substituto(
    impedimento: Impedimento,
    dados: NovaSubstituicao,
    alcance: Collection[int] | None = None,
) -> DesfechoSubstituicao:
    """Porta única — quem grava uma designação passa por aqui, e por aqui passa a conferência."""
    if alcance is not None:
        recusa = recusa_de_substituto_fora_do_alcance(dados.substituto, alcance)
        if recusa is not None:
            return DesfechoSubstituicao(substituicao=None, recusa=recusa)
    return _desfecho(lambda: _gravar_designacao(impedimento, dados))


def trocar_substituto(
    atual: Substituicao,
    dados: TrocaDeSubstituto,
    alcance: Collection[int] | None = None,
) -> DesfechoSubstituicao:
    """Mesmo desfecho e mesma conferência."""
    if alcance is not None:
        recusa = recusa_de_substituto_fora_do_alcance(dados.substituto, alcance)
        if recusa is not None:
            return DesfechoSubstituicao(substituicao=None, recusa=recusa)
    return _desfecho(lambda: _gravar_troca(atual, dados))


def encerrar_substituicao(substituicao: Substituicao) -> None:
    """Em curso, termina hoje e fica registrada; ainda não iniciada, é apagada — registro sem fato
    não é histórico."""
    with transaction.atomic():
        encerrar_substituicao_em(substituicao, timezone.localdate())


def encerrar_substituicao_em(substituicao: Substituicao, dia: date) -> None:
    """Público porque `retornar_ao_exercicio` trunca por aqui as coberturas em curso — é a única
    coisa que `exercicio.py` pede a este módulo, e o que mantém a dependência de mão única."""
    if dia < substituicao.data_inicio:
        substituicao.delete()
        return
    substituicao.data_fim = dia
    substituicao.save(update_fields=["data_fim"])


# ---------------------------------------------------------------------------
# Escritas privadas e conferência de alcance
# ---------------------------------------------------------------------------


def recusa_de_substituto_fora_do_alcance(
    substituto_id: int,
    alcance: Collection[int],
) -> RecusaDeFormulario | None:
    """A regra que prende a designação ao ramo de quem assina. Mora aqui, e não em cada ato: designar
    e trocar escrevem o mesmo vínculo, e a regra escrita duas vezes divergiria na primeira mudança."""
    lotacao = Perfil.objects.filter(pk=substituto_id).values_list("unidade_id", flat=True).first()
    if lotacao is not None and lotacao in alcance:
        return None
    return traduzir_recusa_substituicao(
        (
            ErroBruto(
                controle="substituto",
                tipo="fora_do_alcance",
                mensagem=ERRO_SUBSTITUTO_FORA_DO_ALCANCE,
            ),
        )
    )


def _gravar_designacao(impedimento: Impedimento, dados: NovaSubstituicao) -> Substituicao:
    """A escrita que LEVANTA, privada do módulo. É o `full_clean` que recusa a designação inválida,
    e é o levantar dele que a troca usa para abortar a transação."""
    with transaction.atomic():
        periodo = _periodo_da_designacao(impedimento, dados)
        substituicao = Substituicao(
            impedimento=impedimento,
            substituto=Perfil.objects.get(pk=dados.substituto),
            data_inicio=periodo.inicio,
            data_fim=periodo.fim,
        )
        substituicao.full_clean()
        substituicao.save()
        return substituicao


def _gravar_troca(atual: Substituicao, dados: TrocaDeSubstituto) -> Substituicao:
    with transaction.atomic():
        # A véspera primeiro, e a designação depois: se a nova não colar, o `full_clean` levanta
        # daqui de dentro e o `atomic` desfaz a véspera.
        encerrar_substituicao_em(atual, dados.data_inicio - DIA)
        return _gravar_designacao(
            atual.impedimento,
            NovaSubstituicao(
                substituto=dados.substituto,
                data_inicio=dados.data_inicio,
                data_fim=dados.data_fim,
            ),
        )


def _desfecho(escrever: Callable[[], Substituicao]) -> DesfechoSubstituicao:
    try:
        return DesfechoSubstituicao(substituicao=escrever())
    except DjangoValidationError as erro:
        return DesfechoSubstituicao(
            substituicao=None,
            recusa=traduzir_recusa_substituicao(de_validation_error(erro)),
        )


# ---------------------------------------------------------------------------
# Leituras da cobertura
# ---------------------------------------------------------------------------


def substituicao_vigente(perfil: Perfil) -> Substituicao | None:
    """Quem cobre este perfil hoje. É o que a SPEC 016 compõe com o titular da unidade."""
    return (
        Substituicao.objects.filter(
            q_vigente_em(timezone.localdate()),
            impedimento__perfil=perfil,
        )
        .select_related("substituto", "substituto__unidade", "impedimento__tipo")
        .first()
    )


def substituicao_que_exerce(perfil: Perfil) -> Substituicao | None:
    """Quem este perfil está substituindo hoje — no máximo uma, pela não-sobreposição, e é o outro
    lado da mesma leitura."""
    return (
        Substituicao.objects.filter(
            q_vigente_em(timezone.localdate()),
            substituto=perfil,
        )
        .select_related(
            "impedimento__tipo",
            "impedimento__perfil",
            "impedimento__perfil__unidade",
            "impedimento__perfil__cargo_comissao",
        )
        .first()
    )


def substituicoes_do_impedimento(impedimento: Impedimento) -> QuerySet[Substituicao]:
    """A agenda do afastamento, em ordem — encerradas, vigente e futuras. É o histórico da tela, e
    ele não precisa de tabela nenhuma além desta."""
    return impedimento.substituicoes.order_by("data_inicio").select_related(
        "substituto",
        "substituto__unidade",
    )


def trechos_do_impedimento(
    impedimento: Impedimento,
    agenda: Iterable[Substituicao],
) -> tuple[Trecho, ...]:
    """O afastamento fatiado em cobertos e descobertos — o que a calha desenha, em períodos; a
    conversão para porcentagem é da orquestração. A agenda vem de fora para a tela não perguntá-la
    de novo a cada peça que a consome."""
    ocupados = tuple(
        Trecho(
            periodo=periodo_de(substituicao),
            substituto_id=substituicao.substituto_id,
        )
        for substituicao in agenda
    )
    return trechos(periodo_de(impedimento), ocupados)


def lacuna_proposta(
    impedimento: Impedimento,
    agenda: Iterable[Substituicao],
) -> Periodo | None:
    """O primeiro pedaço descoberto — o que o diálogo de designar já traz nos campos de data."""
    ocupados = tuple(periodo_de(substituicao) for substituicao in agenda)
    descobertos = lacunas(periodo_de(impedimento), ocupados)
    return descobertos[0] if descobertos else None


def candidatos_a_substituto(
    impedimento: Impedimento,
    periodo: Periodo,
    universo: Iterable[Perfil],
    exceto: int | None = None,
) -> list[Perfil]:
    """Quem, do universo que a tela oferece, passaria no avaliador para este período. A mesma
    montagem de DTO que o clean usa — se a tela montasse a sua, "a mesma regra nos dois lugares"
    viraria promessa. Quem escolhe e ordena o universo é a orquestração: filtrar é UX.

    `exceto` é a substituição que está sendo trocada: ela não conta contra si mesma."""
    substituido = _substituido_de(impedimento.perfil, exceto=exceto)
    periodo_do_impedimento = periodo_de(impedimento)
    return [
        perfil
        for perfil in universo
        if avaliar_designacao(
            Designacao(
                periodo=periodo,
                periodo_do_impedimento=periodo_do_impedimento,
                substituido=substituido,
                substituto=_substituto_de(perfil, exceto=exceto),
            )
        )
    ]


def designacao_de(substituicao: Substituicao) -> Designacao:
    """A montagem que o `clean()` e a lista de candidatos partilham. A própria substituição fica de
    fora das listas de períodos: senão ela conflitaria consigo mesma."""
    impedimento = substituicao.impedimento
    return Designacao(
        periodo=periodo_de(substituicao),
        periodo_do_impedimento=periodo_de(impedimento),
        substituido=_substituido_de(impedimento.perfil, exceto=substituicao.pk),
        substituto=_substituto_de(substituicao.substituto, exceto=substituicao.pk),
    )


def periodo_de(registro: TemPeriodo) -> Periodo:
    return Periodo(inicio=registro.data_inicio, fim=registro.data_fim)


def _periodo_da_designacao(
    impedimento: Impedimento,
    dados: NovaSubstituicao,
) -> Periodo:
    if dados.data_inicio is not None:
        return Periodo(inicio=dados.data_inicio, fim=dados.data_fim)
    agenda = substituicoes_do_impedimento(impedimento)
    return lacuna_proposta(impedimento, agenda) or periodo_de(impedimento)


def _substituido_de(perfil: Perfil, exceto: int | None) -> Substituido:
    recebidas = Substituicao.objects.filter(impedimento__perfil_id=perfil.pk)
    if exceto is not None:
        recebidas = recebidas.exclude(pk=exceto)
    return Substituido(
        perfil_id=perfil.pk,
        exonerado=perfil.exonerado,
        tem_cargo_comissao=perfil.cargo_comissao_id is not None,
        substituicoes_recebidas=tuple(periodo_de(recebida) for recebida in recebidas),
    )


def _substituto_de(perfil: Perfil, exceto: int | None) -> Substituto:
    return Substituto(
        perfil_id=perfil.pk,
        exonerado=perfil.exonerado,
        impedimentos=tuple(
            periodo_de(impedimento) for impedimento in perfil.impedimentos.all()
        ),
        substituicoes_exercidas=tuple(
            periodo_de(exercida)
            for exercida in perfil.substituicoes_exercidas.all()
            if exercida.pk != exceto
        ),
    )
