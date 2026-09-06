"""
Substituição de um impedimento (SPEC user_admin/015): quem responde pelo cargo do afastado, por um
período próprio contido no do afastamento. É do impedimento, e não da pessoa — pendurada nela,
sobreviveria à causa —, e um impedimento tem várias, desde que não se sobreponham.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from .impedimentos import Impedimento

ERRO_DESIGNACAO_INVALIDA = (
    "O período da substituição precisa caber no afastamento, e nem o substituído nem o substituto "
    "podem estar exonerados ou já comprometidos nesse período."
)


class Substituicao(models.Model):
    # Várias por impedimento: o que a regra proíbe é sobreposição, não pluralidade — é assim que
    # uma pessoa cobre a primeira semana e outra a segunda.
    impedimento = models.ForeignKey(
        Impedimento,
        on_delete=models.CASCADE,
        related_name="substituicoes",
    )
    substituto = models.ForeignKey(
        "user_admin.Perfil",
        on_delete=models.PROTECT,
        related_name="substituicoes_exercidas",
    )
    # Período próprio, sempre contido no do impedimento: é o que permite substituir só parte do
    # afastamento e, ao mesmo tempo, ler a vigência da substituição sem compor com a dele.
    data_inicio = models.DateField()
    data_fim = models.DateField(
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Substituição"
        verbose_name_plural = "Substituições"
        constraints = [
            # A única coisa que não depende de outra linha, e por isso a única que o banco garante.
            models.CheckConstraint(
                condition=Q(data_fim__isnull=True) | Q(data_fim__gte=F("data_inicio")),
                name="substituicao_fim_nao_antecede_inicio",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.substituto} — {self.impedimento}"

    def clean(self) -> None:
        # Contenção no impedimento, não-sobreposição dos dois lados, cargo do substituído,
        # exoneração das duas pontas e as pontas sendo a mesma pessoa: tudo cruza linha e tabela,
        # nada cabe em constraint. Importado aqui dentro porque a montagem do DTO mora ao lado dos
        # atos, que por sua vez importam este model.
        from services.domain.exercicio import avaliar_designacao

        from apps.user_admin.substituicao import designacao_de

        if self.data_inicio is None:
            return
        if not hasattr(self, "impedimento") or not hasattr(self, "substituto"):
            return
        if not avaliar_designacao(designacao_de(self)):
            raise ValidationError(ERRO_DESIGNACAO_INVALIDA)
