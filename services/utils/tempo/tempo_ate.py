from datetime import datetime, time, timedelta


def segundos_ate_proximo(horario: time, agora: datetime) -> float:
    alvo = agora.replace(
        hour=horario.hour,
        minute=horario.minute,
        second=0,
        microsecond=0,
    )
    # Esperar zero no alvo faria o daemon disparar duas vezes seguidas: no alvo, a próxima é amanhã.
    if alvo <= agora:
        alvo += timedelta(days=1)
    return (alvo - agora).total_seconds()
