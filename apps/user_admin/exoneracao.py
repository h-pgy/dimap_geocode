"""
O ato que tira um servidor do quadro da DIMAP — e o que o reintegra (SPEC user_admin/027). A
exoneração larga, numa transação só, a titularidade, os impedimentos em aberto, as coberturas das
duas pontas, as delegações recebidas e a condição de administrador; a reintegração devolve só o
acesso. A projeção model → DTO mora aqui também, e não no domínio, que não conhece `Perfil` — mesmo
padrão de `apps/unidades/extincao.py` (SPEC user_admin/025).
"""

from dataclasses import dataclass
from datetime import date

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.unidades.titularidade import destituir_titular
from apps.user_admin.exercicio import encerrar_impedimentos, impedimentos_em_aberto
from apps.user_admin.formularios import traduzir_recusa
from apps.user_admin.models import Perfil, Substituicao, q_em_aberto_em
from apps.user_admin.schemas import ComandoExoneracao
from apps.user_admin.substituicao import encerrar_substituicao_em
from services.domain.exoneracao import (
    IdentidadeServidor,
    PreviaDaExoneracao,
    PreviaDaReintegracao,
    avaliar_exoneracao,
    avaliar_reintegracao,
)
from services.utils.erros_formulario import ErroBruto, RecusaDeFormulario


@dataclass(frozen=True)
class DesfechoExoneracao:
    """Mesma forma do `DesfechoAdministrador` (SPEC 022): gravou (`perfil`) ou recusou (`recusa`).
    Serve às duas operações — o que muda entre elas é o que a transação faz, não o recado à view."""

    perfil: Perfil | None
    recusa: RecusaDeFormulario = RecusaDeFormulario()


def previa_da_exoneracao(servidor: Perfil, autor_id: int) -> PreviaDaExoneracao:
    # Importado aqui dentro, como em `competencias/consulta.py`: `competencias` já importa
    # `user_admin` no topo, e o import de módulo fecharia o ciclo.
    from apps.competencias.models.delegacao import Delegacao

    hoje = timezone.localdate()
    return PreviaDaExoneracao(
        servidor=_identidade(servidor),
        unidade_que_dirige=servidor.unidade.sigla if servidor.e_titular else None,
        impedimentos_em_aberto=impedimentos_em_aberto(servidor).count(),
        coberturas_em_curso=Substituicao.objects.filter(
            q_em_aberto_em(hoje), substituto=servidor
        ).count(),
        delegacoes_recebidas=Delegacao.objects.filter(
            q_em_aberto_em(hoje), delegado=servidor
        ).count(),
        administrador=servidor.is_superuser,
        ja_exonerado=servidor.exonerado,
        eh_o_proprio_autor=servidor.pk == autor_id,
    )


def previa_da_reintegracao(servidor: Perfil) -> PreviaDaReintegracao:
    return PreviaDaReintegracao(
        servidor=_identidade(servidor),
        exonerado_em=servidor.exonerado_em,
        unidade=servidor.unidade.sigla,
        unidade_extinta=servidor.unidade.extinta_em is not None,
        ja_no_quadro=not servidor.exonerado,
    )


def _identidade(servidor: Perfil) -> IdentidadeServidor:
    return IdentidadeServidor(
        servidor_id=servidor.pk, rf=servidor.rf, nome_completo=servidor.nome_completo
    )


def exonerar_servidor(comando: ComandoExoneracao, hoje: date) -> DesfechoExoneracao:
    servidor = get_object_or_404(Perfil.objects.select_related("unidade"), pk=comando.servidor_id)
    veredito = avaliar_exoneracao(previa_da_exoneracao(servidor, autor_id=comando.autor_id))
    if not veredito.pode:
        return DesfechoExoneracao(perfil=None, recusa=_recusa(veredito.motivo))
    with transaction.atomic():
        # Primeiro: enquanto a marca estiver de pé, a `UniqueConstraint` de um titular por unidade
        # recusa a designação do próximo, e a unidade fica travada sem direção. É a destituição da
        # SPEC 026 que leva junto as delegações FEITAS por ele e as substituições da titularidade.
        if servidor.e_titular:
            destituir_titular(servidor.unidade)
        # Hoje, e não a véspera: o afastamento valeu até o dia em que a pessoa saiu do quadro. O
        # que ainda não vigorou é apagado lá dentro, e as coberturas caem junto.
        encerrar_impedimentos(impedimentos_em_aberto(servidor), hoje)
        _encerrar_coberturas_exercidas(servidor, hoje)
        _encerrar_delegacoes_recebidas(servidor, hoje)
        servidor.is_superuser = False
        servidor.is_staff = False
        servidor.is_active = False
        servidor.exonerado_em = hoje
        servidor.save(
            update_fields=[
                "is_superuser",
                "is_staff",
                "is_active",
                "exonerado_em",
            ],
        )
    return DesfechoExoneracao(perfil=servidor)


def reintegrar_servidor(comando: ComandoExoneracao) -> DesfechoExoneracao:
    """O reverso devolve o acesso e nada mais: titularidade, cobertura, delegação e caneta de
    administrador se refazem por seus próprios atos."""
    servidor = get_object_or_404(Perfil.objects.select_related("unidade"), pk=comando.servidor_id)
    veredito = avaliar_reintegracao(previa_da_reintegracao(servidor))
    if not veredito.pode:
        return DesfechoExoneracao(perfil=None, recusa=_recusa(veredito.motivo))
    servidor.is_active = True
    servidor.exonerado_em = None
    servidor.save(update_fields=["is_active", "exonerado_em"])
    return DesfechoExoneracao(perfil=servidor)


def _encerrar_coberturas_exercidas(servidor: Perfil, dia: date) -> None:
    # A outra ponta da substituição: as que ele EXERCE sobre o impedimento de terceiros. As do
    # próprio impedimento dele caem com o impedimento, em `encerrar_impedimentos`.
    for substituicao in Substituicao.objects.filter(q_em_aberto_em(dia), substituto=servidor):
        encerrar_substituicao_em(substituicao, dia)


def _encerrar_delegacoes_recebidas(servidor: Perfil, dia: date) -> None:
    # A outra ponta da delegação: as que ele RECEBEU. As que ele fez como titular caem com a
    # destituição (SPEC 026), e as duas pontas nunca se sobrepõem.
    # Importado aqui dentro, como em `competencias/consulta.py`: `competencias` já importa
    # `user_admin` no topo, e o import de módulo fecharia o ciclo.
    from apps.competencias.models.delegacao import Delegacao

    Delegacao.objects.filter(q_em_aberto_em(dia), delegado=servidor).update(data_fim=dia)


def _recusa(motivo: str) -> RecusaDeFormulario:
    return traduzir_recusa((ErroBruto(controle="servidor", tipo="veredito", mensagem=motivo),))
