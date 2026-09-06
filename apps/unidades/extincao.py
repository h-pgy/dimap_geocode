"""
O ato de extinguir e reativar unidade (SPEC user_admin/025): uma transação por operação, e a recusa
da hierarquia traduzida na mesma forma dos outros atos de unidade. A projeção model → DTO mora aqui
também, e não no domínio, que não conhece `Unidade`: o modal e o ato fazem a mesma pergunta ao
banco, e é daqui que `context.py` a importa para montar a face.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.core.erros_formulario import de_validation_error
from apps.competencias.models import Concessao
from apps.unidades.formularios import ler_ato_de_unidade, recusa_do_veredito, traduzir_recusa
from apps.unidades.models import Unidade
from services.domain.extincao_unidade import (
    IdentidadeUnidade,
    PreviaDaExtincao,
    PreviaDaReativacao,
    avaliar_extincao,
    avaliar_reativacao,
)
from services.utils.erros_formulario import RecusaDeFormulario


@dataclass(frozen=True)
class DesfechoExtincao:
    """Mesma forma do `DesfechoUnidade` (SPEC 020): gravou (`unidade`) ou recusou (`recusa`). Serve
    às duas operações — o que muda entre elas é o que a transação faz, não o recado à view."""

    unidade: Unidade | None
    destino: Unidade | None = None
    recusa: RecusaDeFormulario = RecusaDeFormulario()


def previa_da_extincao(unidade: Unidade) -> PreviaDaExtincao:
    destino = unidade.pai
    return PreviaDaExtincao(
        unidade=_identidade(unidade),
        destino=_identidade(destino) if destino is not None else None,
        # `filhas` conta só as vigentes, e é a mesma leitura que `_subir_filhas` faz: a prévia não
        # promete transferir a subordinada já extinta, que não vai sair do lugar.
        servidores=unidade.perfis.count(),
        subordinadas=unidade.filhas.count(),
        ja_extinta=unidade.extinta_em is not None,
    )


def previa_da_reativacao(unidade: Unidade) -> PreviaDaReativacao:
    # `unidade.pai` é acesso de FK, que resolve pelo `_base_manager` (`todas`): a superior extinta
    # precisa CHEGAR aqui para que o veredito possa nomear a sigla que se reativa primeiro.
    # Nunca nulo: raiz não se extingue (`CheckConstraint`), logo o que se reativa sempre tem pai —
    # e é por isso que `PreviaDaReativacao.superior` não é opcional.
    superior = unidade.pai
    assert superior is not None, "raiz não se extingue (CheckConstraint): sempre há um pai aqui"
    atribuicoes = unidade.atribuicoes.filter(extinta_em=unidade.extinta_em)
    return PreviaDaReativacao(
        unidade=_identidade(unidade),
        superior=_identidade(superior),
        superior_extinta=superior.extinta_em is not None,
        atribuicoes=atribuicoes.count(),
        concessoes=Concessao.objects.filter(
            atribuicao__in=atribuicoes,
            extinta_em=unidade.extinta_em,
        ).count(),
        ja_vigente=unidade.extinta_em is None,
    )


def _identidade(unidade: Unidade) -> IdentidadeUnidade:
    return IdentidadeUnidade(unidade_id=unidade.pk, sigla=unidade.sigla)


def extinguir_unidade(valores: Mapping[str, Any], hoje: date) -> DesfechoExtincao:
    leitura = ler_ato_de_unidade(valores)
    if leitura.dto is None:
        return DesfechoExtincao(unidade=None, recusa=leitura.recusa or RecusaDeFormulario())
    unidade = get_object_or_404(
        Unidade.todas.select_related("pai"), pk=leitura.dto.unidade_id
    )
    veredito = avaliar_extincao(previa_da_extincao(unidade))
    if not veredito.pode:
        return DesfechoExtincao(unidade=None, recusa=recusa_do_veredito(veredito.motivo))
    destino = unidade.pai
    # O próprio veredito já confirmou: `avaliar_extincao` só passa quando `previa.destino` (o mesmo
    # `unidade.pai`) não é nulo.
    assert destino is not None
    try:
        with transaction.atomic():
            # As filhas primeiro: é a única etapa que pode recusar, e recusar depois de mover
            # servidor obrigaria a transação a desfazer trabalho que ninguém precisava ter feito.
            _subir_filhas(unidade, destino)
            _transferir_servidores(unidade, destino)
            _extinguir_competencias(unidade, hoje)
            _encerrar_delegacoes(unidade, hoje)
            unidade.extinta_em = hoje
            unidade.save(update_fields=["extinta_em"])
    except ValidationError as recusa:
        return DesfechoExtincao(unidade=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    return DesfechoExtincao(unidade=unidade, destino=destino)


def reativar_unidade(valores: Mapping[str, Any]) -> DesfechoExtincao:
    leitura = ler_ato_de_unidade(valores)
    if leitura.dto is None:
        return DesfechoExtincao(unidade=None, recusa=leitura.recusa or RecusaDeFormulario())
    unidade = get_object_or_404(
        Unidade.todas.select_related("pai"), pk=leitura.dto.unidade_id
    )
    veredito = avaliar_reativacao(previa_da_reativacao(unidade))
    if not veredito.pode:
        return DesfechoExtincao(unidade=None, recusa=recusa_do_veredito(veredito.motivo))
    # Lida ANTES de zerar o campo: é a chave de tudo que a restauração vai procurar.
    extinta_em = unidade.extinta_em
    try:
        with transaction.atomic():
            unidade.extinta_em = None
            # Entre a extinção e agora o tipo do superior pode ter mudado: quem barra é a mesma
            # validação de hierarquia que barra na criação.
            unidade.full_clean()
            unidade.save(update_fields=["extinta_em"])
            _restaurar_competencias(unidade, extinta_em)
    except ValidationError as recusa:
        return DesfechoExtincao(unidade=None, recusa=traduzir_recusa(de_validation_error(recusa)))
    return DesfechoExtincao(unidade=unidade, destino=unidade.pai)


def _subir_filhas(unidade: Unidade, destino: Unidade) -> None:
    # `filhas` lê pelo gerente PADRÃO, então a subordinada já extinta não sobe — e é de propósito:
    # o `pai` dela é a memória de onde ela volta, e repontá-la devolveria, na reativação, uma
    # unidade a um lugar em que ela nunca esteve. Trocar por `Unidade.todas.filter(pai=...)` parece
    # inofensivo e quebra isso em silêncio.
    # Uma a uma, com `full_clean`: nível e tipo vedado são regras de `Unidade.clean()` e nenhum
    # `update()` em massa as cobra.
    for filha in unidade.filhas.all():
        filha.pai = destino
        filha.full_clean()
        filha.save(update_fields=["pai"])


def _transferir_servidores(unidade: Unidade, destino: Unidade) -> None:
    # A titularidade cai no mesmo `update`: o vínculo é com a unidade que deixou de existir, e a
    # unicidade de um titular por unidade barraria o segundo marcado no destino.
    unidade.perfis.update(unidade=destino, e_titular=False)


def _extinguir_competencias(unidade: Unidade, hoje: date) -> None:
    """O que a unidade fazia sai com ela, nos dois níveis. A data é a mesma da unidade: é por ela
    que a reativação reconhece o que caiu junto."""
    atribuicoes = unidade.atribuicoes.filter(extinta_em__isnull=True)
    Concessao.objects.filter(atribuicao__in=atribuicoes, extinta_em__isnull=True).update(
        extinta_em=hoje
    )
    atribuicoes.update(extinta_em=hoje)


def _restaurar_competencias(unidade: Unidade, extinta_em: date | None) -> None:
    """Só o que caiu NAQUELE ato: a data é o que separa a atribuição extinta com a unidade da que foi
    retirada por ato próprio — essa última nem existe mais, porque retirar apaga a linha."""
    atribuicoes = unidade.atribuicoes.filter(extinta_em=extinta_em)
    Concessao.objects.filter(atribuicao__in=atribuicoes, extinta_em=extinta_em).update(
        extinta_em=None
    )
    atribuicoes.update(extinta_em=None)


def _encerrar_delegacoes(unidade: Unidade, hoje: date) -> None:
    """Vigente encerra hoje; a que ainda não começou é apagada — mesmo tratamento que a SPEC 023 dá
    ao impedimento que nunca vigorou, e pelo mesmo motivo: encerrar antes do início é recusado pelo
    `CheckConstraint`."""
    vigentes = unidade.delegacoes.filter(data_inicio__lte=hoje)
    vigentes.filter(Q(data_fim__isnull=True) | Q(data_fim__gt=hoje)).update(data_fim=hoje)
    unidade.delegacoes.filter(data_inicio__gt=hoje).delete()
