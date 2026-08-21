"""Rotas de `competencias` (SPEC autorizacao/007): seis, todas protegidas pelo mesmo contrato. O
`app_name` fecha o `url_name` declarado na ação, e o system check da SPEC 001 faz `reverse` dele no
boot."""

from django.urls import path

from . import views

app_name = "competencias"

urlpatterns = [
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
]
