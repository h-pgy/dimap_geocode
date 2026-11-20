from .anexos.urls import urlpatterns as anexos
from .gestao.urls import urlpatterns as gestao
from .pagina.urls import urlpatterns as pagina
from .taxonomia.urls import urlpatterns as taxonomia

app_name = "faq"

urlpatterns = [
    *pagina,
    *gestao,
    *taxonomia,
    *anexos,
]
