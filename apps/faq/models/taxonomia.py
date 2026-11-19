from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower


class Tema(models.Model):
    nome = models.CharField(max_length=80)
    pai = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subtemas",
    )
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            # A raiz precisa de condição própria: NULL ≠ NULL no Postgres.
            models.UniqueConstraint(
                Lower("nome"), "pai", name="faq_tema_nome_unico_no_pai"
            ),
            models.UniqueConstraint(
                Lower("nome"),
                condition=Q(pai__isnull=True),
                name="faq_tema_nome_unico_na_raiz",
            ),
        ]

    def __str__(self) -> str:
        return self.nome

    def clean(self) -> None:
        # Dois níveis: o banco não consegue dizer isso sem trigger (Caveats da SPEC).
        if (
            self.pai_id is not None
            and self.pai is not None
            and self.pai.pai_id is not None
        ):
            raise ValidationError({"pai": "Subtema não pode ter subtema."})


class PalavraChave(models.Model):
    nome = models.CharField(max_length=60)
    pai = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="filhas",
    )
    # Simétrica: relacionar A a B já põe A nas relacionadas de B, numa linha só da junção.
    relacionadas = models.ManyToManyField("self", symmetrical=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("nome"),
                "pai",
                name="faq_palavra_chave_nome_unico_no_pai",
            ),
            models.UniqueConstraint(
                Lower("nome"),
                condition=Q(pai__isnull=True),
                name="faq_palavra_chave_nome_unico_na_raiz",
            ),
        ]

    def __str__(self) -> str:
        return self.nome

    def clean(self) -> None:
        # Três níveis: o pai já estar no terceiro faria desta a quarta.
        pai = self.pai if self.pai_id is not None else None
        avo = pai.pai if pai is not None and pai.pai_id is not None else None
        if avo is not None and avo.pai_id is not None:
            raise ValidationError({"pai": "Palavra-chave tem no máximo três níveis."})
