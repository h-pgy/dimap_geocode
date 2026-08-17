"""
Inspeção somente-leitura da competência (SPEC autorizacao/002). A projeção da ação não é editável
por tela nenhuma; atribuir unidade a ação é ato administrativo próprio (SPEC 007) sem caminho de
criação aqui — o admin só existe para conferir o que já está no banco.
"""

from django.contrib import admin
from django.http import HttpRequest

from .models import Acao, AtribuicaoUnidade, Concessao, ExecucaoAcao


class SomenteLeituraAdmin(admin.ModelAdmin):
    """Base para as três tabelas: nenhuma delas nasce, muda ou some por aqui."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False


@admin.register(Acao)
class AcaoAdmin(SomenteLeituraAdmin):
    list_display = ["slug", "nome", "estrutural", "ativa"]
    list_filter = ["ativa", "estrutural"]
    search_fields = ["slug", "nome"]


@admin.register(AtribuicaoUnidade)
class AtribuicaoUnidadeAdmin(SomenteLeituraAdmin):
    list_display = ["unidade", "acao"]
    list_filter = ["unidade", "acao"]


@admin.register(Concessao)
class ConcessaoAdmin(SomenteLeituraAdmin):
    list_display = ["atribuicao", "cargo_base", "cargo_comissao", "concedida_por", "concedida_em"]
    list_filter = ["cargo_base", "cargo_comissao"]


@admin.register(ExecucaoAcao)
class ExecucaoAcaoAdmin(SomenteLeituraAdmin):
    """Consulta do histórico de atos — sem tela própria ainda (SPEC autorizacao/004, §4)."""

    list_display = ["acao", "perfil", "unidade", "operacao", "autorizado", "momento"]
    list_filter = ["acao", "unidade", "autorizado"]
    search_fields = ["alvo_identificador"]
