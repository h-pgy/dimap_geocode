"""
A borda que traduz banco → DTO do avaliador de competência (SPEC autorizacao/003): monta as
canetas do perfil, as concessões das unidades delas e os slugs estruturais, numa passagem só —
custo fixo, independente de quantas ações serão perguntadas depois (SPEC autorizacao/003, Caveats).
"""

from apps.competencias.models import Concessao
from apps.competencias.registro import REGISTRO
from apps.user_admin.context import _estado_da_direcao
from apps.user_admin.exercicio import substituicao_que_exerce, substituicao_vigente
from apps.user_admin.models import Perfil, Unidade
from services.domain.autorizacao import (
    AvaliacaoCompetenciaInput,
    Caneta,
    ConcessaoVigente,
    PerfilCompetencia,
)
from services.domain.titularidade import Direcao, avaliar_direcao


def montar_avaliacao(perfil: Perfil) -> AvaliacaoCompetenciaInput:
    """Canetas do perfil, concessões das unidades dessas canetas e os slugs estruturais — custo
    fixo, independente de quantas ações serão perguntadas depois."""
    canetas = canetas_do_perfil(perfil)
    unidades_das_canetas = frozenset(caneta.unidade_id for caneta in canetas)
    concessoes = tuple(
        ConcessaoVigente(
            acao_slug=concessao.atribuicao.acao.slug,
            acao_ativa=concessao.atribuicao.acao.ativa,
            unidade_id=concessao.atribuicao.unidade_id,
            cargo_base_id=concessao.cargo_base_id,
            cargo_comissao_id=concessao.cargo_comissao_id,
        )
        for concessao in Concessao.objects.filter(
            atribuicao__unidade_id__in=unidades_das_canetas
        ).select_related("atribuicao__acao")
    )
    return AvaliacaoCompetenciaInput(
        perfil=PerfilCompetencia(em_exercicio=perfil.em_exercicio, canetas=canetas),
        concessoes=concessoes,
        slugs_estruturais=_slugs_estruturais(),
    )


def canetas_do_perfil(perfil: Perfil) -> tuple[Caneta, ...]:
    """A própria mais a coberta. A cobertura entra com a unidade e os cargos do SUBSTITUÍDO, que é
    quem tem a competência emprestada."""
    canetas = [_caneta_de(quem_exerce=perfil, dono_do_cargo=perfil)]
    substituicao = substituicao_que_exerce(perfil)
    if substituicao is not None:
        canetas.append(
            _caneta_de(quem_exerce=perfil, dono_do_cargo=substituicao.impedimento.perfil)
        )
    return tuple(canetas)


def dirige(perfil: Perfil, unidade: Unidade) -> bool:
    """Confere se quem `avaliar_direcao` aponta é este perfil — titular ou substituto dele. A regra
    de direção não é reescrita aqui, e o estado é o mesmo que a página da unidade monta."""
    titular = unidade.titular
    substituicao = substituicao_vigente(titular) if titular else None
    substituto = substituicao.substituto if substituicao else None
    direcao = avaliar_direcao(_estado_da_direcao(titular, substituto))
    if direcao == Direcao.TITULAR:
        return titular is not None and titular.pk == perfil.pk
    if direcao == Direcao.SUBSTITUTO:
        return substituto is not None and substituto.pk == perfil.pk
    return False


def unidades_dirigidas(perfil: Perfil) -> frozenset[int]:
    """As unidades das canetas que dirigem — pode ser mais de uma, quando alguém cobre o titular de
    outra unidade. É daqui que a SPEC 004 parte para calcular o alcance."""
    return frozenset(
        caneta.unidade_id for caneta in canetas_do_perfil(perfil) if caneta.dirige_a_unidade
    )


def _caneta_de(quem_exerce: Perfil, dono_do_cargo: Perfil) -> Caneta:
    return Caneta(
        unidade_id=dono_do_cargo.unidade_id,
        cargo_base_id=dono_do_cargo.cargo_base_id,
        cargo_comissao_id=dono_do_cargo.cargo_comissao_id,
        dirige_a_unidade=dirige(quem_exerce, dono_do_cargo.unidade),
    )


def _slugs_estruturais() -> frozenset[str]:
    return frozenset(
        implementada.acao.slug for implementada in REGISTRO.todas() if implementada.acao.estrutural
    )
