"""
Contexto global do widget de usuário no topo (SPEC autenticacao/001): a identidade autenticada é
resolvida uma vez por request, para `base.html` alimentar `#widget-area-usuario` em toda página.
"""

from typing import Any

from django.http import HttpRequest

from apps.unidades.paleta import hex_da_cor
from apps.user_admin.apresentacao import imagem_do_perfil


def contexto_usuario_autenticado(request: HttpRequest) -> dict[str, Any]:
    if not request.user.is_authenticated:
        return {}
    return {
        "imagem_perfil_usuario": imagem_do_perfil(request.user),
        "cor_unidade_hex": hex_da_cor(request.user.cor_unidade),
    }
