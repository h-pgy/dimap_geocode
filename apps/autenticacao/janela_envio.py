"""
A janela entre envios à caixa de entrada de um servidor (SPEC autenticacao/003 e 004): compartilhada
entre a recuperação de senha e o reenvio da senha de uso único, porque as duas protegem o mesmo
destino.
"""

import time

from django.conf import settings
from django.core.cache import cache

from apps.user_admin.models import Perfil

CHAVE_JANELA = "janela_envio_credencial:{pk}"
JANELA_REENVIO_SEGUNDOS = settings.JANELA_REENVIO_SEGUNDOS


def espera_do_reenvio(perfil: Perfil) -> int:
    """O valor guardado é o instante em que o envio libera, e não um sinalizador: sem ele a tela
    diria "aguarde" sem saber quanto, e o cache do Django não conta o tempo que falta para uma
    chave expirar."""
    liberado_em = cache.get(CHAVE_JANELA.format(pk=perfil.pk))
    if liberado_em is None:
        return 0
    return max(0, int(liberado_em - time.time()))


def armar_janela(perfil: Perfil) -> None:
    # Só depois de a mensagem sair de fato: com o envio desligado não há caixa de entrada a
    # proteger, e segurar ali só atrapalharia o desenvolvimento.
    cache.set(
        CHAVE_JANELA.format(pk=perfil.pk),
        time.time() + JANELA_REENVIO_SEGUNDOS,
        timeout=JANELA_REENVIO_SEGUNDOS,
    )
