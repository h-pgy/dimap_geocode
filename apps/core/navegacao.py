"""Origem da requisição (SPEC painel/001): usado pela página cujo botão de volta muda de destino
conforme de onde o usuário veio — chegou pelo painel, o botão leva de volta a ele; chegou de outro
lugar, leva para onde essa tela sempre levou.
"""

from urllib.parse import urlparse

from django.http import HttpRequest
from django.urls import reverse


def veio_do_painel(request: HttpRequest) -> bool:
    referer = request.META.get("HTTP_REFERER", "")
    return urlparse(referer).path == reverse("painel:painel")
