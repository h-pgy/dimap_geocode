"""
Impedimentos do servidor da DIMAP (SPEC user_admin/002): o tipo de impedimento é um catálogo
reutilizável (férias, licença, afastamento) e o impedimento concreto vincula um servidor a um
tipo por um período. Sobreposição de períodos do mesmo servidor é permitida — ver SPEC.
"""

from django.db import models
from django.db.models import F, Q


class TipoImpedimento(models.Model):
    nome = models.CharField(
        max_length=120,
        unique=True,
    )
    sigla = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    class Meta:
        verbose_name = "Tipo de impedimento"
        verbose_name_plural = "Tipos de impedimento"
        constraints = [
            # unique=True no campo barraria o segundo tipo sem sigla; a condição isenta o vazio.
            models.UniqueConstraint(
                fields=["sigla"],
                condition=~Q(sigla=""),
                name="tipo_impedimento_sigla_unica",
            ),
        ]

    def __str__(self) -> str:
        return self.nome_exibicao

    @property
    def nome_exibicao(self) -> str:
        return self.sigla or self.nome


class Impedimento(models.Model):
    perfil = models.ForeignKey(
        "user_admin.Perfil",
        on_delete=models.CASCADE,
        related_name="impedimentos",
    )
    tipo = models.ForeignKey(
        TipoImpedimento,
        on_delete=models.PROTECT,
        related_name="impedimentos",
    )
    data_inicio = models.DateField()
    # Nulo = prazo indeterminado; data-sentinela faria toda comparação de data mentir.
    data_fim = models.DateField(
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Impedimento"
        verbose_name_plural = "Impedimentos"
        constraints = [
            models.CheckConstraint(
                condition=Q(data_fim__isnull=True) | Q(data_fim__gte=F("data_inicio")),
                name="impedimento_fim_nao_antecede_inicio",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.perfil} — {self.tipo.nome_exibicao}"
