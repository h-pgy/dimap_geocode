from datetime import datetime

from .constants import MESES


def por_extenso(momento: datetime) -> str:
    """A data como ela sai no quadro de fecho. O momento chega já no fuso em que se quer lê-lo:
    converter aqui exigiria que o domínio conhecesse o fuso do ambiente."""
    return f"{momento.day} de {MESES[momento.month - 1]} de {momento.year}, às {momento:%Hh%Mmin}"
