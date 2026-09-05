from django.urls import path

from apps.cargos import views

app_name = "cargos"

urlpatterns = [
    path("", views.listar_cargos, name="listar_cargos"),
    # Alvo do swap do HTMX da tabela: só o <tbody>.
    path("corpo/", views.corpo_cargos, name="corpo_cargos"),
    path("novo/", views.modal_criar_cargo, name="modal_criar_cargo"),
    # A escrita é rota apartada da que mostra o formulário: é essa separação que faz "abrir a tela
    # não cadastra nada" ser estrutural, e não uma flag no formulário.
    path("novo/gravar/", views.gravar_criacao_cargo, name="gravar_criacao_cargo"),
    # `cargo`, e não `pk`: é o parâmetro que o alcance da ação nomeia (aqui, sem alcance, é só o
    # nome que a rota usa para o alvo).
    path("editar/", views.modal_editar_cargo, name="modal_editar_cargo"),
    path("<int:cargo>/editar/gravar/", views.gravar_edicao_cargo, name="gravar_edicao_cargo"),
    # Uma porta para abrir (a face sai do estado do cargo) e uma por operação para gravar: é essa
    # separação, e não uma flag no formulário, que faz "abrir o modal não pratica o ato" ser
    # estrutural.
    path("extinguir/", views.modal_extinguir_cargo, name="modal_extinguir_cargo"),
    path(
        "<int:cargo>/extinguir/gravar/",
        views.gravar_extincao_cargo,
        name="gravar_extincao_cargo",
    ),
    path("reativar/", views.modal_reativar_cargo, name="modal_reativar_cargo"),
    path(
        "<int:cargo>/reativar/gravar/",
        views.gravar_reativacao_cargo,
        name="gravar_reativacao_cargo",
    ),
    # O catálogo de cargo base (SPEC user_admin/030): mesmo molde de rotas do de cima.
    path("base/", views.listar_cargos_base, name="listar_cargos_base"),
    path("base/corpo/", views.corpo_cargos_base, name="corpo_cargos_base"),
    path("base/novo/", views.modal_criar_cargo_base, name="modal_criar_cargo_base"),
    path(
        "base/novo/gravar/",
        views.gravar_criacao_cargo_base,
        name="gravar_criacao_cargo_base",
    ),
    path("base/editar/", views.modal_editar_cargo_base, name="modal_editar_cargo_base"),
    path(
        "base/<int:cargo>/editar/gravar/",
        views.gravar_edicao_cargo_base,
        name="gravar_edicao_cargo_base",
    ),
    path("base/extinguir/", views.modal_extinguir_cargo_base, name="modal_extinguir_cargo_base"),
    path(
        "base/<int:cargo>/extinguir/gravar/",
        views.gravar_extincao_cargo_base,
        name="gravar_extincao_cargo_base",
    ),
    path("base/reativar/", views.modal_reativar_cargo_base, name="modal_reativar_cargo_base"),
    path(
        "base/<int:cargo>/reativar/gravar/",
        views.gravar_reativacao_cargo_base,
        name="gravar_reativacao_cargo_base",
    ),
]
