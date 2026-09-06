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
    # A ação "registrar impedimento de servidor" (SPEC user_admin/023): os dois modais da página do
    # servidor, as duas rotas que gravam — o alvo vem do caminho, que é o único id que o cliente não
    # forja — e a tela da rota direta com as duas leituras que ela encadeia.
    path(
        "servidores/<int:servidor>/impedimento/modal/",
        views.modal_impedimento,
        name="modal_impedimento",
    ),
    path(
        "servidores/<int:servidor>/impedimento/",
        views.gravar_impedimento,
        name="gravar_impedimento",
    ),
    path("servidores/<int:servidor>/retorno/modal/", views.modal_retorno, name="modal_retorno"),
    path("servidores/<int:servidor>/retorno/", views.gravar_retorno, name="gravar_retorno"),
    path(
        "servidores/impedimento/",
        views.modal_registrar_impedimento,
        name="modal_registrar_impedimento",
    ),
    # Mesma lista de servidores por unidade do modal de plenos poderes, servida por rota própria: o
    # partial e o contexto se reusam, a competência que protege a rota é que muda.
    path("servidores/impedimento/opcoes/", views.opcoes_impedimento, name="opcoes_impedimento"),
    path("servidores/impedimento/face/", views.face_impedimento, name="face_impedimento"),
    # A ação "designar substituto" (SPEC user_admin/024). O impedimento e a substituição descem
    # ABAIXO do servidor no caminho: é o servidor que o alcance confere, e são eles que a consulta
    # escopa por ele.
    path("servidores/<int:servidor>/impedimentos/<int:impedimento>/substituto/modal/", views.modal_designar, name="modal_designar"),
    path("servidores/<int:servidor>/impedimentos/<int:impedimento>/substituto/", views.gravar_designacao, name="gravar_designacao"),
    path("servidores/<int:servidor>/substituicoes/<int:substituicao>/trocar/modal/", views.modal_trocar, name="modal_trocar"),
    path("servidores/<int:servidor>/substituicoes/<int:substituicao>/trocar/", views.gravar_troca, name="gravar_troca"),
    path("servidores/<int:servidor>/substituicoes/<int:substituicao>/encerrar/modal/", views.modal_encerrar, name="modal_encerrar"),
    path("servidores/<int:servidor>/substituicoes/<int:substituicao>/encerrar/", views.gravar_encerramento, name="gravar_encerramento"),
    path("servidores/substituicoes/", views.modal_designar_substituto, name="modal_designar_substituto"),
    # Mesma lista de servidores por unidade dos outros dois modais diretos, servida por rota
    # própria: o partial e o contexto se reusam, a competência que protege a rota é que muda.
    path("servidores/substituicoes/opcoes/", views.opcoes_substituicao, name="opcoes_substituicao"),
    path("servidores/substituicoes/face/", views.face_substituicao, name="face_substituicao"),
    # A ação "exonerar servidor" (SPEC user_admin/027): as três portas — o botão da seção
    # Exercício, a coluna da tabela e o card do painel — chegam à mesma rota direta, que resolve
    # `?servidor=` quando ele já é conhecido. Precisa reverter sem argumento (`competencias.E004`).
    path("servidores/exonerar/", views.modal_exonerar_servidor, name="modal_exonerar_servidor"),
    path("servidores/exonerar/opcoes/", views.opcoes_exoneracao, name="opcoes_exoneracao"),
    path("servidores/exonerar/face/", views.face_exoneracao, name="face_exoneracao"),
    path("servidores/<int:servidor>/exonerar/", views.gravar_exoneracao, name="gravar_exoneracao"),
    path(
        "servidores/<int:servidor>/reintegrar/",
        views.gravar_reintegracao,
        name="gravar_reintegracao",
    ),
]
