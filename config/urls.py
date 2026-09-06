from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path

# Anotada porque a rota de mídia abaixo acrescenta URLPattern a uma lista que, sem isso, o mypy
# infere como só de URLResolver (todas as entradas são include).
urlpatterns: list[URLResolver | URLPattern] = [
    path("admin/", admin.site.urls),
    path("", include("apps.autenticacao.urls")),
    path("", include("apps.core.urls")),
    path("painel/", include("apps.painel.urls")),
    path("", include("apps.mapping.urls")),
    path("gestao/", include("apps.user_admin.urls")),
    path("gestao/unidades/", include("apps.unidades.urls")),
    path("gestao/cargos/", include("apps.cargos.urls")),
    path("competencias/", include("apps.competencias.urls")),
    path("", include("apps.search.urls")),
    path("logradouro/", include("apps.logradouro_matcher.urls")),
    path("logradouro/", include("apps.logradouro_geocoder.urls")),
    path("lote/", include("apps.lote_matcher.urls")),
    path("lote/", include("apps.lote_geocoder.urls")),
    path("endereco/", include("apps.address_geocoder.urls")),
]

# A foto do perfil (SPEC user_admin/006) é servida pelo runserver só em dev; em produção o arquivo
# de mídia é do servidor web, não do Django.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
