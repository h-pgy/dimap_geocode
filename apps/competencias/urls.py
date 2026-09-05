"""Rotas de `competencias` (SPEC autorizacao/007): seis, todas protegidas pelo mesmo contrato. O
`app_name` fecha o `url_name` declarado na ação, e o system check da SPEC 001 faz `reverse` dele no
boot."""

from django.urls import path

from . import views

app_name = "competencias"

urlpatterns = [
    # Leitura, não ato (SPEC painel/002, §7): sem contrato, sem `acao_protegida`.
    path("registro-acoes/", views.listar_registro_acoes, name="listar_registro_acoes"),
    path("registro-acoes/corpo/", views.corpo_execucoes, name="corpo_execucoes"),
    # A tela. Sem argumento na URL: o alvo viaja como parâmetro, que é o que o alcance confere.
    path("atribuicoes/", views.definir_atribuicao, name="definir_atribuicao"),
    # Trocar de unidade na árvore troca só o painel — a árvore não é reenviada.
    path("atribuicoes/painel/", views.painel_atribuicoes, name="painel_atribuicoes"),
    path("atribuicoes/catalogo/", views.catalogo, name="catalogo_atribuicao"),
    path("atribuicoes/atribuir/", views.atribuir, name="atribuir"),
    # A confirmação é rota de LEITURA e a remoção é rota de escrita: é essa separação, e não uma
    # flag no formulário, que faz "sem confirmação nada é apagado" ser estrutural.
    path("atribuicoes/remover/confirmar/", views.confirmar_remocao, name="confirmar_remocao"),
    path("atribuicoes/remover/", views.remover, name="remover"),
    # A tela de conceder competência (SPEC autorizacao/008), a mesma coreografia: painel por
    # hx-get ao trocar de unidade, modal por hx-get, e conceder/revogar por hx-post.
    path("conceder/", views.conceder, name="conceder"),
    path("conceder/painel/", views.painel_concessoes, name="painel_concessoes"),
    path("conceder/modal/", views.modal_conceder, name="modal_conceder"),
    path("conceder/modal-delegar/", views.modal_delegar, name="modal_delegar"),
    path("conceder/conceder/", views.conceder_cargo, name="conceder_cargo"),
    path("conceder/revogar/", views.revogar_cargo, name="revogar_cargo"),
    path("conceder/delegar/", views.delegar_servidor, name="delegar_servidor"),
    path("conceder/revogar-delegacao/", views.revogar_delegacao, name="revogar_delegacao"),
]
