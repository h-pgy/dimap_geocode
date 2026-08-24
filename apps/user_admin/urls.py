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
    # A ação "tornar administrador" (SPEC user_admin/022): a tela da rota direta, a lista de
    # servidores que ela recarrega, o botão do servidor escolhido e a gravação — que incide sobre o
    # servidor já existente, vindo do caminho da rota, e não da tela direta ou da dos dois modais.
    path("servidores/administrador/", views.modal_administrador, name="modal_administrador"),
    path("servidores/administrador/opcoes/", views.opcoes_administrador, name="opcoes_administrador"),
    path("servidores/administrador/estado/", views.estado_administrador, name="estado_administrador"),
    path(
        "servidores/<int:servidor>/administrador/",
        views.gravar_administrador,
        name="gravar_administrador",
    ),
]
