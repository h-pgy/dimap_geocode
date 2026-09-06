"""
Delegação nominal de competência estrutural (SPEC autorizacao/009): vincula uma competência estrutural
a um servidor (Perfil) específico, herdando o alcance do ramo da unidade delegante.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class Delegacao(models.Model):
    acao = models.ForeignKey(
        "competencias.Acao",
        on_delete=models.PROTECT,
        related_name="delegacoes",
    )
    unidade = models.ForeignKey(
        "unidades.Unidade",
        on_delete=models.PROTECT,
        related_name="delegacoes",
    )
    delegante = models.ForeignKey(
        "user_admin.Perfil",
        on_delete=models.PROTECT,
        related_name="delegacoes_feitas",
    )
    delegado = models.ForeignKey(
        "user_admin.Perfil",
        on_delete=models.PROTECT,
        related_name="delegacoes_recebidas",
    )
    data_inicio = models.DateField()
    data_fim = models.DateField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Delegação de competência"
        verbose_name_plural = "Delegações de competência"
        constraints = [
            models.CheckConstraint(
                condition=Q(data_fim__isnull=True) | Q(data_fim__gte=F("data_inicio")),
                name="delegacao_fim_nao_antecede_inicio",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.acao} em {self.unidade} → {self.delegado}"

    def clean(self) -> None:
        if not self.acao.estrutural:
            raise ValidationError("Apenas competências estruturais podem ser delegadas nominalmente.")
        if self.delegante_id == self.delegado_id:
            raise ValidationError("O titular não pode delegar competência a si mesmo.")
        if self.delegado.exonerado:
            raise ValidationError("Servidor exonerado não pode receber delegação de competência.")
