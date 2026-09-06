"""
Comparação e fatiamento de períodos (SPEC user_admin/015): a única guarda da não-sobreposição,
que saiu do banco por não caber em constraint. Domínio puro, sem Django.
"""

from datetime import date, timedelta

from services.domain.exercicio.models import Periodo, Trecho

DIA = timedelta(days=1)


def se_sobrepoem(a: Periodo, b: Periodo) -> bool:
    """Encostar pelas pontas é sobrepor: o dia compartilhado teria dois respondendo pelo cargo."""
    return _comeca_ate(a.inicio, b.fim) and _comeca_ate(b.inicio, a.fim)


def vigente_em(periodo: Periodo, dia: date) -> bool:
    """Valer num dia é sobrepor esse dia — o mesmo predicado, com o período de um dia só."""
    return se_sobrepoem(periodo, Periodo(inicio=dia, fim=dia))


def contem(externo: Periodo, interno: Periodo) -> bool:
    """O período da substituição nunca começa antes nem termina depois do impedimento."""
    if interno.inicio < externo.inicio:
        return False
    if externo.fim is None:
        return True
    return interno.fim is not None and interno.fim <= externo.fim


def lacunas(
    impedimento: Periodo,
    ocupados: tuple[Periodo, ...],
) -> tuple[Periodo, ...]:
    """Os pedaços do afastamento sem ninguém respondendo. A primeira lacuna é o período que a
    designação propõe por padrão."""
    descobertos: list[Periodo] = []
    cursor = impedimento.inicio
    for ocupado in sorted(ocupados, key=_pelo_inicio):
        if ocupado.inicio > cursor:
            descobertos.append(Periodo(inicio=cursor, fim=ocupado.inicio - DIA))
        # Cobertura indeterminada: daqui para a frente não sobra descoberto a apurar.
        if ocupado.fim is None:
            return tuple(descobertos)
        cursor = max(cursor, ocupado.fim + DIA)
    if _comeca_ate(cursor, impedimento.fim):
        descobertos.append(Periodo(inicio=cursor, fim=impedimento.fim))
    return tuple(descobertos)


def trechos(
    impedimento: Periodo,
    ocupados: tuple[Trecho, ...],
) -> tuple[Trecho, ...]:
    """O afastamento fatiado em ordem, cobertos e descobertos alternados. Existe para a linha da
    cobertura não ser montada intercalando duas listas no template (§3.1)."""
    periodos_ocupados = tuple(trecho.periodo for trecho in ocupados)
    descobertos = [
        Trecho(periodo=periodo, substituto_id=None)
        for periodo in lacunas(impedimento, periodos_ocupados)
    ]
    return tuple(sorted([*ocupados, *descobertos], key=_trecho_pelo_inicio))


def _comeca_ate(inicio: date, fim: date | None) -> bool:
    # Fim nulo é indeterminado: alcança qualquer início posterior ao seu.
    return fim is None or inicio <= fim


def _pelo_inicio(periodo: Periodo) -> date:
    return periodo.inicio


def _trecho_pelo_inicio(trecho: Trecho) -> date:
    return trecho.periodo.inicio
