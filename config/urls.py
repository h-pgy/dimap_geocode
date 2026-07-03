from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("", include("apps.search.urls")),
    path("logradouro/", include("apps.logradouro_matcher.urls")),
    path("logradouro/", include("apps.logradouro_geocoder.urls")),
    path("lote/", include("apps.lote_matcher.urls")),
    path("lote/", include("apps.lote_geocoder.urls")),
    path("endereco/", include("apps.address_geocoder.urls")),
]
