from datetime import datetime, time

from services.utils.tempo import segundos_ate_proximo


def test_segundos_ate_proximo_horario_ainda_hoje() -> None:
    espera = segundos_ate_proximo(time(3, 0), datetime(2026, 8, 3, 1, 30, 0))

    assert espera == 1.5 * 3600


def test_segundos_ate_proximo_horario_ja_passou() -> None:
    espera = segundos_ate_proximo(time(3, 0), datetime(2026, 8, 3, 5, 0, 0))

    assert espera == 22 * 3600

    # Horário exatamente agora: o daemon acabou de rodar e voltou ao loop — esperar zero o
    # faria disparar duas vezes seguidas.
    espera_no_alvo = segundos_ate_proximo(time(3, 0), datetime(2026, 8, 3, 3, 0, 0))

    assert espera_no_alvo == 24 * 3600
