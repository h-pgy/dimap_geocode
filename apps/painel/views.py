from typing import cast

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.competencias.resolucao import slugs_liberados
from apps.mapping.context import contexto_fundo_admin
from apps.user_admin.models import Perfil

from .abas_declaradas import PAINEL
from .resolucao import MontagemPainel, ResolvedorPainel

TEMPLATE_PAINEL = "painel/painel.html"


@login_required
def painel(request: HttpRequest) -> HttpResponse:
    perfil = cast(Perfil, request.user)
    resolvido = ResolvedorPainel()(
        MontagemPainel(
            painel=PAINEL,
            slugs_liberados=slugs_liberados(perfil),
            perfil_id=perfil.pk,
        )
    )
    return render(request, TEMPLATE_PAINEL, {"painel": resolvido, **contexto_fundo_admin()})
