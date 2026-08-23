from django.urls import path

from apps.user_admin import views

app_name = "user_admin"

urlpatterns = [
    path("servidores/", views.listar_servidores, name="listar_servidores"),
    # Partial do corpo da tabela: rota própria em vez de sniffar o cabeçalho do HTMX — quem decide
    # o que devolver é a URL, como no resto do projeto.
    path("servidores/corpo/", views.corpo_servidores, name="corpo_servidores"),
    path("servidores/novo/", views.criar_perfil, name="criar_perfil"),
    # Rota de escrita apartada da que mostra o formulário (SPEC criacao_usuarios/004): é essa
    # separação que faz "abrir a tela não cadastra ninguém" ser estrutural, e não uma flag no
    # formulário.
    path("servidores/novo/gravar/", views.gravar_servidor, name="gravar_servidor"),
    # Ler é a página, editar é o modal — e a gravação é uma terceira rota, protegida como a de
    # editar (SPEC criacao_usuarios/005). `servidor`, e não `pk`: é o parâmetro que o alcance da
    # ação nomeia.
    path("servidores/<int:pk>/", views.pagina_perfil, name="pagina_perfil"),
    path("servidores/<int:servidor>/editar/", views.editar_perfil, name="editar_perfil"),
    path("servidores/<int:servidor>/gravar/", views.gravar_edicao, name="gravar_edicao"),
    path("unidades/nova/", views.criar_unidade, name="criar_unidade"),
    path(
        "unidades/cor-sugerida/",
        views.cor_sugerida_unidade,
        name="cor_sugerida_unidade",
    ),
    path("unidades/arvore/", views.arvore_de_unidades, name="arvore_de_unidades"),
    path("unidades/<int:pk>/", views.pagina_unidade, name="pagina_unidade"),
]
