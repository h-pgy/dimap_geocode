"""
Unidade da DIMAP (SPEC user_admin/001): catálogo de lotação referenciado pelo Perfil.
"""

from django.db import models


class Unidade(models.Model):
    nome = models.CharField(
        max_length=120,
        unique=True,
    )
    sigla = models.CharField(
        max_length=20,
        unique=True,
    )

    class Meta:
        verbose_name = "Unidade"
        verbose_name_plural = "Unidades"

    def __str__(self) -> str:
        return self.sigla
