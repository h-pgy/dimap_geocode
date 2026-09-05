"""
O ato praticado (SPEC autorizacao/004): guarda o que descreve o ato NO DIA em que foi praticado —
cargo, unidade e a cobertura, se houve —, não o que o cadastro do autor diz hoje.
"""

from django.conf import settings
from django.db import models

from apps.cargos.models import CargoBase, CargoComissao
from apps.unidades.models import Unidade

from .acao import Acao


class ExecucaoAcao(models.Model):
    acao = models.ForeignKey(Acao, on_delete=models.PROTECT, related_name="acoes_executadas")
    perfil = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="acoes_executadas",
        null=True,
    )
    # Lotação no momento do ato: perfil muda de unidade, e o histórico não pode mudar junto.
    unidade = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name="acoes_executadas")
    cargo_base = models.ForeignKey(CargoBase, on_delete=models.PROTECT, related_name="acoes_executadas")
    cargo_comissao = models.ForeignKey(
        CargoComissao,
        on_delete=models.PROTECT,
        related_name="acoes_executadas",
        null=True,
    )
    # Ato praticado cobrindo alguém: a pessoa, nunca a linha da Substituicao, que é encerrada e
    # reaberta ao longo do tempo.
    substituindo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="execucoes_cobertas",
        null=True,
        blank=True,
    )
    autorizado = models.BooleanField()
    # A ação é a competência; a operação é o que se fez com ela — atribuir não é remover.
    operacao = models.CharField(max_length=40, blank=True)
    # Entidade territorial não é model (vem de parquet e WFS): o alvo é texto livre. Par de alvos
    # vira identificador composto, em vez de multiplicar colunas por ação.
    alvo_tipo = models.CharField(max_length=40, blank=True)
    alvo_identificador = models.CharField(max_length=120, blank=True)
    momento = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Execução de ação"
        verbose_name_plural = "Execuções de ação"

    def __str__(self) -> str:
        veredito = "autorizada" if self.autorizado else "negada"
        return f"{self.acao} — {veredito} — {self.momento:%d/%m/%Y %H:%M}"
