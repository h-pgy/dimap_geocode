from django.urls import path

from apps.user_admin import views

app_name = "user_admin"

urlpatterns = [
    path("servidores/", views.listar_servidores, name="listar_servidores"),
    # Partial do corpo da tabela: rota própria em vez de sniffar o cabeçalho do HTMX — quem decide
    # o que devolver é a URL, como no resto do projeto.
    path("servidores/corpo/", views.corpo_servidores, name="corpo_servidores"),
    path("servidores/novo/", views.criar_perfil, name="criar_perfil"),
    # Duas rotas para o mesmo servidor, e é a segunda que o épico `autorizacao` vai proteger: ler é
    # a página, editar é o modal (SPEC user_admin/017).
    path("servidores/<int:pk>/", views.pagina_perfil, name="pagina_perfil"),
    path("servidores/<int:pk>/editar/", views.editar_perfil, name="editar_perfil"),
    path("unidades/nova/", views.criar_unidade, name="criar_unidade"),
    path(
        "unidades/cor-sugerida/",
        views.cor_sugerida_unidade,
        name="cor_sugerida_unidade",
    ),
    path("unidades/arvore/", views.arvore_de_unidades, name="arvore_de_unidades"),
    path("unidades/<int:pk>/", views.pagina_unidade, name="pagina_unidade"),
]
