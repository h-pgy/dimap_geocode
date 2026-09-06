"""
Quem dirige a unidade hoje, dito para a tela (SPEC user_admin/016): o estado que o avaliador de
domínio lê, o cargo mínimo em padrão de vencimento e as frases dos dois alarmes.

Público porque a pergunta é da unidade e três telas a fazem: a página da unidade, a página do
servidor que a titulariza e o seletor de alcance de `competencias`.
"""

from apps.cargos.models import CargoComissao
from apps.unidades.models import TipoUnidade, Unidade
from apps.user_admin.models import Perfil
from services.domain.titularidade import EstadoDaDirecao

# O organograma fala em padrão de cargo, não em número de nível (SPEC user_admin/016).
ROTULO_ALTA_ADMINISTRACAO = "Alta administração"


def estado_da_direcao(
    titular: Perfil | None,
    substituto: Perfil | None,
) -> EstadoDaDirecao:
    return EstadoDaDirecao(
        tem_titular=titular is not None,
        titular_em_exercicio=bool(titular and titular.em_exercicio),
        # O substituto fora de exercício não cobre ninguém: a unidade fica sem direção.
        substituto_do_titular_em_exercicio=bool(substituto and substituto.em_exercicio),
    )


def rotulo_do_minimo(tipo: TipoUnidade) -> str:
    # O organograma fala em padrão de cargo, não em número de nível.
    if tipo.exige_alta_administracao:
        return ROTULO_ALTA_ADMINISTRACAO
    cargo = CargoComissao.objects.filter(
        e_chefia=True,
        nivel=tipo.nivel_minimo_titular,
    ).first()
    return cargo.padrao if cargo else ""


def alarme_sem_titular(unidade: Unidade) -> str:
    return (
        f"A {unidade.sigla} está sem titular. Nenhum servidor titulariza esta unidade — "
        "é preciso nomear um titular."
    )


def alarme_sem_direcao(unidade: Unidade, titular: Perfil) -> str:
    return (
        f"A {unidade.sigla} está sem quem responda por ela. {titular.nome} {titular.sobrenome} "
        "é o titular, está afastado e não há substituto designado — designe um substituto na "
        "página dele."
    )
