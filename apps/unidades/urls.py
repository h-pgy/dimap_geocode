from django.urls import path

from apps.unidades import views

app_name = "unidades"

urlpatterns = [
    path("nova/", views.criar_unidade, name="criar_unidade"),
    # A escrita é rota apartada da que mostra o formulário: é essa separação que faz "abrir a tela
    # não cadastra nada" ser estrutural, e não uma flag no formulário.
    path("nova/gravar/", views.gravar_unidade, name="gravar_unidade"),
    # O ato é UM (`cadastrar_unidade`); o que muda é o desfecho que cada tela precisa ver. A
    # página troca o formulário inteiro pelo painel de conclusão; as telas de servidor trocam só o
    # bloco de campos por uma tarja curta e ainda atualizam, fora de banda, o select de lotação que
    # vive fora do modal.
    path(
        "nova/gravar-e-selecionar/",
        views.gravar_unidade_e_selecionar,
        name="gravar_unidade_e_selecionar",
    ),
    # A raiz tem porta própria porque é ato próprio: mesma tela, outro contrato de competência. O
    # `url_name` do contrato aponta para a de abertura, que é a que o check resolve.
    path("raiz/", views.criar_unidade_raiz, name="criar_unidade_raiz"),
    path("raiz/gravar/", views.gravar_unidade_raiz, name="gravar_unidade_raiz"),
    path("cor-sugerida/", views.cor_sugerida_unidade, name="cor_sugerida_unidade"),
    path("arvore/", views.arvore_de_unidades, name="arvore_de_unidades"),
    path("<int:pk>/", views.pagina_unidade, name="pagina_unidade"),
    # `unidade`, e não `pk`: é o parâmetro que o alcance da ação nomeia.
    path("<int:unidade>/editar/", views.editar_unidade, name="editar_unidade"),
    path("<int:unidade>/gravar/", views.gravar_edicao_unidade, name="gravar_edicao_unidade"),
]
