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
from apps.user_admin.schemas import NovoImpedimento
from apps.user_admin.substituicao import (
    candidatos_a_substituto,
    designacao_de,
    designar_substituto,
    encerrar_substituicao,
    encerrar_substituicao_em,
    lacuna_proposta,
    periodo_de,
    substituicao_que_exerce,
    substituicao_vigente,
    substituicoes_do_impedimento,
    trechos_do_impedimento,
    trocar_substituto,
)

DIA = timedelta(days=1)


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


def retornar_ao_exercicio(perfil: Perfil) -> None:
    """Encerra na VÉSPERA de hoje TODOS os impedimentos vigentes — encerrar um só deixaria a pessoa
    fora pelo outro — e acerta as substituições: trunca a que está em curso, apaga as que não
    começaram. O que ainda não vigorou é apagado, não encerrado (SPEC user_admin/023).

    A véspera, e não hoje: o período é inclusivo no fim, então um impedimento que termina hoje ainda
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
            encerrar_substituicao_em(substituicao, ontem)
        # Um a um, e não em massa: o que começa hoje não tem data anterior ao início para gravar, e
        # cada um decide entre ser encurtado e ser apagado.
        for impedimento in vigentes:
            _encerrar_impedimento_em(impedimento, ontem)


def retorno_eh_revogacao(perfil: Perfil) -> bool:
    """Verdadeiro quando TODO impedimento que vale hoje começa hoje: nenhum chegou a vigorar, e
    encerrá-los é apagá-los. Falso quando algum começou antes — aí houve saída do exercício, e o ato
    devolve a cadeira. Falso também sem impedimento algum: não há o que revogar.

    É a pergunta que a tela faz para escolher a face, e a que o ato faz para nomear a operação."""
    hoje = timezone.localdate()
    inicios_dos_vigentes = Impedimento.objects.filter(
        q_vigente_em(hoje),
        perfil=perfil,
    ).values_list("data_inicio", flat=True)
    nenhum_vigorou = all(inicio == hoje for inicio in inicios_dos_vigentes)
    return bool(inicios_dos_vigentes) and nenhum_vigorou


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


def _encerrar_impedimento_em(impedimento: Impedimento, dia: date) -> None:
    # Mesma regra de `_encerrar_em`: encerrar antes do próprio início não é encurtar, é dizer que o
    # impedimento nunca vigorou. O CASCADE leva as substituições dele junto.
    if dia < impedimento.data_inicio:
        impedimento.delete()
        return
    impedimento.data_fim = dia
    impedimento.save(update_fields=["data_fim"])

