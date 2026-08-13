"""
Atos e leituras de exercício e substituição (SPEC user_admin/015): registrar impedimento, designar,
encerrar, trocar e voltar ao exercício — funções em transação, e há um caminho só para cada
escrita, como nos atos de titularidade (SPEC 014). Aqui também mora a montagem dos DTOs de domínio
a partir do banco, partilhada pelo `clean()` da substituição e pela lista de candidatos da tela.

Exercício não é ato nem coluna: quem está na cadeira é `Perfil.em_exercicio`, leitura derivada do
impedimento vigente e da exoneração.
"""

from collections.abc import Iterable
from datetime import date, timedelta
from typing import Protocol

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

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

from apps.user_admin.models import (
    Impedimento,
    Perfil,
    Substituicao,
    TipoImpedimento,
    q_em_aberto_em,
    q_vigente_em,
)
from apps.user_admin.schemas import NovaSubstituicao, NovoImpedimento, TrocaDeSubstituto

DIA = timedelta(days=1)


class TemPeriodo(Protocol):
    """Impedimento e substituição partilham a convenção de período — e é só isso que a montagem
    dos DTOs precisa saber sobre eles."""

    data_inicio: date
    data_fim: date | None


# ---------------------------------------------------------------------------
# Atos
# ---------------------------------------------------------------------------


def registrar_impedimento(perfil: Perfil, dados: NovoImpedimento) -> Impedimento:
    """Grava o impedimento — que é, ele próprio, a saída do exercício, na data que ele declara."""
    with transaction.atomic():
        impedimento = Impedimento(
            perfil=perfil,
            tipo=TipoImpedimento.objects.get(pk=dados.tipo),
            data_inicio=dados.data_inicio,
            data_fim=dados.data_fim,
        )
        impedimento.full_clean()
        impedimento.save()
        return impedimento


def designar_substituto(
    impedimento: Impedimento,
    dados: NovaSubstituicao,
) -> Substituicao:
    """Período em branco vira a primeira lacuna do afastamento — o impedimento inteiro quando não há
    nenhuma outra substituição, inclusive com o fim nulo."""
    with transaction.atomic():
        periodo = _periodo_da_designacao(impedimento, dados)
        substituicao = Substituicao(
            impedimento=impedimento,
            substituto=Perfil.objects.get(pk=dados.substituto),
            data_inicio=periodo.inicio,
            data_fim=periodo.fim,
        )
        # É o clean que recusa a designação inválida: a regra cruza linha e tabela (§ Contexto).
        substituicao.full_clean()
        substituicao.save()
        return substituicao


def encerrar_substituicao(substituicao: Substituicao) -> None:
    """Em curso, termina hoje e fica registrada; ainda não iniciada, é apagada — registro sem fato
    não é histórico."""
    with transaction.atomic():
        _encerrar_em(substituicao, timezone.localdate())


def trocar_substituto(atual: Substituicao, dados: TrocaDeSubstituto) -> Substituicao:
    """Encerra a atual na VÉSPERA do dia em que a nova assume e designa a nova, na mesma transação.
    A véspera é o que evita tanto o dia com dois respondendo quanto a lacuna de um dia."""
    with transaction.atomic():
        # A véspera primeiro: a nova é validada contra a anterior já encurtada, senão as duas
        # colidiriam justamente no dia da troca.
        _encerrar_em(atual, dados.data_inicio - DIA)
        return designar_substituto(
            atual.impedimento,
            NovaSubstituicao(
                substituto=dados.substituto,
                data_inicio=dados.data_inicio,
                data_fim=dados.data_fim,
            ),
        )


def retornar_ao_exercicio(perfil: Perfil) -> None:
    """Encerra na VÉSPERA de hoje TODOS os impedimentos vigentes — encerrar um só deixaria a pessoa
    fora pelo outro — e acerta as substituições: trunca a que está em curso, apaga as que não
    começaram.

    A véspera, e não hoje: o período é inclusivo no fim, então um afastamento que termina hoje ainda
    vale hoje, e o botão teria mentido — quem volta ao exercício volta agora, não amanhã."""
    hoje = timezone.localdate()
    ontem = hoje - DIA
    with transaction.atomic():
        vigentes = Impedimento.objects.filter(q_vigente_em(hoje), perfil=perfil)
        # Só as em aberto: encerrar uma que já terminou a alongaria até ontem.
        for substituicao in Substituicao.objects.filter(
            q_em_aberto_em(hoje),
            impedimento__in=vigentes,
        ):
            _encerrar_em(substituicao, ontem)
        # Um a um, e não em massa: o afastamento que começou HOJE não pode terminar ontem, e aí o
        # retorno só vale a partir de amanhã — nenhuma data anterior ao início existe para gravar.
        for impedimento in vigentes:
            impedimento.data_fim = max(ontem, impedimento.data_inicio)
            impedimento.save(update_fields=["data_fim"])


# ---------------------------------------------------------------------------
# Leituras — "está substituído" é sempre "há substituição vigente hoje"
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


def impedimentos_em_aberto(perfil: Perfil) -> QuerySet[Impedimento]:
    """O vigente e os que ainda vêm: é sobre estes que a seção monta cartão e oferece designar."""
    return (
        Impedimento.objects.filter(
            q_em_aberto_em(timezone.localdate()),
            perfil=perfil,
        )
        .select_related("tipo")
        .order_by("data_inicio")
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
    # Início em branco significa "o pedaço descoberto"; informado, as datas valem como vieram, e é
    # o clean que recusa o que não couber no afastamento.
    if dados.data_inicio is not None:
        return Periodo(inicio=dados.data_inicio, fim=dados.data_fim)
    agenda = substituicoes_do_impedimento(impedimento)
    return lacuna_proposta(impedimento, agenda) or periodo_de(impedimento)


def _encerrar_em(substituicao: Substituicao, dia: date) -> None:
    # Encerrar antes do próprio início não é encurtar: é dizer que a cobertura nunca vigorou.
    if dia < substituicao.data_inicio:
        substituicao.delete()
        return
    # Sem full_clean: encurtar uma cobertura nunca cria sobreposição.
    substituicao.data_fim = dia
    substituicao.save(update_fields=["data_fim"])


def _substituido_de(perfil: Perfil, exceto: int | None) -> Substituido:
    recebidas = Substituicao.objects.filter(impedimento__perfil=perfil)
    if exceto is not None:
        recebidas = recebidas.exclude(pk=exceto)
    return Substituido(
        perfil_id=perfil.pk,
        exonerado=perfil.exonerado,
        tem_cargo_comissao=perfil.cargo_comissao_id is not None,
        substituicoes_recebidas=tuple(periodo_de(recebida) for recebida in recebidas),
    )


def _substituto_de(perfil: Perfil, exceto: int | None) -> Substituto:
    # `.all()` com o filtro em Python: assim a lista de candidatos aproveita o prefetch_related da
    # orquestração em vez de disparar duas consultas por pessoa.
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
